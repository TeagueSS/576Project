"""MQTT client coroutine using SimPy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import simpy

from sim.config import NodeConfig
from sim.mac import MACScheduler
from sim.metrics import MetricCollector
from sim.network import MQTTNetwork, MQTTMessage
from sim.phy_profiles import PHY_PROFILES


@dataclass
class EnergyState:
    tx_energy_mj: float = 0.0
    rx_energy_mj: float = 0.0
    sleep_energy_mj: float = 0.0


class MQTTClient:
    def __init__(
        self,
        env: simpy.Environment,
        config: NodeConfig,
        mac: MACScheduler,
        network: MQTTNetwork,
        metrics: MetricCollector,
        gateway_id: Optional[str] = None,
    ) -> None:
        self.env = env
        self.config = config
        self.mac = mac
        self.network = network
        self.metrics = metrics
        self.energy = EnergyState()
        self.gateway_id = gateway_id
        self.session = self.network.connect(
            client_id=config.node_id,
            clean_session=config.clean_session,
            keep_alive=30.0,
            will=(config.will_topic, config.will_message.encode("utf-8"), config.qos)
            if config.will_topic and config.will_message
            else None,
        )
        self.network.subscribe(config.node_id, config.topic, config.qos)
        self.process = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.config.publish_interval_s)
            payload_bits = self.config.payload_bytes * 8
            profile = PHY_PROFILES[self.config.phy]
            csma_sampler = None
            if self.config.phy in {"wifi", "zigbee"}:
                csma_sampler = lambda: 0.001  # constant backoff for simplicity
            tx_result = yield self.env.process(
                self.mac.tx(
                    self.config.node_id,
                    self.config.phy,
                    payload_bits,
                    csma_sampler,
                    duty_cycle_override=self.config.duty_cycle_override,
                )
            )
            if not tx_result.success:
                continue
            self.energy.tx_energy_mj += tx_result.energy_mj
            # Record radio TX time
            self.metrics.record_radio_tx(self.config.node_id, tx_result.duration_s)
            message = MQTTMessage(
                topic=self.config.topic,
                payload=b"x" * self.config.payload_bytes,
                qos=self.config.qos,
                retain=self.config.retained,
            )
            self.network.publish(self.config.node_id, message, gateway_id=self.gateway_id)
            # Sleep energy accumulation
            sleep_duration = self.config.publish_interval_s - (tx_result.latency_ms / 1000.0)
            if sleep_duration > 0:
                self.energy.sleep_energy_mj += sleep_duration * profile.sleep_power_mw / 1000.0
                self.metrics.record_radio_sleep(self.config.node_id, sleep_duration)
            self.metrics.record_energy(
                self.config.node_id,
                self.energy.tx_energy_mj + self.energy.sleep_energy_mj + self.energy.rx_energy_mj,
            )
            session = self.network.sessions.get(self.config.node_id)
            if session:
                session.last_seen = self.env.now

    def handle_ack(self, msg_id: int) -> None:
        self.network.ack(self.config.node_id, msg_id)


