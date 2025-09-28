"""Experiment batch runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import simpy

from sim.config import SimulationConfig, NodeConfig
from sim.mac import MACScheduler
from sim.metrics import MetricCollector
from sim.mobility import MobilityManager, MobilityProfile
from sim.mqtt import MQTTClient
from sim.network import MQTTNetwork
from sim.phy_profiles import PHY_PROFILES
from sim.utils import rng


@dataclass
class ExperimentResult:
    name: str
    snapshots: List


class ExperimentRunner:
    """Runs experiments according to provided configuration factory."""

    def __init__(self, config: SimulationConfig) -> None:
        # SimulationConfig is captured once so repeated runs reuse topology/
        # mobility data while allowing scenario-level overrides (e.g. failover).
        self.config = config
        self.current_network = None

    def run(
        self,
        scenario_name: str,
        stop_flag: callable | None = None,
        on_network: callable | None = None,
    ) -> ExperimentResult:
        env = simpy.Environment()
        metrics = MetricCollector()
        mac = MACScheduler(env, self.config.zigbee_duty_cycle_window_s)
        network = MQTTNetwork(env, metrics, self.config)
        self.current_network = network
        if on_network:
            try:
                on_network(network)
            except Exception:
                pass

        # Seed the environment with starting coordinates and mobility profiles.
        initial_positions = {}
        mobility_profiles = {}
        area_x, area_y = self.config.area_size
        for node in self.config.nodes:
            initial_positions[node.node_id] = (rng.uniform(0, area_x), rng.uniform(0, area_y))
            mobility_profiles[node.node_id] = MobilityProfile(
                speed_m_s=node.speed_m_s,
                pattern=node.mobility_pattern,
            )

        mobility = MobilityManager(env, self.config.area_size, initial_positions, mobility_profiles)

        clients: Dict[str, MQTTClient] = {}
        for node in self.config.nodes:
            # Create a SimPy process per client – each MQTTClient publishes,
            # sleeps, and reports metrics based on its NodeConfig.
            metrics.battery_capacity_mj[node.node_id] = node.battery_capacity_mj
            clients[node.node_id] = MQTTClient(env, node, mac, network, metrics, gateway_id=node.gateway_id)

        def broker_process():
            while True:
                if stop_flag and stop_flag():
                    # Respect GUI stop requests gracefully mid-iteration.
                    break
                yield env.timeout(self.config.stats_interval_s)
                network.process_queue()
                network.check_keep_alive()
                metrics.update_positions(dict(mobility.items()))
                metrics.update_gateways(
                    {
                        gw.gateway_id: {
                            "position": gw.position,
                            "range": getattr(gw, "coverage_radius_m", 40.0),
                        }
                        for gw in self.config.gateways
                    }
                )
                metrics.snapshot(env.now)

        env.process(broker_process())

        if self.config.broker_failover_s is not None:
            env.process(self._broker_failover(env, network, stop_flag))

        if self.config.moving_gateway_ids:
            env.process(self._move_gateways(env, stop_flag))

        def stopper():
            while True:
                if stop_flag and stop_flag():
                    env.exit()
                yield env.timeout(1)

        env.process(stopper())
        try:
            env.run(until=self.config.duration_s)
        except simpy.core.StopSimulation:
            pass
        return ExperimentResult(name=scenario_name, snapshots=metrics.snapshots)

    def _broker_failover(self, env: simpy.Environment, network: MQTTNetwork, stop_flag=None):
        # Introduce a broker outage at the configured timestamp to observe
        # reconnect behaviour and session persistence.
        yield env.timeout(self.config.broker_failover_s)
        if stop_flag and stop_flag():
            return
        for session in network.sessions.values():
            session.connected = False
            network.metrics.update_client_state(session.client_id, "reconnecting")
        yield env.timeout(self.config.broker_recover_s or 10.0)
        if stop_flag and stop_flag():
            return
        for session in network.sessions.values():
            network.connect(session.client_id, session.clean_session, session.keep_alive)

    def _move_gateways(self, env: simpy.Environment, stop_flag=None):
        # Periodically nudge configured gateways to emulate mobile coverage
        # and study handoff/coverage behaviour.
        while True:
            if stop_flag and stop_flag():
                return
            yield env.timeout(self.config.gateway_move_interval_s)
            for gw in self.config.gateways:
                if gw.gateway_id in self.config.moving_gateway_ids:
                    gx, gy = gw.position
                    gw.position = (
                        max(0, min(self.config.area_size[0], gx + rng.uniform(-1, 1) * self.config.gateway_move_distance)),
                        max(0, min(self.config.area_size[1], gy + rng.uniform(-1, 1) * self.config.gateway_move_distance)),
                    )


