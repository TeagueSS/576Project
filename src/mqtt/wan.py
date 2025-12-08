"""Models WAN latency/loss between gateway and cloud broker."""

import random

class WanLink:
    def __init__(self, env, latency_ms=(50, 200), loss_rate=0.01):
        self.env = env
        self.latency_range = (latency_ms[0]/1000.0, latency_ms[1]/1000.0)
        self.loss_rate = loss_rate

    def send(self, destination_callback, *args, **kwargs):
        """
        Simulates sending a packet over WAN.
        :param destination_callback: The function to call when packet arrives (e.g., broker.publish)
        :param args: Arguments to pass to the callback
        """
        return self.env.process(self._transmission_process(destination_callback, args, kwargs))

    def _transmission_process(self, callback, args, kwargs):
        # 1. Calculate Delay
        delay = random.uniform(*self.latency_range)
        yield self.env.timeout(delay)

        # 2. Check for Packet Loss
        if random.random() < self.loss_rate:
            # Packet dropped silently
            return None

        # 3. Deliver
        # If the destination is a coroutine (SimPy process), yield it
        result = callback(*args, **kwargs)
        if hasattr(result, 'callbacks'):  # Basic check if it's a SimPy event/process
            yield result
        return result