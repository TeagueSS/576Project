"""BLE 5.x profile: range, rate, energy plus connection-event timing helpers."""

from .abstract_radio import AbstractRadio


class BleRadio(AbstractRadio):
    def calculate_tx_time(self, size_bytes):
        # 2Mbps PHY
        speed_bps = self.config["throughput_kbps"] * 1000 / 8
        # BLE Header overhead
        header = 10
        tx_time = (size_bytes + header) / speed_bps

        # Connection Interval latency (average wait is half interval)
        # Assuming 30ms interval default
        conn_latency = 0.015
        return tx_time + conn_latency

    def get_energy_per_bit(self):
        return self.config["tx_power_mw"]
