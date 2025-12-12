"""Timing utilities for orchestrating resonance cycles."""

from __future__ import annotations

import random
import time


def wait_randomized(base: float = 0.5, jitter: float = 0.3) -> None:
    """Sleep for a pseudo-randomised duration around *base*."""

    delay = base + random.uniform(-jitter, jitter)
    time.sleep(max(0.01, delay))

