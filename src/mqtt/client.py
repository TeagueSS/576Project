import simpy
import random


class MqttClient:
    def __init__(self, env, client_id, broker, radio, parent_node, clean_session=True):
        self.env = env
        self.client_id = client_id
        self.broker = broker
        self.radio = radio
        self.node = parent_node
        self.clean_session = clean_session

        self.connected = False
        self.backoff = 1.0
        self.msg_queue = []
        self.keep_alive = 10.0
        self.last_packet_time = 0.0

        self.env.process(self.network_loop())

    def network_loop(self):
        while True:
            if self.node.state == "disconnected":
                self.connected = False
                yield self.env.timeout(1.0)
                continue

            if not self.broker.is_alive:
                self.connected = False
                if self.node.state == "active":
                    self.node.state = "broker_down"
                yield self.env.timeout(0.5)
                continue

            if not self.connected:
                yield self.env.process(self.attempt_connect())

            if self.connected and self.msg_queue:
                msg = self.msg_queue.pop(0)
                yield self.env.process(self.send_publish(msg))
                self.last_packet_time = self.env.now

            elif self.connected and (self.env.now - self.last_packet_time > self.keep_alive):
                yield self.env.process(self.send_ping())
                self.last_packet_time = self.env.now

            else:
                yield self.env.timeout(0.1)

    def attempt_connect(self):
        # NEW: Check Network Link (Mesh aware)
        link = self.node.get_network_link()

        if not link:
            self.connected = False
            if self.node.state != "disconnected":
                self.node.state = "scanning"
            yield self.env.timeout(1.0)
            return

        # Link found!
        dist, parent_id = link

        tx_time = self.radio.calculate_tx_time(60)
        yield self.env.timeout(tx_time)
        self._consume_energy(tx_time)

        try:
            success = yield self.env.process(
                self.broker.connect(self.client_id, self, clean_session=self.clean_session)
            )
        except Exception:
            success = False

        if success:
            self.connected = True
            self.backoff = 1.0
            self.last_packet_time = self.env.now
            # Store parent for lines
            self.node.connected_parent_id = parent_id

            if self.node.state in ("broker_down", "disconnected", "scanning"):
                self.node.state = "active"
        else:
            wait = self.backoff + random.uniform(0, 1)
            yield self.env.timeout(wait)
            self.backoff = min(self.backoff * 2, 60)

    def publish(self, topic, payload, qos=0):
        if self.node.state != "disconnected":
            self.msg_queue.append({"t": topic, "p": payload, "q": qos})

    def send_publish(self, msg):
        link = self.node.get_network_link()
        if not link:
            self.connected = False
            if self.node.state != "disconnected": self.node.state = "scanning"
            self.node.connected_parent_id = None
            self.msg_queue.insert(0, msg)
            return

        payload_size = len(str(msg["p"]))
        tx_time = self.radio.calculate_tx_time(payload_size)
        yield self.env.timeout(tx_time)
        self._consume_energy(tx_time)

        try:
            ack = yield self.env.process(
                self.broker.publish(self.client_id, msg["t"], msg["p"], msg["q"])
            )
            if msg["q"] > 0 and not ack:
                yield self.env.timeout(1.0)
                self.msg_queue.insert(0, msg)
        except Exception:
            self.connected = False

    def send_ping(self):
        tx_time = self.radio.calculate_tx_time(2)
        yield self.env.timeout(tx_time)
        self._consume_energy(tx_time)
        try:
            if hasattr(self.broker, 'ping'):
                yield self.env.process(self.broker.ping(self.client_id))
            else:
                yield self.env.timeout(0.01)
        except Exception:
            self.connected = False

    def on_message(self, msg):
        rx_time = self.radio.calculate_tx_time(len(str(msg["payload"])))
        p_mw = self.radio.config["rx_power_mw"]
        if hasattr(self.node, "consume_energy"):
            self.node.consume_energy(p_mw * rx_time / 1000)

    def _consume_energy(self, duration_sec):
        p_mw = self.radio.config["tx_power_mw"]
        if hasattr(self.node, "consume_energy"):
            self.node.consume_energy(p_mw * duration_sec / 1000)