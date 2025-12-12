"""Tests for the Ouroboros trading swarm blueprint."""

from __future__ import annotations

from typing import Dict, Iterable

import pytest

from ainsoft.pipeline.ouroboros import (
    CSPStateMachine,
    FieldTensorRouter,
    GabrielCell,
    GabrielCellSwarm,
    KyberiosController,
    Policy,
    ShadowChain,
    ThresholdPolicy,
    build_default_swarm,
    default_scoring,
)


class DummyPolicy(Policy):
    def evaluate(self, global_state: Dict[str, float], feedback: Iterable[Dict[str, float]]) -> Dict[str, float]:
        return {"action": "trade", "multiplier": 1.0, "volatility": global_state.get("volatility", 1.0)}


def test_gabriel_cell_swarm_cycle() -> None:
    swarm = build_default_swarm(2)
    controller = KyberiosController(swarm, ThresholdPolicy(threshold=0.0))
    result = controller.run_cycle({"volatility": 0.5, "liquidity": 1.0})
    assert result["decision"]["executed"] is True
    assert len(result["responses"]) == 2


def test_field_tensor_router_routing_and_decay() -> None:
    router = FieldTensorRouter(dissolution_rate=0.01)
    routed = router.route({"score": 0.8}, {"volatility": 0.2}, lambda msg: msg["score"] > 0.5)
    assert routed is True
    router.self_dissolve()
    # Ensure the transient state clears without errors
    routed = router.route({"score": 0.4}, {"volatility": 0.2}, lambda msg: True)
    assert routed is False


def test_csp_state_machine_executes_on_quorum() -> None:
    shadow_chain = ShadowChain()

    def quorum(intents: Dict[str, Dict[str, float]]) -> bool:
        return len(intents) >= 2

    calls = {"cex": 0}

    def exec_cex(legs: Iterable[Dict[str, float]]) -> bool:
        calls["cex"] += len(list(legs))
        return True

    machine = CSPStateMachine(shadow_chain, quorum, {"cex": exec_cex})
    machine.open_intents("cycle-1", ["leg-a", "leg-b"])
    machine.add_intent("leg-a", {"score": 0.7})
    machine.add_intent("leg-b", {"score": 0.8})
    assert machine.try_quorum(edge=0.9, tau_edge=0.5)
    assert machine.execute([{"route": 1}], venue="CEX")
    assert machine.state == "CONFIRM"
    assert calls["cex"] == 1
    assert shadow_chain.entries()


def test_custom_gabriel_cell_scoring() -> None:
    def scoring(params: Dict[str, float], market_state: Dict[str, float]) -> float:
        assert params["psi"] == pytest.approx(0.5)
        return default_scoring(params, market_state)

    cell = GabrielCell("c1", "Navigator", {"psi": 0.5, "rho": 0.4, "omega": 0.3, "alpha": 0.2, "beta": 0.1}, scoring)
    swarm = GabrielCellSwarm([cell])
    controller = KyberiosController(swarm, DummyPolicy())
    controller.run_cycle({"volatility": 0.1, "liquidity": 0.2})
    assert cell.history
