"""Simplified MAC layer modeling for BLE, Wi-Fi, and Zigbee."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import simpy
from ..utils import rng

from ..phy_profiles import PHY_PROFILES


@dataclass
class MACResult:
    success: bool
    latency_ms: float
    energy_mj: float
    duplicate: bool = False
    duration_s: float = 0.0


class DutyCycleTracker:
    def __init__(self, window_s: float, limit: float) -> None:
        self.window_s = window_s
        self.limit = limit
        self.usage = []

    def can_tx(self, now: float, duration_s: float) -> bool:
        self._prune(now)
        used = sum(end - start for start, end in self.usage)
        return (used + duration_s) / self.window_s <= self.limit

    def record(self, start: float, end: float) -> None:
        self.usage.append((start, end))

    def _prune(self, now: float) -> None:
        horizon = now - self.window_s
        self.usage = [(s, e) for s, e in self.usage if e >= horizon]


class MACScheduler:
    """Provides timing and energy estimates for transmissions."""

    def __init__(self, env: simpy.Environment, zigbee_window_s: float) -> None:
        self.env = env
        self.duty_cycle_trackers: Dict[str, DutyCycleTracker] = {}
        self.zigbee_window_s = zigbee_window_s
        # Simplified MAC timing parameters
        self.ble_conn_interval_s = 0.06  # 60 ms BLE connection interval approximation
        self.wifi_cw_s = 0.003  # 3 ms contention window max
        self.zigbee_cw_s = 0.008  # 8 ms contention window max
        self.ack_success_prob = 0.98

    def tx(
        self,
        node_id: str,
        phy_key: str,
        payload_bits: int,
        csma_delay_sampler: Optional[Callable[[], float]] = None,
        duty_cycle_override: float | None = None,
    ) -> MACResult:
        profile = PHY_PROFILES[phy_key]
        duration_s = payload_bits / (profile.data_rate_mbps * 1e6)
        energy_tx = duration_s * profile.tx_power_mw / 1000.0

        if phy_key == "zigbee" and profile.duty_cycle_limit is not None:
            tracker = self.duty_cycle_trackers.setdefault(
                node_id,
                DutyCycleTracker(
                    self.zigbee_window_s,
                    duty_cycle_override if duty_cycle_override is not None else profile.duty_cycle_limit,
                ),
            )
            if not tracker.can_tx(self.env.now, duration_s):
                return MACResult(success=False, latency_ms=0.0, energy_mj=0.0, duration_s=0.0)

        # BLE connection events: align to next connection interval boundary
        pre_wait_s = 0.0
        if phy_key == "ble":
            # Time until next event boundary
            phase = self.env.now % self.ble_conn_interval_s
            pre_wait_s = (self.ble_conn_interval_s - phase) if phase > 0 else 0.0

        # CSMA/CA backoff approximation for Wi-Fi/Zigbee
        if csma_delay_sampler:
            csma_delay = csma_delay_sampler()
        else:
            if phy_key == "wifi":
                csma_delay = rng.uniform(0, self.wifi_cw_s)
            elif phy_key == "zigbee":
                csma_delay = rng.uniform(0, self.zigbee_cw_s)
            else:
                csma_delay = 0.0

        # Optional MAC ACK with single retry approximation for wifi/zigbee
        mac_retry_s = 0.0
        if phy_key in {"wifi", "zigbee"}:
            if rng.random() > self.ack_success_prob:
                # one retry with additional backoff
                backoff = (self.wifi_cw_s if phy_key == "wifi" else self.zigbee_cw_s)
                mac_retry_s = duration_s + rng.uniform(0, backoff)

        total_tx_time_s = pre_wait_s + csma_delay + duration_s + mac_retry_s
        latency_ms = total_tx_time_s * 1000.0 + profile.tx_latency_ms

        start_time = self.env.now
        # Wait until connection event if BLE
        if pre_wait_s > 0:
            yield self.env.timeout(pre_wait_s)
        # Transmit including CSMA and retry time
        yield self.env.timeout(csma_delay + duration_s + mac_retry_s)
        end_time = self.env.now
        if phy_key == "zigbee" and profile.duty_cycle_limit is not None:
            tracker.record(start_time, end_time)

        return MACResult(success=True, latency_ms=latency_ms, energy_mj=energy_tx, duration_s=(end_time - start_time))


