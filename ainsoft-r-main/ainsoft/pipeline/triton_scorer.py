"""Spectral scoring utilities for the Fixpunktattraktor pipeline."""

from __future__ import annotations

from typing import Any

from .fixpunktattraktor import FixpunktCandidate


def triton_scorer(payload: Any) -> float:
    """Compute a deterministic pseudo spectral score for *payload*.

    The scoring function accepts either raw payloads or
    :class:`~ainsoft.pipeline.fixpunktattraktor.FixpunktCandidate` instances.  The
    implementation is a placeholder for complex signal processing (Fourier,
    statistical, machine learning, ...).  It maps the payload to a value in the
    ``[0.0, 1.0]`` interval using a stable hash.
    """

    if isinstance(payload, FixpunktCandidate):
        payload = payload.value
    return float(hash(repr(payload)) % 100) / 100.0


__all__ = ["triton_scorer"]
