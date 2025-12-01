"""Zigbee/802.15.4 profile: low-rate CSMA/CA plus duty-cycle cap helpers."""

from .abstract_radio import AbstractRadio


class ZigbeeRadio(AbstractRadio):
    def calculate_tx_time(self, size_bytes):
        # 250kbps
        speed_bps = self.config["throughput_kbps"] * 1000 / 8
        # Zigbee max payload is small (~127 bytes PHY), huge fragmentation overhead if large
        # We assume simplified packetization
        header = 30  # PHY+MAC
        tx_time = (size_bytes + header) / speed_bps

        # CSMA/CA for 802.15.4 is slower than Wi-Fi
        backoff = 0.002  # 2ms avg backoff
        return tx_time + backoff

    def get_energy_per_bit(self):
        return self.config["tx_power_mw"]
