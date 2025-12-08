import simpy
import random
import math
from ..radios import create_radio
from ..mqtt.client import MqttClient


class SensorNode:
    def __init__(self, env, node_id, pos, radio_type, broker, network_lookup_fn):
        self.env = env
        self.id = node_id
        self.x, self.y = pos
        self.network_lookup_fn = network_lookup_fn

        self.radio = create_radio(radio_type, env)
        self.mqtt = MqttClient(env, node_id, broker, self.radio, self)

        self.battery_j = 1000.0
        self.state = "scanning"
        self.active = True
        self.connected_parent_id = None

        self.topic_root = "sensors"
        if "iPhone" in node_id or "Mobile" in node_id:
            self.topic_root = "mobile"
        elif "Laptop" in node_id:
            self.topic_root = "workstation"

        self.process = self.env.process(self.app_loop())

    def get_network_link(self):
        all_nodes = self.network_lookup_fn()

        # Heuristic: Mesh if range is short (<100m)
        is_mesh = False
        if isinstance(self.radio.config.get('range_m'), (int, float)):
            if self.radio.config['range_m'] < 100: is_mesh = True

        candidates = []
        for n in all_nodes:
            if n.id == self.id: continue

            dist = math.hypot(self.x - n.x, self.y - n.y)
            if not self.radio.can_reach(dist): continue

            # Robust Gateway Check (Partial string match)
            if "Gate" in n.id or getattr(n, "is_gateway", False):
                candidates.append((dist, n.id))
            # Mesh Check: Connect to active sensors if in mesh mode
            elif is_mesh and n.state == "active" and n.active:
                candidates.append((dist, n.id))

        if not candidates: return None
        # Connect to closest valid parent
        candidates.sort(key=lambda x: x[0])
        return candidates[0]

    def consume_energy(self, joules):
        self.battery_j -= joules
        if self.mqtt.broker and hasattr(self.mqtt.broker, 'metrics'):
            metrics = getattr(self.mqtt.broker, 'metrics', None)
            if metrics: metrics.record_energy(self.id, joules)
        if self.battery_j <= 0:
            self.state = "dead"
            self.active = False

    def toggle_connection(self):
        if self.state == "disconnected":
            self.state = "scanning"
            self.mqtt.connected = False
        else:
            self.state = "disconnected"
            self.mqtt.connected = False
            self.connected_parent_id = None

    def stop(self):
        self.active = False
        self.state = "dead"

    def app_loop(self):
        yield self.env.timeout(random.uniform(0, 2))
        while self.active and self.battery_j > 0:
            if self.state == "disconnected":
                yield self.env.timeout(1.0)
                continue

            self.consume_energy(0.05)

            if self.mqtt.connected:
                topic = "unknown"
                if self.topic_root == "mobile":
                    topic = random.choice(["mobile/gps", "mobile/status"])
                elif self.topic_root == "workstation":
                    topic = random.choice(["work/file_sync", "work/email"])
                else:
                    topic = random.choice(["sensors/temp", "sensors/humidity"])

                self.mqtt.publish(topic, 25.0, qos=1)

            yield self.env.timeout(random.uniform(0.8, 2.5))