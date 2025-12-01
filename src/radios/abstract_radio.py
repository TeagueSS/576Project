from abc import ABC, abstractmethod


class AbstractRadio(ABC):
    def __init__(self, env, config):
        self.env = env
        self.config = config

    @abstractmethod
    def calculate_tx_time(self, size_bytes):
        pass

    @abstractmethod
    def get_energy_per_bit(self):
        pass

    def can_reach(self, dist_m):
        # Simple hard cutoff based on range_m from config
        # In a more complex sim, this would use path loss models
        return dist_m <= self.config["range_m"]
