import simpy
import random


class MqttBroker:
    def __init__(self, env, metrics_collector):
        self.env = env
        self.metrics = metrics_collector
        self.is_alive = True
        self.last_failover_start = None
        self.last_failover_end = None

        # Map: topic_filter -> list of client_ids
        self.subscriptions = {}
        # Map: topic -> payload (Last Retained)
        self.retained = {}
        # Map: client_id -> queue of messages (Persistent sessions)
        self.client_queues = {}

        # Clients currently online: client_id -> client_instance
        self.connected_clients = {}

    def failover_sequence(self, downtime_s):
        """Simulate a crash and reboot."""
        self.is_alive = False
        self.last_failover_start = float(self.env.now)
        print(f"[{self.env.now:.2f}] !!! BROKER CRASH !!!")

        # NEW: Force disconnect everyone (Simulate TCP Reset)
        # This forces clients to notice the failure and start retrying
        for client in self.connected_clients.values():
            client.connected = False

        # Clear the broker's own list
        self.connected_clients = {}

        yield self.env.timeout(downtime_s)
        self.is_alive = True
        self.last_failover_end = float(self.env.now)
        print(f"[{self.env.now:.2f}] ... BROKER RECOVERED ...")

    def connect(self, client_id, client_instance, clean_session=True):
        if not self.is_alive:
            return False

        # ACK Latency
        yield self.env.timeout(random.uniform(0.01, 0.05))

        self.connected_clients[client_id] = client_instance

        # SESSION MANAGEMENT
        if clean_session:
            # Wipe any previous state
            self.client_queues[client_id] = []
        else:
            # Persistent Session: Restore queue if it exists
            if client_id not in self.client_queues:
                self.client_queues[client_id] = []

            # Deliver all queued messages immediately
            queue_len = len(self.client_queues[client_id])
            if queue_len > 0:
                print(f"[{self.env.now:.2f}] Broker delivering {queue_len} offline msgs to {client_id}")
                for msg in list(self.client_queues[client_id]):
                    self.env.process(self._deliver_msg(client_id, msg))
                self.client_queues[client_id] = []

        return True

    def ping(self, client_id):
        """Handle PINGREQ from client."""
        if not self.is_alive:
            return False
        # PINGRESP is just an ACK
        yield self.env.timeout(random.uniform(0.005, 0.01))
        return True

    def publish(self, sender_id, topic, payload, qos=0, retain=False):
        if not self.is_alive:
            return False

        # 1. Record Publish Metric
        msg_id = f"{sender_id}_{self.env.now}_{random.randint(0, 9999)}"
        self.metrics.record_publish(
            msg_id,
            topic=topic,
            qos=qos,
            size_bytes=len(str(payload)),
            publisher_id=sender_id,
            timestamp=self.env.now,
        )

        if retain:
            self.retained[topic] = payload

        # 2. Find Subscribers (With Wildcard Support)
        matched_clients = set()
        for sub_filter, client_ids in self.subscriptions.items():
            if self._topic_matches(sub_filter, topic):
                for cid in client_ids:
                    matched_clients.add(cid)

        # 3. Distribute
        for sub_id in matched_clients:
            msg = {"topic": topic, "payload": payload, "qos": qos, "id": msg_id}

            if sub_id in self.connected_clients:
                self.env.process(self._deliver_msg(sub_id, msg))
            else:
                # OFFLINE HANDLING
                if sub_id not in self.client_queues:
                    self.client_queues[sub_id] = []
                self.client_queues[sub_id].append(msg)

        # 4. ACK
        if qos > 0:
            yield self.env.timeout(random.uniform(0.01, 0.05))
            return True
        return None

    def subscribe(self, client_id, topic):
        if not self.is_alive:
            return False

        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        if client_id not in self.subscriptions[topic]:
            self.subscriptions[topic].append(client_id)

        # Check retained
        for ret_topic, payload in self.retained.items():
            if self._topic_matches(topic, ret_topic):
                msg = {
                    "topic": ret_topic,
                    "payload": payload,
                    "qos": 0,
                    "id": f"ret_{self.env.now}",
                }
                self.env.process(self._deliver_msg(client_id, msg))

    def _deliver_msg(self, client_id, msg):
        yield self.env.timeout(random.uniform(0.01, 0.05))
        # Verify client is still connected before sending
        if client_id in self.connected_clients:
            self.connected_clients[client_id].on_message(msg)
            # CRITICAL: This updates the metrics!
            self.metrics.record_delivery(
                msg["id"], subscriber_id=client_id, timestamp=self.env.now
            )

    def _topic_matches(self, sub_filter, topic):
        """Basic MQTT wildcard matching."""
        if sub_filter == "#":
            return True
        if sub_filter == topic:
            return True
        return False