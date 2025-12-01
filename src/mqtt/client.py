import simpy
import random


class MqttClient:
    def __init__(self, env, client_id, broker, radio, parent_node):
        self.env = env
        self.client_id = client_id
        self.broker = broker
        self.radio = radio
        self.node = parent_node

        self.connected = False
        self.backoff = 1.0
        self.msg_queue = []

        self.env.process(self.network_loop())

    def network_loop(self):
        while True:
            # 1. Manual Disconnect Check
            if self.node.state == "disconnected":
                self.connected = False
                yield self.env.timeout(1.0)
                continue

            # 2. Connection Handling
            if not self.connected:
                yield self.env.process(self.attempt_connect())

            # 3. Message Processing
            if self.connected and self.msg_queue:
                msg = self.msg_queue.pop(0)
                yield self.env.process(self.send_publish(msg))
            else:
                yield self.env.timeout(0.1)

    def attempt_connect(self):
        # Range Check
        gw_dist = self.node.get_distance_to_gateway()
        if not self.radio.can_reach(gw_dist):
            self.connected = False
            yield self.env.timeout(1.0)  # Out of range, wait
            return

        # Physics Simulation
        tx_time = self.radio.calculate_tx_time(60)
        yield self.env.timeout(tx_time)

        p_mw = self.radio.config["tx_power_mw"]
        if hasattr(self.node, "consume_energy"):
            self.node.consume_energy(p_mw * tx_time / 1000)

        # Broker Handshake
        success = yield self.env.process(self.broker.connect(self.client_id, self))

        if success:
            self.connected = True
            self.backoff = 1.0
        else:
            wait = self.backoff + random.uniform(0, 1)
            yield self.env.timeout(wait)
            self.backoff = min(self.backoff * 2, 60)

    def publish(self, topic, payload, qos=0):
        if self.node.state != "disconnected":
            self.msg_queue.append({"t": topic, "p": payload, "q": qos})

    def send_publish(self, msg):
        # --- CRITICAL FIX: CONTINUOUS RANGE CHECK ---
        gw_dist = self.node.get_distance_to_gateway()

        if not self.radio.can_reach(gw_dist):
            # Signal Lost! Drop connection immediately.
            self.connected = False
            # Put message back in front of queue (QoS behavior)
            self.msg_queue.insert(0, msg)
            return
        # ---------------------------------------------

        payload_size = len(str(msg["p"]))
        tx_time = self.radio.calculate_tx_time(payload_size)

        yield self.env.timeout(tx_time)

        p_mw = self.radio.config["tx_power_mw"]
        if hasattr(self.node, "consume_energy"):
            self.node.consume_energy(p_mw * tx_time / 1000)

        try:
            ack = yield self.env.process(
                self.broker.publish(self.client_id, msg["t"], msg["p"], msg["q"])
            )
            if msg["q"] > 0 and not ack:
                yield self.env.timeout(1.0)
                self.msg_queue.insert(0, msg)
        except Exception:
            self.connected = False

    def on_message(self, msg):
        rx_time = self.radio.calculate_tx_time(len(str(msg["payload"])))
        p_mw = self.radio.config["rx_power_mw"]
        if hasattr(self.node, "consume_energy"):
            self.node.consume_energy(p_mw * rx_time / 1000)
