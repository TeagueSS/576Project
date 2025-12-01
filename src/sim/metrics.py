from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, MutableMapping, Set


@dataclass
class MessageInfo:
    topic: str
    qos: int
    size_bytes: int
    publisher_id: str
    publish_time: float


class MetricsCollector:
    def __init__(self, latency_window: int = 256) -> None:
        self._published: Dict[str, MessageInfo] = {}
        self._delivered_messages: Set[str] = set()
        self._delivery_latency: Deque[float] = deque(maxlen=latency_window)
        self._duplicates = 0
        self._energy_joules: MutableMapping[str, float] = defaultdict(float)

        # Heatmap History
        self._delivery_history: Deque[tuple] = deque(maxlen=1000)

        # NEW: Track last activity time for visual lines
        self._last_activity: Dict[str, float] = {}

    def record_publish(
        self,
        message_id: str,
        topic: str,
        qos: int,
        size_bytes: int,
        publisher_id: str,
        timestamp: float,
    ) -> None:
        self._published[message_id] = MessageInfo(
            topic, qos, size_bytes, publisher_id, timestamp
        )
        # Record that this node just did something
        self._last_activity[publisher_id] = timestamp

    def record_delivery(
        self,
        message_id: str,
        subscriber_id: str,
        timestamp: float,
        duplicate: bool = False,
    ) -> None:
        info = self._published.get(message_id)
        if info is None:
            return

        latency = max(0.0, timestamp - info.publish_time)
        self._delivery_latency.append(latency)

        if duplicate:
            self._duplicates += 1
        else:
            self._delivered_messages.add(message_id)

        self._delivery_history.append((timestamp, info.topic))

    def record_energy(self, device_id: str, joules: float) -> None:
        self._energy_joules[device_id] += joules

    # --- READERS ---
    def delivery_ratio(self) -> float:
        if not self._published:
            return 0.0
        return len(self._delivered_messages) / len(self._published)

    def average_latency(self) -> float:
        if not self._delivery_latency:
            return 0.0
        return sum(self._delivery_latency) / len(self._delivery_latency)

    def get_topic_rates(
        self, current_time: float, window: float = 2.0
    ) -> Dict[str, float]:
        rates = defaultdict(float)
        cutoff = current_time - window
        for ts, topic in self._delivery_history:
            if ts >= cutoff:
                rates[topic] += 1
        for t in rates:
            rates[t] = rates[t] / window
        return dict(rates)

    # NEW: Get nodes that sent a msg in the last 'window' seconds
    def get_active_publishers(
        self, current_time: float, window: float = 0.5
    ) -> List[str]:
        active = []
        cutoff = current_time - window
        for node_id, last_ts in self._last_activity.items():
            if last_ts >= cutoff:
                active.append(node_id)
        return active

    def summary(self) -> Dict[str, Any]:
        return {
            "delivery_ratio": self.delivery_ratio(),
            "avg_latency": self.average_latency(),
            "duplicates": self._duplicates,
            "total_energy_j": sum(self._energy_joules.values()),
        }
