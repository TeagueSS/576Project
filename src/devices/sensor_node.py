import simpy
import random
from ..radios import create_radio
from ..mqtt.client import MqttClient


class SensorNode:
    def __init__(self, env, node_id, pos, radio_type, broker, gateway_lookup_fn):
        self.env = env
        self.id = node_id
        self.x, self.y = pos
        self.gateway_lookup = gateway_lookup_fn

        self.radio = create_radio(radio_type, env)
        self.mqtt = MqttClient(env, node_id, broker, self.radio, self)

        self.battery_j = 1000.0
        self.state = "active"
        self.active = True

        # Determine topics
        self.topic_root = "sensors"
        if "iPhone" in node_id or "Mobile" in node_id:
            self.topic_root = "mobile"

        self.process = self.env.process(self.app_loop())

    def get_distance_to_gateway(self):
        gx, gy = self.gateway_lookup()
        import math

        return math.hypot(self.x - gx, self.y - gy)

    def consume_energy(self, joules):
        self.battery_j -= joules
        # CRITICAL FIX: Report this to the global metrics collector
        # Access path: self.mqtt -> broker -> metrics
        if self.mqtt.broker and self.mqtt.broker.metrics:
            self.mqtt.broker.metrics.record_energy(self.id, joules)

        if self.battery_j <= 0:
            self.state = "dead"
            self.active = False

    def toggle_connection(self):
        if self.state == "disconnected":
            self.state = "active"
            self.mqtt.connected = True  # Force client state
        else:
            self.state = "disconnected"
            self.mqtt.connected = False

    def stop(self):
        self.active = False
        self.state = "dead"

    def app_loop(self):
        yield self.env.timeout(random.uniform(0, 2))
        while self.active and self.battery_j > 0:
            if self.state == "disconnected":
                yield self.env.timeout(1.0)
                continue

            # 1. Report Energy (Idle/Sleep)
            self.consume_energy(0.05)

            # 2. Publish
            if self.mqtt.connected:
                # Varied topics for Heatmap
                if self.topic_root == "mobile":
                    topic = random.choice(["mobile/gps", "mobile/app_data"])
                else:
                    topic = random.choice(
                        ["sensors/temp", "sensors/humid", "sensors/battery"]
                    )

                payload = 20 + random.uniform(-5, 5)
                # This triggers record_publish -> sink triggers record_delivery
                self.mqtt.publish(topic, payload, qos=1)

            yield self.env.timeout(random.uniform(0.5, 2.0))
