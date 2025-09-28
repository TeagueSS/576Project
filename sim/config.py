"""Configuration dataclasses for IoT MQTT simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class NodeConfig:
    node_id: str
    phy: str  # key into PHY_PROFILES
    topic: str
    qos: int
    payload_bytes: int
    publish_interval_s: float
    mobility_pattern: str  # "stationary", "grid", "rwp"
    speed_m_s: float
    clean_session: bool = False
    retained: bool = False
    duty_cycle_override: float | None = None
    gateway_id: str | None = None
    will_topic: str | None = None
    will_message: str | None = None
    battery_capacity_mj: float = 500000.0


@dataclass
class GatewayConfig:
    gateway_id: str
    position: Tuple[float, float]
    wan_latency_ms: float
    wan_loss_rate: float
    coverage_radius_m: float = 40.0


@dataclass
class BrokerConfig:
    supervision_timeout_ms: int = 5000
    conn_interval_ms: int = 60
    queue_capacity: int = 500
    ack_delay_ms: int = 30
    failure_recovery_ms: int = 1000


@dataclass
class SimulationConfig:
    area_size: Tuple[int, int]
    nodes: List[NodeConfig]
    gateways: List[GatewayConfig]
    broker: BrokerConfig
    stationary_ratio: float = 0.7
    duration_s: float = 3600.0
    wan_latency_ms: float = 50.0
    wan_latency_jitter_ms: float = 10.0
    wan_reconnect_backoff: Tuple[float, float] = (0.5, 5.0)
    stats_interval_s: float = 5.0
    initial_broker_online: bool = True
    zigbee_duty_cycle_window_s: float = 60.0
    topic_list: List[str] = field(default_factory=list)
    broker_failover_s: float | None = None
    broker_recover_s: float | None = None
    moving_gateway_ids: List[str] = field(default_factory=list)
    gateway_move_interval_s: float = 120.0
    gateway_move_distance: float = 10.0
    wan_loss_rate: float = 0.01




