"""Tests for resonance computation utilities."""

from __future__ import annotations

from ainsoft.core.oscillator import Oscillator
from ainsoft.scan.signal_analyzer import analyze_signals


def test_analyze_resonance():
    responses = [{"latency": 0.1}, {"latency": 0.2}]
    score = analyze_signals(responses)

    osc = Oscillator()
    resonance = osc.compute([score])

    assert 0.0 <= resonance <= 1.0

