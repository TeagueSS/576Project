import simpy
import random
from ..devices.sensor_node import SensorNode
from ..mqtt.broker import MqttBroker
from ..mobility.random_waypoint import RandomWaypoint


class ScenarioLoader:
    def __init__(self, env, metrics):
        self.env = env
        self.metrics = metrics
        self.nodes = []
        self.broker = MqttBroker(env, metrics)
        self.gw_pos = (100, 100)

        # NEW: Global setting for the current experiment
        self.active_protocol = "zigbee"

        # Create Sink
        self.sink_client = SinkSubscriber(env, self.broker)

    def load_experiment(self, protocol_mode="zigbee"):
        """Resets and loads a fresh scenario with the specific protocol."""
        self.nodes = []
        self.active_protocol = protocol_mode.lower()  # ble, wifi, or zigbee
        self.gw_pos = (100, 100)

        # Default Topology
        self.add_dynamic_node("Gateway", 100, 100)
        self.add_dynamic_node("Sensor", 80, 80)
        self.add_dynamic_node("Sensor", 120, 120)
        self.add_dynamic_node("Mobile", 50, 150)

    def add_dynamic_node(self, node_type, x, y):
        clean_type = node_type.replace("Add ", "").split()[0]
        new_id = f"{clean_type[:3]}_{random.randint(100, 999)}"

        # --- PROTOCOL SELECTION LOGIC ---
        # Gateways always need to support the active protocol + Backhaul
        # Mobiles/Sensors use the Active Protocol (for E2 comparison)

        if clean_type == "Gateway":
            # Gateway effectively acts as the radio hub for the chosen protocol
            radio = self.active_protocol
        elif clean_type == "Mobile" or clean_type == "iPhone":
            radio = self.active_protocol
        else:
            radio = self.active_protocol

        # Create Node
        node = SensorNode(
            self.env, new_id, (x, y), radio, self.broker, lambda: self.gw_pos
        )

        if clean_type in ["Mobile", "iPhone"]:
            node.is_mobile = True
            RandomWaypoint(self.env, node)

        self.nodes.append(node)
        return node

    def remove_node(self, node_id):
        for n in self.nodes:
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
                    # Pass the protocol to GUI so it knows how big to draw the circle
                    "protocol": self.active_protocol,
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
