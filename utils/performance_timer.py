"""
Performance Timer Utility.
Reusable timing instrumentation for pipeline profiling.
"""

import time


class PipelineTimer:
    """
    Lightweight step timer for pipeline profiling.

    Usage:
        timer = PipelineTimer()
        timer.start("File Load")
        ...
        timer.stop("File Load")
        timer.start("Normalization")
        ...
        timer.stop("Normalization")
        summary = timer.summary()
    """

    def __init__(self):
        self._starts = {}
        self._steps = []  # list of (name, duration_sec)

    def start(self, step_name: str):
        """Begin timing a named step."""
        self._starts[step_name] = time.perf_counter()

    def stop(self, step_name: str) -> float:
        """
        End timing a named step. Returns duration in seconds.
        Raises KeyError if step was never started.
        """
        end = time.perf_counter()
        start = self._starts.pop(step_name)
        duration = end - start
        self._steps.append((step_name, duration))
        return duration

    def total(self) -> float:
        """Total elapsed time across all completed steps."""
        return sum(d for _, d in self._steps)

    def summary(self) -> dict:
        """
        Returns a dict with:
          steps: list of (name, seconds)
          total: float
          formatted: list of "Step Name: X.Xs" strings
        """
        formatted = []
        for name, dur in self._steps:
            formatted.append(f"{name}: {dur:.1f}s")
        formatted.append(f"TOTAL: {self.total():.1f}s")

        return {
            "steps": list(self._steps),
            "total": self.total(),
            "formatted": formatted,
        }

    def summary_dict(self) -> dict:
        """Returns a flat dict of {step_name: duration_seconds}."""
        d = {}
        for name, dur in self._steps:
            d[name] = round(dur, 2)
        d["TOTAL"] = round(self.total(), 2)
        return d
