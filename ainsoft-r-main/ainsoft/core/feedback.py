"""Feedback module for self modulation."""

from __future__ import annotations

from typing import Dict


class Feedback:
    """Evaluate the impact of impulses."""

    def __init__(self) -> None:
        self.last_feedback = 0.5

    def evaluate(self, result: Dict) -> float:
        """Extract an impact score from *result*."""

        impact = float(result.get("impact", 0.5))
        impact = min(max(impact, 0.0), 1.0)
        self.last_feedback = impact
        return impact

