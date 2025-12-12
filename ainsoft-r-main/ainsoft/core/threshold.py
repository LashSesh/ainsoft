"""Adaptive threshold logic for resonance triggering."""

from __future__ import annotations


class Threshold:
    """Dynamically adapt the activation threshold."""

    def __init__(self, base: float = 0.7) -> None:
        self.value = base

    def check(self, score: float) -> bool:
        """Return ``True`` if *score* exceeds the threshold."""

        return score > self.value

    def adapt(self, feedback: float) -> None:
        """Adjust the threshold based on feedback."""

        delta = (feedback - 0.5) * 0.1
        self.value = min(max(self.value + delta, 0.3), 0.99)

