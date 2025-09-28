"""MQTT network modeling with QoS and session handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import simpy

from sim.metrics import MetricCollector
from sim.utils import rng
from sim.config import SimulationConfig


@dataclass
class MQTTMessage:
    topic: str
    payload: bytes
    qos: int
    retain: bool = False
    dup: bool = False
    msg_id: Optional[int] = None
    sender: Optional[str] = None
    timestamp: float = 0.0


@dataclass
class ClientSession:
    client_id: str
    clean_session: bool
    inflight: Dict[int, MQTTMessage] = field(default_factory=dict)
    subscriptions: Dict[str, int] = field(default_factory=dict)
    connected: bool = True
    last_seen: float = 0.0
    keep_alive: float = 30.0
    pending_retransmit: Dict[int, float] = field(default_factory=dict)
    next_reconnect: float = 0.0
    will_topic: Optional[str] = None
    will_message: Optional[bytes] = None
    will_qos: int = 0


@dataclass
class GatewayLink:
    latency_ms: float
    loss_rate: float


class MQTTNetwork:
    """SimPy-based MQTT broker and clients."""

    def __init__(self, env: simpy.Environment, metrics: MetricCollector, config: SimulationConfig) -> None:
        self.env = env
        self.metrics = metrics
        self.sessions: Dict[str, ClientSession] = {}
        self.retained: Dict[str, MQTTMessage] = {}
        self.broker_queue: list[Tuple[MQTTMessage, GatewayLink]] = []
        self.msg_counter = 1
        self.config = config
        self.gateway_links: Dict[str, GatewayLink] = {
            gw.gateway_id: GatewayLink(gw.wan_latency_ms, gw.wan_loss_rate) for gw in config.gateways
        }
        self.backoff_state: Dict[str, float] = {}
        self.retry_limit = 3
        self.reconnect_queue: list[str] = []
        self.failover_active: bool = False

    def connect(
        self,
        client_id: str,
        clean_session: bool,
        keep_alive: float,
        will: Optional[Tuple[str, bytes, int]] = None,
    ) -> ClientSession:
        session = self.sessions.get(client_id)
        if session and not clean_session:
            session.connected = True
            session.last_seen = self.env.now
            session.keep_alive = keep_alive
            if will:
                session.will_topic, session.will_message, session.will_qos = will
            self.metrics.update_client_state(client_id, "connected")
            return session
        session = ClientSession(client_id=client_id, clean_session=clean_session)
        session.keep_alive = keep_alive
        session.last_seen = self.env.now
        if will:
            session.will_topic, session.will_message, session.will_qos = will
        self.sessions[client_id] = session
        self.metrics.update_client_state(client_id, "connected")
        return session

    def disconnect(self, client_id: str) -> None:
        session = self.sessions.get(client_id)
        if session:
            session.connected = False
            session.last_seen = self.env.now
            if session.will_topic and session.will_message:
                self._queue_message(
                    MQTTMessage(
                        topic=session.will_topic,
                        payload=session.will_message,
                        qos=session.will_qos,
                        retain=False,
                        sender=client_id,
                        timestamp=self.env.now,
                    ),
                    loss_rate=self.config.wan_loss_rate,
                    latency_ms=self.config.wan_latency_ms,
                )
            self.metrics.update_client_state(client_id, "disconnected")

    def publish(
        self,
        client_id: str,
        message: MQTTMessage,
        gateway_id: Optional[str] = None,
    ) -> None:
        message.msg_id = self.msg_counter
        self.msg_counter += 1
        message.sender = client_id
        message.timestamp = self.env.now
        loss_rate = self.config.wan_loss_rate
        latency_ms = self.config.wan_latency_ms
        if gateway_id and gateway_id in self.gateway_links:
            link = self.gateway_links[gateway_id]
            loss_rate = link.loss_rate
            latency_ms = link.latency_ms
        self.metrics.record_send()
        self._queue_message(message, loss_rate=loss_rate, latency_ms=latency_ms)
        if message.retain:
            self.retained[message.topic] = message
        self.sessions[client_id].last_seen = self.env.now

    def subscribe(self, client_id: str, topic: str, qos: int) -> None:
        session = self.sessions[client_id]
        session.subscriptions[topic] = qos
        if topic in self.retained:
            self._deliver(client_id, self.retained[topic], latency_ms=5.0)
        session.last_seen = self.env.now

    def process_queue(self) -> None:
        pending = []
        while self.broker_queue:
            message, link = self.broker_queue.pop(0)
            if rng.random() < link.loss_rate:
                continue
            latency_ms = link.latency_ms + rng.uniform(0, self.config.wan_latency_jitter_ms)
            pending.append((message, latency_ms))
        for message, latency_ms in pending:
            self.metrics.set_broker_queue_depth(len(self.broker_queue))
            for session in self.sessions.values():
                if not session.connected:
                    continue
                for topic, qos in session.subscriptions.items():
                    if self._match(topic, message.topic):
                        dup = False
                        if message.qos == 1:
                            session.inflight[message.msg_id] = message
                            session.pending_retransmit[message.msg_id] = self.env.now + 2 * (latency_ms / 1000.0)
                        if rng.random() < 0.02:
                            dup = True
                            self.metrics.record_duplicate()
                        self.metrics.update_client_state(session.client_id, "connected")
                        self._deliver(session.client_id, message, latency_ms, dup=dup)
                        # Schedule broker-side ack for QoS1
                        if message.qos == 1:
                            self.env.process(self._schedule_ack(session.client_id, message.msg_id, latency_ms))

    def ack(self, client_id: str, msg_id: int) -> None:
        session = self.sessions[client_id]
        session.inflight.pop(msg_id, None)
        session.pending_retransmit.pop(msg_id, None)

    def check_keep_alive(self) -> None:
        now = self.env.now
        for session in self.sessions.values():
            if session.connected and now - session.last_seen > session.keep_alive:
                self.disconnect(session.client_id)
                self._schedule_reconnect(session.client_id)
            elif not session.connected and session.next_reconnect and now >= session.next_reconnect:
                self.reconnect_queue.append(session.client_id)
            to_requeue = []
            for msg_id, deadline in list(session.pending_retransmit.items()):
                if now >= deadline:
                    msg = session.inflight.get(msg_id)
                    if not msg:
                        session.pending_retransmit.pop(msg_id, None)
                        continue
                    retry_count = getattr(msg, "retries", 0)
                    if retry_count >= self.retry_limit:
                        session.pending_retransmit.pop(msg_id, None)
                        session.inflight.pop(msg_id, None)
                        continue
                    msg.retries = retry_count + 1
                    msg.dup = True
                    to_requeue.append(msg)
                    session.pending_retransmit[msg_id] = now + 2
            for msg in to_requeue:
                self._queue_message(msg, loss_rate=self.config.wan_loss_rate, latency_ms=self.config.wan_latency_ms)
        while self.reconnect_queue:
            cid = self.reconnect_queue.pop(0)
            session = self.sessions[cid]
            self.connect(session.client_id, session.clean_session, session.keep_alive)

    def _deliver(self, client_id: str, message: MQTTMessage, latency_ms: float, dup: bool = False) -> None:
        self.metrics.record_delivery(latency_ms)
        if dup:
            self.metrics.record_duplicate()

    @staticmethod
    def _match(subscription: str, topic: str) -> bool:
        if subscription == topic:
            return True
        if subscription.endswith("/#"):
            prefix = subscription[:-2]
            return topic.startswith(prefix)
        return False

    def _queue_message(self, message: MQTTMessage, loss_rate: float, latency_ms: float) -> None:
        # Enforce broker queue capacity
        if len(self.broker_queue) >= self.config.broker.queue_capacity:
            self.metrics.record_queue_drop()
            return
        self.broker_queue.append((message, GatewayLink(latency_ms, loss_rate)))
        self.metrics.set_broker_queue_depth(len(self.broker_queue))
        self.metrics.record_topic(message.topic)

    def _schedule_reconnect(self, client_id: str) -> None:
        backoff = self.backoff_state.get(client_id, self.config.wan_reconnect_backoff[0])
        backoff = min(backoff * 2, self.config.wan_reconnect_backoff[1])
        self.backoff_state[client_id] = backoff
        session = self.sessions[client_id]
        session.next_reconnect = self.env.now + backoff

    def _schedule_ack(self, client_id: str, msg_id: int, latency_ms: float):
        """Simulate PUBACK delivery back to the broker to clear inflight."""
        yield self.env.timeout(latency_ms / 1000.0)
        self.ack(client_id, msg_id)

    # --------- Failover helpers for GUI-triggered events ----------
    def trigger_failover(self, down_seconds: float = 10.0) -> None:
        """Start a broker failover immediately from the current time.

        Disconnects all sessions, marks reconnecting, waits down_seconds, then
        reconnects sessions (respecting clean_session flags).
        """
        if self.failover_active:
            return
        self.failover_active = True

        def _failover_proc():
            # Disconnect everyone
            for session in self.sessions.values():
                session.connected = False
                self.metrics.update_client_state(session.client_id, "reconnecting")
            # Down interval
            yield self.env.timeout(down_seconds)
            # Recover
            for session in self.sessions.values():
                self.connect(session.client_id, session.clean_session, session.keep_alive)
            self.failover_active = False

        self.env.process(_failover_proc())


