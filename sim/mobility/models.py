"""Mobility management for stationary and mobile clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import simpy

from ..utils import rng


@dataclass
class MobilityProfile:
    speed_m_s: float
    pattern: str  # "stationary", "grid", "rwp"


class MobilityManager:
    """Updates client positions according to mobility profiles."""

    def __init__(
        self,
        env: simpy.Environment,
        area: Tuple[int, int],
        initial_positions: Dict[str, Tuple[float, float]],
        mobility_profiles: Dict[str, MobilityProfile],
    ) -> None:
        self.env = env
        self.area = area
        self.positions = dict(initial_positions)
        self.profiles = mobility_profiles
        self.processes = [env.process(self._run(client_id)) for client_id in mobility_profiles]

    def _run(self, client_id: str):
        """Advance the coroutine governing an individual client's movement."""
        profile = self.profiles[client_id]
        while True:
            if profile.pattern == "stationary" or profile.speed_m_s <= 0:
                # Even stationary devices wake occasionally so the map refreshes.
                yield self.env.timeout(5)
                continue
            x, y = self.positions[client_id]
            speed = profile.speed_m_s
            if profile.pattern == "grid":
                dx, dy = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
                nx = min(max(0, x + dx * speed), self.area[0])
                ny = min(max(0, y + dy * speed), self.area[1])
            else:  # random waypoint
                nx = rng.uniform(0, self.area[0])
                ny = rng.uniform(0, self.area[1])
                distance = ((nx - x) ** 2 + (ny - y) ** 2) ** 0.5
                travel_time = max(distance / speed, 1.0)
                steps = max(int(travel_time), 1)
                for step in range(steps):
                    frac = (step + 1) / steps
                    ix = x + (nx - x) * frac
                    iy = y + (ny - y) * frac
                    self.positions[client_id] = (ix, iy)
                    yield self.env.timeout(travel_time / steps)
                continue
            self.positions[client_id] = (nx, ny)
            move_time = max(1.0, 5.0 / speed)
            yield self.env.timeout(move_time)

    def get_position(self, client_id: str) -> Tuple[float, float]:
        """Return current coordinates for diagnostics/tests."""
        return self.positions.get(client_id, (0.0, 0.0))

    def items(self) -> Iterable[Tuple[str, Tuple[float, float]]]:
        """Expose iterator compatible with dict(items())."""
        return self.positions.items()


