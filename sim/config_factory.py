"""Factory helpers to build simulation configurations for scenarios."""

from __future__ import annotations

from dataclasses import replace
from typing import List

from sim.config import BrokerConfig, GatewayConfig, NodeConfig, SimulationConfig


def make_config(scenario: str = "baseline", node_count: int = 10) -> SimulationConfig:
    nodes: List[NodeConfig] = []
    base_count = max(1, node_count - 1)
    for idx in range(base_count):
        nodes.append(
            NodeConfig(
                node_id=f"sensor_{idx}",
                phy="zigbee" if idx < 5 else "ble",
                topic="sensors/temperature" if idx < 5 else "sensors/humidity",
                qos=1 if idx % 2 == 0 else 0,
                payload_bytes=32,
                publish_interval_s=30 + idx,
                mobility_pattern="stationary" if idx < 7 else "grid",
                speed_m_s=0.0 if idx < 7 else 1.0,
                clean_session=False,
                retained=False,
                gateway_id="gw1" if idx < 5 else "gw2",
                will_topic="alerts/status",
                will_message=f"sensor_{idx} offline",
                battery_capacity_mj=500000.0,
            )
        )

    nodes.append(
        NodeConfig(
            node_id="mobile_cam",
            phy="wifi",
            topic="cameras/stream",
            qos=0,
            payload_bytes=256,
            publish_interval_s=10,
            mobility_pattern="rwp",
            speed_m_s=1.5,
            clean_session=True,
            retained=False,
            gateway_id="gw2",
            will_topic="alerts/status",
            will_message="mobile_cam offline",
            battery_capacity_mj=800000.0,
        )
    )

    gateways = [
        GatewayConfig(gateway_id="gw1", position=(20, 20), wan_latency_ms=50, wan_loss_rate=0.01, coverage_radius_m=45.0),
        GatewayConfig(gateway_id="gw2", position=(80, 80), wan_latency_ms=70, wan_loss_rate=0.02, coverage_radius_m=45.0),
    ]

    broker = BrokerConfig(supervision_timeout_ms=5000, conn_interval_ms=60, queue_capacity=500)

    config = SimulationConfig(
        area_size=(100, 100),
        nodes=nodes,
        gateways=gateways,
        broker=broker,
        topic_list=list(dict.fromkeys(node.topic for node in nodes)),
        duration_s=600,
        stats_interval_s=5,
    )

    if scenario == "duty_cycle":
        for node in config.nodes:
            if node.phy == "zigbee":
                node.duty_cycle_override = 0.05
        config.duration_s = 1800
    elif scenario == "protocol_compare":
        phies = ["ble", "wifi", "zigbee"]
        for idx, node in enumerate(config.nodes):
            node.phy = phies[idx % len(phies)]
        config.duration_s = 900
    elif scenario == "ble_only":
        for node in config.nodes:
            node.phy = "ble"
        config.duration_s = 900
    elif scenario == "wifi_only":
        for node in config.nodes:
            node.phy = "wifi"
        config.duration_s = 900
    elif scenario == "zigbee_only":
        for node in config.nodes:
            node.phy = "zigbee"
        config.duration_s = 900
    elif scenario == "topology_failover":
        config.broker_failover_s = 200
        config.broker_recover_s = 30
        config.moving_gateway_ids = ["gw2"]
        config.gateway_move_interval_s = 60
        config.gateway_move_distance = 15.0
    elif scenario == "topology_failover_clean":
        # All clients use clean sessions (no persistence)
        config.broker_failover_s = 200
        config.broker_recover_s = 30
        config.moving_gateway_ids = ["gw2"]
        config.gateway_move_interval_s = 60
        config.gateway_move_distance = 15.0
        for node in config.nodes:
            node.clean_session = True
    elif scenario == "topology_failover_persist":
        # All clients resume sessions (persistent)
        config.broker_failover_s = 200
        config.broker_recover_s = 30
        config.moving_gateway_ids = ["gw2"]
        config.gateway_move_interval_s = 60
        config.gateway_move_distance = 15.0
        for node in config.nodes:
            node.clean_session = False

    return config


