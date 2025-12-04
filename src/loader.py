import random
from .devices.sensor_node import SensorNode
from .mqtt.broker import MqttBroker
from .mobility.random_waypoint import RandomWaypoint


class ScenarioLoader:
    """
    Lightweight replacement for the removed experiments/ folder.
    Provides basic topology setup and GUI node data.
    """

    def __init__(self, env, metrics):
        self.env = env
        self.metrics = metrics
        self.nodes = []
        self.broker = MqttBroker(env, metrics)
        self.gw_pos = (100, 100)
        self.active_protocol = "zigbee"

    def load_experiment(self, protocol_mode="zigbee"):
        """Set up a basic topology with the chosen protocol."""
        self.nodes = []
        self.active_protocol = protocol_mode.lower()
        self.gw_pos = (100, 100)

        # Default topology: one gateway, two sensors, one mobile
        self.add_dynamic_node("Gateway", 100, 100)
        self.add_dynamic_node("Sensor", 80, 80)
        self.add_dynamic_node("Sensor", 120, 120)
        self.add_dynamic_node("Mobile", 50, 150)

    def add_dynamic_node(self, node_type, x, y):
        clean_type = node_type.replace("Add ", "").split()[0]
        new_id = f"{clean_type[:3]}_{random.randint(100, 999)}"

        # All nodes use the active protocol
        radio = self.active_protocol

        node = SensorNode(
            self.env, new_id, (x, y), radio, self.broker, lambda: self.gw_pos
        )

        if clean_type in ["Mobile", "iPhone"]:
            node.is_mobile = True
            RandomWaypoint(self.env, node)

        self.nodes.append(node)
        return node

    def remove_node(self, node_id):
        for n in list(self.nodes):
            if n.id == node_id:
                n.stop()
                self.nodes.remove(n)
                break

    def get_node(self, node_id):
        return next((n for n in self.nodes if n.id == node_id), None)

    def get_gui_node_data(self):
        data = []
        for n in self.nodes:
            ntype = "Sensor"
            if getattr(n, "is_mobile", False):
                ntype = "Mobile"
            if "Gateway" in n.id or "Gat" in n.id:
                ntype = "Gateway"

            data.append(
                {
                    "id": n.id,
                    "x": n.x,
                    "y": n.y,
                    "type": ntype,
                    "state": n.state,
                    "ip": "10.0.0.1",
                    "battery": int(max(0, (n.battery_j / 1000.0) * 100)),
                    "protocol": self.active_protocol,
                    # Connection info (for map lines)
                    "mqtt_connected": getattr(n.mqtt, "connected", False),
                    "in_range": n.mqtt.radio.can_reach(n.get_distance_to_gateway())
                    if hasattr(n, "mqtt")
                    else True,
                    "distance": n.get_distance_to_gateway()
                    if hasattr(n, "get_distance_to_gateway")
                    else 0,
                }
            )
        return data


class SinkSubscriber:
    def __init__(self, env, broker):
        self.env = env
        self.broker = broker
        self.id = "CLOUD_SINK"
        self.env.process(self.start())

    def start(self):
        yield self.env.process(self.broker.connect(self.id, self))
        self.broker.subscribe(self.id, "#")

    def on_message(self, msg):
        pass

