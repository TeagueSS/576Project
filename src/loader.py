import random
import math
from .devices.sensor_node import SensorNode
from .devices.gateway import Gateway
from .mqtt.broker import MqttBroker
from .mqtt.wan import WanLink
from .mobility.random_waypoint import RandomWaypoint
from .mobility.grid import GridMobility


class WanBrokerProxy:
    def __init__(self, real_broker, wan_link):
        self.real_broker = real_broker
        self.wan_link = wan_link

    @property
    def is_alive(self): return self.real_broker.is_alive

    @property
    def metrics(self): return self.real_broker.metrics

    def connect(self, client_id, client_instance, clean_session=True):
        return self.real_broker.connect(client_id, client_instance, clean_session)

    def publish(self, sender_id, topic, payload, qos=0, retain=False):
        return self.wan_link.send(self.real_broker.publish, sender_id, topic, payload, qos, retain)

    def subscribe(self, client_id, topic):
        return self.real_broker.subscribe(client_id, topic)


class ScenarioLoader:
    def __init__(self, env, metrics):
        self.env = env
        self.metrics = metrics
        self.nodes = []
        self.broker = MqttBroker(env, metrics)
        self.wan_link = WanLink(env, latency_ms=(100, 300), loss_rate=0.01)
        self.cloud_broker_proxy = WanBrokerProxy(self.broker, self.wan_link)
        self.gw_pos = (250, 250)
        self.active_protocol = "zigbee"
        self.sink = SinkSubscriber(env, self.broker)

    def _get_network_nodes(self):
        return self.nodes

    def load_experiment(self, selection_str="E3"):
        self.nodes = []
        sel = selection_str.lower()
        self.gw_pos = (250, 250)

        if "wifi" in sel or "wi-fi" in sel:
            self.active_protocol = "wifi"
        elif "ble" in sel:
            self.active_protocol = "ble"
        else:
            self.active_protocol = "zigbee"

        if "e1" in sel:
            self._setup_e1_duty_cycle()
        elif "e2" in sel:
            self._setup_e2_comparison()
        elif "e3" in sel:
            self._setup_e3_failover()
        elif "zigbee only" in sel:
            self._setup_zigbee_industrial()
        elif "wi-fi only" in sel:
            self._setup_wifi_office()
        elif "ble only" in sel:
            self._setup_ble_tracking()
        elif "ad-hoc" in sel:
            self._setup_adhoc_mesh()
        else:
            self._setup_e3_failover()

    def _setup_e1_duty_cycle(self):
        # Tighter spacing for Zigbee (Range ~30m)
        self.add_dynamic_node("Gateway", 250, 250)
        self.add_dynamic_node("Sensor", 250, 230)  # 20m dist
        self.add_dynamic_node("Sensor", 250, 210)
        self.add_dynamic_node("Sensor", 270, 250)
        self.add_dynamic_node("Sensor", 290, 250)

    def _setup_e2_comparison(self):
        self.add_dynamic_node("Gateway", 250, 250)
        self.add_dynamic_node("Sensor", 280, 250)
        self.add_dynamic_node("Sensor", 320, 250)
        self.add_dynamic_node("Sensor", 400, 250)

    def _setup_e3_failover(self):
        self.add_dynamic_node("Gateway", 250, 250)
        self.add_dynamic_node("iPhone", 150, 250, is_mobile=True)
        self.add_dynamic_node("Laptop", 350, 250)

    def _setup_zigbee_industrial(self):
        self.add_dynamic_node("Gateway", 250, 250)
        self.add_dynamic_node("Sensor", 250, 230)  # Close
        self.add_dynamic_node("Sensor", 250, 210)  # Daisy chain
        self.add_dynamic_node("Asset Tag", 230, 250, is_mobile=True)

    def _setup_wifi_office(self):
        self.add_dynamic_node("Gateway", 250, 250)
        self.add_dynamic_node("Laptop", 280, 250)
        self.add_dynamic_node("iPhone", 200, 200, is_mobile=True)

    def _setup_ble_tracking(self):
        self.add_dynamic_node("Gateway", 250, 250)
        self.add_dynamic_node("Beacon", 230, 250)
        self.add_dynamic_node("Beacon", 270, 250)
        self.add_dynamic_node("Wearable", 250, 220, is_mobile=True)

    def _setup_adhoc_mesh(self):
        self.add_dynamic_node("Source Node", 100, 250)
        self.add_dynamic_node("Ad-Hoc Relay", 150, 250)
        self.add_dynamic_node("Ad-Hoc Relay", 200, 250)
        self.add_dynamic_node("Sink Node", 250, 250)

    def add_dynamic_node(self, node_type, x, y, is_mobile=False):
        clean_type = node_type.replace("Add ", "").split()[0]
        if clean_type in ["iPhone", "Mobile", "Wearable", "Asset Tag"]:
            is_mobile = True

        new_id = f"{clean_type[:4]}_{random.randint(100, 999)}"
        radio = self.active_protocol

        if "Gateway" in clean_type:
            node = Gateway(self.env, new_id, (x, y), self.cloud_broker_proxy, self._get_network_nodes)
            self.gw_pos = (x, y)
            node.is_gateway = True
        else:
            node = SensorNode(self.env, new_id, (x, y), radio, self.broker, self._get_network_nodes)

        if is_mobile:
            node.is_mobile = True
            GridMobility(self.env, node, bounds=(0, 500))

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
        parent_map = {}
        for n in self.nodes:
            if hasattr(n, 'connected_parent_id') and n.connected_parent_id:
                p = n.connected_parent_id
                parent_map[p] = parent_map.get(p, 0) + 1

        for n in self.nodes:
            ntype = "Sensor"
            if getattr(n, "is_gateway", False) or "Gateway" in n.id:
                ntype = "Gateway"
            elif "Laptop" in n.id:
                ntype = "Laptop"
            elif "iPhone" in n.id:
                ntype = "iPhone"
            elif "Asset" in n.id:
                ntype = "Asset Tag"
            elif "Beacon" in n.id:
                ntype = "Beacon"
            elif "Wearable" in n.id:
                ntype = "Wearable"
            elif "Relay" in n.id:
                ntype = "Ad-Hoc Relay"
            elif "Source" in n.id:
                ntype = "Source Node"
            elif "Sink" in n.id:
                ntype = "Sink Node"

            connected = False
            parent = None
            retries = 0
            next_retry = 0.0

            if hasattr(n, "mqtt"):
                connected = n.mqtt.connected
                parent = n.connected_parent_id
                # <--- EXTRACT STATS --->
                if not connected:
                    retries = getattr(n.mqtt, 'retry_count', 0)
                    next_retry = getattr(n.mqtt, 'backoff', 0.0)

            # Color Logic:
            visual_state = n.state
            if ntype == "Gateway":
                visual_state = "active" if parent_map.get(n.id, 0) > 0 else "scanning"
            else:
                if connected and n.state != "dead":
                    visual_state = "active"
                elif not connected and n.state == "active":
                    visual_state = "scanning"

            batt = 100
            if n.battery_j != float('inf'):
                batt = int(max(0, (n.battery_j / 1000.0) * 100))

            data.append({
                "id": n.id, "x": n.x, "y": n.y, "type": ntype, "state": visual_state,
                "battery": batt, "protocol": self.active_protocol,
                "mqtt_connected": connected,
                "parent_id": parent,
                "retries": retries,
                "next_retry": next_retry
            })
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

    def on_message(self, msg): pass