"""PHY profile definitions for BLE 5.x, Wi-Fi 802.11n, and Zigbee 802.15.4.

These profiles provide simplified parameters used by the simulation to
approximate data rate, range, and energy usage. The values are not exact but
are within realistic bounds for comparative analysis.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PHYProfile:
    """Container describing simplified characteristics of a PHY layer."""

    name: str
    data_rate_mbps: float
    range_m: float
    tx_power_mw: float
    rx_power_mw: float
    sleep_power_mw: float
    tx_latency_ms: float
    duty_cycle_limit: float | None = None
    notes: str = ""


BLE_PHY = PHYProfile(
    name="BLE 5.x",
    data_rate_mbps=2.0,
    range_m=50.0,
    tx_power_mw=15.0,
    rx_power_mw=10.0,
    sleep_power_mw=0.05,
    tx_latency_ms=7.5,  # connection interval midpoint
    notes="Modeled with periodic connection events and deep sleep between events.",
)

WIFI_PHY = PHYProfile(
    name="Wi-Fi 802.11n",
    data_rate_mbps=72.2,
    range_m=90.0,
    tx_power_mw=320.0,
    rx_power_mw=220.0,
    sleep_power_mw=2.5,
    tx_latency_ms=2.0,
    notes="Simplified CSMA/CA with high throughput but higher energy cost.",
)

ZIGBEE_PHY = PHYProfile(
    name="Zigbee 802.15.4",
    data_rate_mbps=0.25,
    range_m=30.0,
    tx_power_mw=35.0,
    rx_power_mw=20.0,
    sleep_power_mw=0.1,
    tx_latency_ms=15.0,
    duty_cycle_limit=0.1,
    notes="Low data rate with strict duty cycle limits and low power.",
)


PHY_PROFILES = {
    "ble": BLE_PHY,
    "wifi": WIFI_PHY,
    "zigbee": ZIGBEE_PHY,
}


