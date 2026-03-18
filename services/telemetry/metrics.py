"""
Per-stage timing and counting metrics for the schematic-iq pipeline.

Provides a lightweight ``StageTimer`` context manager and a ``PipelineMetrics``
aggregator that collects timings and counts for a single pipeline run.

Usage:
    from services.telemetry import PipelineMetrics

    metrics = PipelineMetrics()
    with metrics.stage("stage1"):
        geometry = extract_geometry(...)
    metrics.set_counts("stage1", wires=42, chains=8)
    print(metrics.summary())
"""

import time
from contextlib import contextmanager
from typing import Any


class StageTimer:
    """Simple stop-watch for a named pipeline stage."""

    __slots__ = ("name", "start_time", "end_time", "elapsed")

    def __init__(self, name: str):
        self.name = name
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.elapsed: float = 0.0

    def start(self) -> "StageTimer":
        self.start_time = time.perf_counter()
        return self

    def stop(self) -> "StageTimer":
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        return self


class PipelineMetrics:
    """Collect timing and count metrics across pipeline stages."""

    def __init__(self) -> None:
        self._timers: dict[str, StageTimer] = {}
        self._counts: dict[str, dict[str, Any]] = {}

    # -- Timing ---------------------------------------------------------------

    @contextmanager
    def stage(self, name: str):
        """Context manager that times a named stage.

        Usage::

            with metrics.stage("stage1"):
                run_stage_1(...)
        """
        timer = StageTimer(name)
        timer.start()
        try:
            yield timer
        finally:
            timer.stop()
            self._timers[name] = timer

    def get_elapsed(self, name: str) -> float:
        """Return elapsed seconds for *name*, or 0.0 if not recorded."""
        t = self._timers.get(name)
        return t.elapsed if t else 0.0

    @property
    def total_elapsed(self) -> float:
        return sum(t.elapsed for t in self._timers.values())

    # -- Counts ---------------------------------------------------------------

    def set_counts(self, stage: str, **counts: Any) -> None:
        """Record arbitrary counts for a stage (e.g. ``wires=42``)."""
        self._counts.setdefault(stage, {}).update(counts)

    def get_counts(self, stage: str) -> dict[str, Any]:
        return dict(self._counts.get(stage, {}))

    # -- Reporting ------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """Return a JSON-serialisable summary of the pipeline run."""
        stages = {}
        for name in list(self._timers) + [
            k for k in self._counts if k not in self._timers
        ]:
            entry: dict[str, Any] = {}
            if name in self._timers:
                entry["elapsed_s"] = round(self._timers[name].elapsed, 3)
            if name in self._counts:
                entry["counts"] = self._counts[name]
            stages[name] = entry
        return {
            "total_elapsed_s": round(self.total_elapsed, 3),
            "stages": stages,
        }
