"""Lifecycle orchestration for AinSOFT."""

from __future__ import annotations

from typing import Optional

from ainsoft.core.feedback import Feedback
from ainsoft.core.impulse import Impulse
from ainsoft.core.network import ProxyConfig
from ainsoft.core.oscillator import Oscillator
from ainsoft.core.threshold import Threshold
from ainsoft.orchestrator.scheduler import wait_randomized
from ainsoft.scan.probe_emitter import emit_probe_pattern
from ainsoft.scan.response_observer import collect_responses
from ainsoft.scan.signal_analyzer import analyze_signals


def run_lifecycle_cycle(
    target: str,
    port: int = 8080,
    *,
    proxy_config: Optional[ProxyConfig] = None,
) -> None:
    """Execute a single resonance cycle against *target*/*port* with proxy-aware I/O."""

    probe_result = emit_probe_pattern(target, port, proxy_config=proxy_config)
    responses = collect_responses(port, proxy_config=proxy_config)
    resonance_score = analyze_signals(responses)

    oscillator = Oscillator()
    osc_score = oscillator.compute([resonance_score])

    threshold = Threshold()
    if threshold.check(osc_score):
        impulse = Impulse()
        vector = impulse.construct({"probe": probe_result, "score": osc_score})
        fired = impulse.fire(vector, target, port, proxy_config=proxy_config)

        feedback = Feedback()
        feedback_score = feedback.evaluate({"impact": 1.0 if fired else 0.2})
        threshold.adapt(feedback_score)

    wait_randomized()

