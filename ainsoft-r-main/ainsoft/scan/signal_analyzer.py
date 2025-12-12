"""Analyse response signals to derive resonance scores."""

from __future__ import annotations

from statistics import fmean
from typing import Dict, List


def analyze_signals(responses: List[Dict]) -> float:
    """Normalise the mean latency of responses into the range ``[0, 1]``."""

    if not responses:
        return 0.0

    latencies = [r["latency"] for r in responses if "latency" in r]
    if not latencies:
        return 0.0

    score = float(fmean(latencies))
    return min(max(score, 0.0), 1.0)

