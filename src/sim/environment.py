"""Creates the SimPy env and exposes helpers to register devices and clocks.

This module keeps the simulation plumbing tiny but explicit:

* we wrap ``simpy.Environment`` so the rest of the project can share one
  canonical clock and RNG seed without re-creating envs in every test;
* we provide helper hooks for registering long-running device processes and
  for scheduling periodic callbacks (useful for keep-alive timers, GUI polls,
  etc.) so experiments do not have to sprinkle raw SimPy boilerplate
  everywhere;
* we expose a thin RNG helper because most modules will need deterministic
  randomness (e.g., CSMA backoff, mobility) to make experiments reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

import random
import simpy

ProcessFactory = Callable[[simpy.Environment], simpy.events.Process]
PeriodicCallback = Callable[[simpy.Environment], None]


@dataclass
class SimulationEnvironment:
    """Thin wrapper around ``simpy.Environment`` with helpful utilities.

    The class keeps track of registered device processes (useful for
    debugging), exposes a seeded ``random.Random`` instance so every module is
    reproducible, and provides ``run``/``timeout`` helpers to reduce boilerplate
    when wiring up experiments.
    """

    seed: int = 0
    default_until: Optional[float] = None
    env: simpy.Environment = field(init=False)
    rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.env = simpy.Environment()
        self.rng = random.Random(self.seed)
        self._processes: Dict[str, simpy.events.Process] = {}

    # ------------------------------------------------------------------
    # basic helpers
    @property
    def now(self) -> float:
        """Current simulation timestamp (seconds)."""

        return float(self.env.now)

    def timeout(self, duration: float) -> simpy.events.Timeout:
        """Shortcut for ``env.timeout`` to keep call-sites tidy."""

        if duration < 0:
            raise ValueError("Timeout duration must be non-negative")
        return self.env.timeout(duration)

    # ------------------------------------------------------------------
    # process management
    def register_process(
        self,
        name: str,
        generator_factory: ProcessFactory,
    ) -> simpy.events.Process:
        """Register and start a device/process by name.

        ``generator_factory`` receives the underlying SimPy environment and
        must return a generator (or ``Process``) that can be scheduled.
        """

        if name in self._processes:
            raise ValueError(f"Process '{name}' already registered")
        process = self.env.process(generator_factory(self.env))
        self._processes[name] = process
        return process

    def cancel_process(self, name: str) -> None:
        """Stop a registered process if it is still alive."""

        process = self._processes.pop(name, None)
        if process is not None and not process.triggered:
            process.interrupt("cancelled")

    # ------------------------------------------------------------------
    # periodic scheduling utilities
    def schedule_periodic(
        self,
        name: str,
        interval: float,
        callback: PeriodicCallback,
        start_after: float = 0.0,
    ) -> None:
        """Schedule a callback that runs every ``interval`` seconds.

        The callback receives the raw SimPy environment so it can register
        events/timeouts as needed (e.g., send keep-alive pings). ``name`` is
        used to register the backing process for debugging/cleanup.
        """

        if interval <= 0:
            raise ValueError("interval must be positive")

        def periodic(env: simpy.Environment):
            yield env.timeout(start_after)
            while True:
                callback(env)
                yield env.timeout(interval)

        self.register_process(name, periodic)

    # ------------------------------------------------------------------
    # run helpers
    def run(self, until: Optional[float] = None) -> None:
        """Advance the simulation clock until ``until`` (or default)."""

        target = until if until is not None else self.default_until
        self.env.run(until=target)

    # ------------------------------------------------------------------
    # diagnostics
    def describe_processes(self) -> Dict[str, str]:
        """Return a summary of registered processes for debugging/GUI."""

        summary: Dict[str, str] = {}
        for name, process in self._processes.items():
            status = "done" if process.processed else "active"
            summary[name] = status
        return summary
