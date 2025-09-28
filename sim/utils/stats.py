"""Statistical helper functions."""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List
from dataclasses import dataclass

from sim.metrics import MetricSnapshot


@dataclass
class ExperimentSummary:
    """Summary statistics for a completed experiment."""
    scenario: str
    delivery_ratio: float
    avg_latency_ms: float
    duplicates: int
    energy_consumed_mj: float
    avg_battery_days: float
    send_events: int
    delivery_events: int


def rolling_mean(values: Deque[float], new_value: float, window: int) -> float:
    values.append(new_value)
    if len(values) > window:
        values.popleft()
    return sum(values) / len(values)


def compute_summary_stats(snapshots: List[MetricSnapshot], scenario_name: str) -> ExperimentSummary:
    """Compute summary statistics from a list of snapshots."""
    if not snapshots:
        return ExperimentSummary(
            scenario=scenario_name,
            delivery_ratio=0.0,
            avg_latency_ms=0.0,
            duplicates=0,
            energy_consumed_mj=0.0,
            avg_battery_days=0.0,
            send_events=0,
            delivery_events=0,
        )
    
    final_snapshot = snapshots[-1]
    
    # Compute average battery life across all clients
    battery_days = list(final_snapshot.battery_estimate_days.values())
    finite_battery_days = [d for d in battery_days if d != float("inf")]
    avg_battery_days = sum(finite_battery_days) / len(finite_battery_days) if finite_battery_days else float("inf")
    
    return ExperimentSummary(
        scenario=scenario_name,
        delivery_ratio=final_snapshot.delivery_ratio,
        avg_latency_ms=final_snapshot.avg_latency_ms,
        duplicates=final_snapshot.duplicates,
        energy_consumed_mj=final_snapshot.energy_consumed_mj,
        avg_battery_days=avg_battery_days,
        send_events=final_snapshot.send_events,
        delivery_events=final_snapshot.delivery_events,
    )


__all__ = ["rolling_mean", "compute_summary_stats", "ExperimentSummary"]


