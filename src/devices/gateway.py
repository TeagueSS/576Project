"""Gateway bridging wireless nodes to the WAN, enforcing coverage and queues."""

from .sensor_node import SensorNode

class Gateway(SensorNode):
    def __init__(self, env, node_id, pos, broker, gateway_lookup_fn=None):
        super().__init__(env, node_id, pos, "wifi", broker, gateway_lookup_fn)
        self.battery_j = float('inf')
        self.is_gateway = True
        # Coordinator starts Active
        self.state = "active"

    def consume_energy(self, joules): pass

    def get_network_link(self):
        # Gateway is the root, has no parent
        return None

    def app_loop(self):
        while self.active:
            yield self.env.timeout(1.0)