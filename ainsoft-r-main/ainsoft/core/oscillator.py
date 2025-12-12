"""Tripolar resonance logic.

The oscillator aggregates numeric signals and normalises the result
into a bounded resonance score.
"""

from __future__ import annotations

from statistics import fmean
from typing import Iterable, List


class Oscillator:
    """Compute resonance values from numeric signals."""

    def __init__(self) -> None:
        self.last_state = 0.0

    def compute(self, signals: Iterable[float]) -> float:
        """Return a resonance score between 0.0 and 1.0."""

        values: List[float] = list(signals)
        if not values:
            self.last_state = 0.0
            return 0.0

        mean = float(fmean(values))
        score = min(max(mean, 0.0), 1.0)
        self.last_state = score
        return score

