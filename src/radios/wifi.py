"""Wi-Fi 802.11n profile: CSMA/CA timing, ACK expectations, and power use."""

from .abstract_radio import AbstractRadio
import random


class WifiRadio(AbstractRadio):
    def calculate_tx_time(self, size_bytes):
        # throughput_mbps to bytes per second
        speed_bps = self.config["throughput_mbps"] * 1_000_000 / 8
        # Add basic overhead (PHY preamble + MAC header) ~50 bytes
        total_size = size_bytes + 50
        tx_time = total_size / speed_bps

        # CSMA/CA Backoff simulation (avg of min/max contention window)
        cw = self.config.get("contention_window", [15, 1023])
        slot_time = 9e-6  # 9us
        avg_slots = (cw[0] + cw[1]) / 4  # Rough average backoff
        backoff = avg_slots * slot_time

        return tx_time + backoff

    def get_energy_per_bit(self):
        # Simplification: Power * Time / Bits
        # Handled in device logic mostly, but exposed here
        return self.config["tx_power_mw"]
