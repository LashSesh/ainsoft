"""Tests for the Fixpunktattraktor pipeline components."""

from __future__ import annotations

from typing import Any, Dict, List

from ainsoft.pipeline.aion_pipeline import build_fixpunkt_engine_from_config, PipelineOrchestrator
from ainsoft.pipeline.fixpunktattraktor import FixpunktCandidate, FixpunktAttraktorEngine, FixpunktState, mandorla_consensus
from ainsoft.pipeline.network_dispatcher import network_dispatcher
from ainsoft.pipeline.scorpiosync_generators import http_builder_transformer
from ainsoft.pipeline.blueprints import (
    GabrielCell,
    KyberiotesField,
    DTTModulator,
    DTTGabrielCell,
    TripolarResonanceModule,
    EmotionRegulationModule,
    vesica_overlap,
    dtt_feedback,
)


def test_pipeline_orchestrator_runs_chain(monkeypatch):
    captured: Dict[str, Any] = {}

    def generator() -> Dict[str, Any]:
        return {"method": "GET", "url": "http://example.test", "headers": {}, "body": ""}

    def dispatcher(payload: Any, proxy_cfg=None) -> Dict[str, Any]:
        captured["payload"] = payload
        captured["proxy"] = proxy_cfg
        return {"status": "captured", "payload": payload}

    orchestrator = PipelineOrchestrator(
        generators=[generator],
        transformers=[http_builder_transformer],
        dispatchers=[dispatcher],
    )

    result = orchestrator.run(proxy_cfg={"enabled": False})
    assert result[0]["stages"][-1].startswith("GET http://example.test")
    assert captured["payload"].startswith("GET http://example.test")
    assert captured["proxy"] == {"enabled": False}


def test_fixpunkt_engine_selects_best_candidate():
    def generator_high() -> Dict[str, Any]:
        return {"id": "high", "impact": 0.9}

    def generator_low() -> Dict[str, Any]:
        return {"id": "low", "impact": 0.4}

    def score(candidate: Any) -> float:
        if isinstance(candidate, FixpunktCandidate):
            candidate = candidate.value
        return candidate["impact"]

    def impulse(candidate: Any) -> float:
        if isinstance(candidate, FixpunktCandidate):
            candidate = candidate.value
        return round(candidate["impact"], 1)

    def threshold_eval(candidate: Any, threshold: float) -> bool:
        if isinstance(candidate, FixpunktCandidate):
            candidate = candidate.value
        return candidate["impact"] >= threshold

    config = {
        "pipeline": {
            "generators": [generator_high, generator_low],
            "transformers": [],
            "dispatchers": [],
        },
        "fixpunkt": {
            "scorer": score,
            "impulses": [impulse, impulse],
            "threshold_evaluator": threshold_eval,
            "threshold_range": [0.5, 0.8],
        },
    }

    engine = build_fixpunkt_engine_from_config(config)
    result = engine.run()
    assert result is not None
    assert result.value["id"] == "high"


def test_network_dispatcher_uses_proxy(monkeypatch):
    calls: List[Any] = []

    class DummySocket:
        def __init__(self, *_args, **_kwargs):
            self.closed = False

        def settimeout(self, _timeout: float) -> None:
            pass

        def connect(self, _target):
            calls.append("connect")

        def sendall(self, _data: bytes) -> None:
            calls.append("send")

        def close(self) -> None:
            self.closed = True

    def fake_create_socket(proxy_cfg, **_kwargs):
        calls.append(proxy_cfg)
        return DummySocket()

    monkeypatch.setattr("ainsoft.pipeline.network_dispatcher.create_socket_with_optional_proxy", fake_create_socket)

    response = network_dispatcher("PING", proxy_cfg={"enabled": True, "host": "127.0.0.1", "port": 1080})
    assert calls[0] == {"enabled": True, "host": "127.0.0.1", "port": 1080}
    assert "status" in response


def test_gabriel_cells_sync_and_feedback():
    cell_a = GabrielCell(0.2)
    cell_b = GabrielCell(0.8, neighbors=[cell_a])
    field = KyberiotesField([cell_a, cell_b])

    before = (cell_a.state, cell_b.state)
    field.synchronize()
    after = (cell_a.state, cell_b.state)
    assert after != before

    modulator = DTTModulator(omega=0.0, amplitude=0.0, offset=1.0, mode="scaled")
    adaptive = DTTGabrielCell(0.1, modulator, neighbors=[cell_b])
    adaptive.step()
    feedback_state = dtt_feedback({"lr": 1.0, "threshold": 0.5}, modulator)
    assert feedback_state["lr"] > 0.0
    assert adaptive.state != 0.1


def test_mandorla_consensus_uses_overlap():
    candidate = FixpunktCandidate({"vector": [1.0, 0.0, 0.0]}, {"vector": [1.0, 0.0, 0.0]})
    state = FixpunktState([candidate], selected=candidate)
    result = mandorla_consensus(state, state, threshold=0.5)
    assert result is not None
    assert result.metadata.get("mandorla_overlap") is True
    assert vesica_overlap([1, 0, 0], [1, 0, 0])


def test_fixpunkt_engine_with_dtt_and_emotion():
    def generator():
        return [
            {"id": "alpha", "impact": 0.9, "vector": [0.8, 0.1, 0.1]},
            {"id": "beta", "impact": 0.4, "vector": [0.1, 0.1, 0.8]},
        ]

    def score(candidate: Any) -> float:
        if isinstance(candidate, FixpunktCandidate):
            candidate = candidate.value
        return candidate["impact"]

    def impulse(candidate: Any) -> Any:
        if isinstance(candidate, FixpunktCandidate):
            candidate = candidate.value
        return candidate["id"]

    def evaluator(candidate: Any, threshold: float) -> bool:
        if isinstance(candidate, FixpunktCandidate):
            candidate = candidate.value
        return candidate["impact"] >= threshold

    modulators = {
        "wt": DTTModulator(omega=0.0, amplitude=0.0, offset=1.0, mode="raw"),
        "sw": DTTModulator(omega=0.0, amplitude=0.0, offset=1.0, mode="raw"),
    }
    resonance_module = TripolarResonanceModule([0.1, 0.2, 0.3])
    emotion_module = EmotionRegulationModule()

    engine = FixpunktAttraktorEngine(
        candidate_generator=generator,
        scorer=score,
        impulse_funcs=[impulse, impulse],
        threshold_evaluator=evaluator,
        threshold_range=[0.5, 0.7],
        dtt_modulators=modulators,
        resonance_module=resonance_module,
        emotion_module=emotion_module,
        consensus_fn=mandorla_consensus,
    )

    result = engine.run()
    assert result is not None
    assert result.value["id"] == "alpha"
    assert "resonance" in result.metadata
    assert "emotion_state" in result.metadata
    assert emotion_module.state() != (0.0, 0.0)
