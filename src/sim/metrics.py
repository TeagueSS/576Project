"""Tracks delivery ratio, latency, duplicates, and energy for the GUI/exports."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, MutableMapping, Set


@dataclass
class MessageInfo:
    """Bookkeeping record for a published MQTT packet."""

    topic: str
    qos: int
    size_bytes: int
    publisher_id: str
    publish_time: float


EventListener = Callable[[Dict[str, Any]], None]


class MetricsCollector:
    """Lightweight aggregator powering experiments and the GUI panels."""

    def __init__(self, latency_window: int = 256) -> None:
        self._published: Dict[str, MessageInfo] = {}
        self._delivered_messages: Set[str] = set()
        self._delivery_latency: Deque[float] = deque(maxlen=latency_window)
        self._delivery_counts: MutableMapping[str, int] = defaultdict(int)
        self._duplicates = 0
        self._energy_joules: MutableMapping[str, float] = defaultdict(float)
        self._listeners: MutableMapping[str, List[EventListener]] = defaultdict(list)

    # ------------------------------------------------------------------
    # listener plumbing
    def on(self, event_type: str, listener: EventListener) -> None:
        """Register a callback that receives metric updates in real time."""

        self._listeners[event_type].append(listener)

    def _notify(self, event_type: str, payload: Dict[str, Any]) -> None:
        for listener in self._listeners.get(event_type, []):
            listener(payload)

    # ------------------------------------------------------------------
    # metric writers
    def record_publish(
        self,
        message_id: str,
        *,
        topic: str,
        qos: int,
        size_bytes: int,
        publisher_id: str,
        timestamp: float,
    ) -> None:
        """Log a new publish so we can compute latency later."""

        self._published[message_id] = MessageInfo(
            topic=topic,
            qos=qos,
            size_bytes=size_bytes,
            publisher_id=publisher_id,
            publish_time=timestamp,
        )
        self._notify(
            "publish",
            {
                "timestamp": timestamp,
                "topic": topic,
                "size_bytes": size_bytes,
            },
        )

    def record_delivery(
        self,
        message_id: str,
        *,
        subscriber_id: str,
        timestamp: float,
        duplicate: bool = False,
    ) -> None:
        """Track that a subscriber received the message (duplicates optional)."""

        info = self._published.get(message_id)
        if info is None:
            return  # unknown (e.g. retained message before sim start)

        latency = max(0.0, timestamp - info.publish_time)
        self._delivery_latency.append(latency)
        self._delivery_counts[subscriber_id] += 1

        if not duplicate and message_id not in self._delivered_messages:
            self._delivered_messages.add(message_id)

        if duplicate:
            self._duplicates += 1

        self._notify(
            "delivery",
            {
                "timestamp": timestamp,
                "latency": latency,
                "duplicate": duplicate,
            },
        )

    def record_energy(self, device_id: str, joules: float) -> None:
        """Accumulate energy consumption per device."""

        if joules < 0:
            raise ValueError("Energy must be non-negative")
        self._energy_joules[device_id] += joules
        self._notify(
            "energy",
            {
                "device_id": device_id,
                "joules": joules,
            },
        )

    # ------------------------------------------------------------------
    # derived stats
    def delivery_ratio(self) -> float:
        """Fraction of published messages that made it to at least one subscriber."""

        total_published = len(self._published)
        if total_published == 0:
            return 0.0
        return len(self._delivered_messages) / total_published

    def average_latency(self) -> float:
        if not self._delivery_latency:
            return 0.0
        return sum(self._delivery_latency) / len(self._delivery_latency)

    def duplicate_count(self) -> int:
        return self._duplicates

    def energy_by_device(self) -> Dict[str, float]:
        return dict(self._energy_joules)

    def summary(self) -> Dict[str, Any]:
        """Small dict for GUI panels/exports."""

        return {
            "delivery_ratio": self.delivery_ratio(),
            "avg_latency": self.average_latency(),
            "duplicates": self.duplicate_count(),
            "total_energy_j": sum(self._energy_joules.values()),
        }
