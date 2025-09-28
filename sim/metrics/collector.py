"""Metrics collection and aggregation for the IoT MQTT simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class MetricSnapshot:
    timestamp: float
    delivery_ratio: float
    avg_latency_ms: float
    duplicates: int
    energy_consumed_mj: float
    broker_queue_depth: int
    send_events: int = 0
    delivery_events: int = 0
    topic_rates: Dict[str, float] = field(default_factory=dict)
    client_states: Dict[str, str] = field(default_factory=dict)
    energy_per_client: Dict[str, float] = field(default_factory=dict)
    positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    battery_estimate_days: Dict[str, float] = field(default_factory=dict)
    gateways: Dict[str, Dict[str, float]] = field(default_factory=dict)
    sleep_ratio_avg: float = 0.0
    queue_drops: int = 0
    time_to_restore_s: float = 0.0


@dataclass
class MetricCollector:
    """Collects time series metrics during a simulation run."""

    delivery_events: int = 0
    send_events: int = 0
    duplicate_events: int = 0
    total_latency_ms: float = 0.0
    latency_samples: int = 0
    energy_mj: Dict[str, float] = field(default_factory=dict)
    broker_queue_depth: int = 0
    snapshots: List[MetricSnapshot] = field(default_factory=list)
    topic_counts: Dict[str, int] = field(default_factory=dict)
    client_states: Dict[str, str] = field(default_factory=dict)
    snapshot_interval_s: float = 5.0
    last_snapshot_time: float = 0.0
    positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    battery_capacity_mj: Dict[str, float] = field(default_factory=dict)
    gateways: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Radio state accounting (seconds)
    radio_tx_s: Dict[str, float] = field(default_factory=dict)
    radio_sleep_s: Dict[str, float] = field(default_factory=dict)
    radio_rx_s: Dict[str, float] = field(default_factory=dict)
    queue_drops: int = 0
    # Restore metrics
    failover_time_s: float = 0.0
    restored_time_s: float = 0.0

    def record_send(self) -> None:
        """Capture a transmit attempt from any client."""
        self.send_events += 1

    def record_delivery(self, latency_ms: float) -> None:
        """Record an end-to-end delivery and accumulate latency stats."""
        self.delivery_events += 1
        self.total_latency_ms += latency_ms
        self.latency_samples += 1

    def record_duplicate(self) -> None:
        """Increment duplicate counter for QoS1 retransmissions / dup detection."""
        self.duplicate_events += 1

    def record_energy(self, client_id: str, energy_mj_total: float) -> None:
        """Track cumulative energy per client in millijoules."""
        self.energy_mj[client_id] = energy_mj_total

    def record_radio_tx(self, client_id: str, seconds: float) -> None:
        self.radio_tx_s[client_id] = self.radio_tx_s.get(client_id, 0.0) + max(0.0, seconds)

    def record_radio_sleep(self, client_id: str, seconds: float) -> None:
        self.radio_sleep_s[client_id] = self.radio_sleep_s.get(client_id, 0.0) + max(0.0, seconds)

    def record_radio_rx(self, client_id: str, seconds: float) -> None:
        self.radio_rx_s[client_id] = self.radio_rx_s.get(client_id, 0.0) + max(0.0, seconds)

    def record_queue_drop(self) -> None:
        self.queue_drops += 1

    def set_broker_queue_depth(self, depth: int) -> None:
        """Expose instantaneous broker queue depth for sparkline visual."""
        self.broker_queue_depth = depth

    def record_topic(self, topic: str) -> None:
        """Tally topic usage for heatmap rates."""
        self.topic_counts[topic] = self.topic_counts.get(topic, 0) + 1

    def update_client_state(self, client_id: str, state: str) -> None:
        """Persist latest connection state (connected/reconnecting/etc.)."""
        self.client_states[client_id] = state

    def update_positions(self, positions: Dict[str, Tuple[float, float]]) -> None:
        """Provide latest mobility coordinates for map rendering."""
        self.positions = dict(positions)

    def update_gateways(self, gateways) -> None:
        """Expose gateway placement/range for map overlays."""
        self.gateways = dict(gateways)

    def snapshot(self, timestamp: float) -> MetricSnapshot:
        """Materialize a point-in-time snapshot consumed by the GUI."""
        delivery_ratio = (self.delivery_events / self.send_events) if self.send_events else 0.0
        avg_latency = (self.total_latency_ms / self.latency_samples) if self.latency_samples else 0.0
        total_energy = sum(self.energy_mj.values())
        elapsed = timestamp - self.last_snapshot_time if self.last_snapshot_time else self.snapshot_interval_s
        elapsed = max(elapsed, 1e-6)
        topic_rates = {topic: count / elapsed for topic, count in self.topic_counts.items()}
        battery_estimate = {}
        for client_id, capacity in self.battery_capacity_mj.items():
            consumption = self.energy_mj.get(client_id, 0.0)
            if consumption <= 0:
                battery_estimate[client_id] = float("inf")
            else:
                battery_estimate[client_id] = capacity / consumption * (timestamp / 86400 if timestamp else 1)
        # Sleep ratio: sleep / (tx+rx+sleep) averaged across clients
        sleep_ratios = []
        for cid in set().union(self.radio_tx_s.keys(), self.radio_rx_s.keys(), self.radio_sleep_s.keys()):
            tx = self.radio_tx_s.get(cid, 0.0)
            rx = self.radio_rx_s.get(cid, 0.0)
            sl = self.radio_sleep_s.get(cid, 0.0)
            total = tx + rx + sl
            if total > 0:
                sleep_ratios.append(sl / total)
        sleep_ratio_avg = sum(sleep_ratios) / len(sleep_ratios) if sleep_ratios else 0.0

        snap = MetricSnapshot(
            timestamp=timestamp,
            delivery_ratio=delivery_ratio,
            avg_latency_ms=avg_latency,
            duplicates=self.duplicate_events,
            energy_consumed_mj=total_energy,
            broker_queue_depth=self.broker_queue_depth,
            send_events=self.send_events,
            delivery_events=self.delivery_events,
            topic_rates=topic_rates,
            client_states=dict(self.client_states),
            energy_per_client=dict(self.energy_mj),
            positions=dict(self.positions),
            battery_estimate_days=battery_estimate,
            gateways=dict(self.gateways),
            sleep_ratio_avg=sleep_ratio_avg,
            queue_drops=self.queue_drops,
            time_to_restore_s=self.restored_time_s if self.restored_time_s else 0.0,
        )
        self.snapshots.append(snap)
        self.topic_counts.clear()
        self.last_snapshot_time = timestamp
        return snap

    def reset(self) -> None:
        """Clear state between experiments."""
        self.delivery_events = 0
        self.send_events = 0
        self.duplicate_events = 0
        self.total_latency_ms = 0.0
        self.latency_samples = 0
        self.energy_mj.clear()
        self.snapshots.clear()
        self.broker_queue_depth = 0
        self.topic_counts.clear()
        self.client_states.clear()
        self.last_snapshot_time = 0.0
        self.positions.clear()



