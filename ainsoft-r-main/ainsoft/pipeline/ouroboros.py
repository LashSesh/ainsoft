"""Ouroboros trading swarm blueprint for AinSOFT.

This module captures the finance-oriented expansion described in the
"AinSOFT Ouroboros Expansion" blueprint.  The implementation keeps the
interfaces lightweight while remaining composable with the existing
pipeline system.  All core classes are pure Python and rely only on the
standard library so they can run in restricted environments or during
unit tests without external APIs.
"""

from __future__ import annotations

import itertools
import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, MutableMapping, Optional


# ---------------------------------------------------------------------------
# GabrielCell & Swarm infrastructure
# ---------------------------------------------------------------------------


@dataclass
class GabrielCell:
    """Trading-focused GabrielCell implementation.

    Each cell receives a role (``Navigator``, ``Locker`` …) and an arbitrary
    ``params`` dictionary.  The :meth:`act` method evaluates market state via a
    simple 5D resonance proxy and optionally dispatches the output to a
    provided feedback sink.  The concrete trading logic can be swapped by
    injecting a different ``scoring_func``.
    """

    cell_id: str
    role: str
    params: MutableMapping[str, float]
    scoring_func: Callable[[MutableMapping[str, float], MutableMapping[str, float]], float]
    feedback_sink: Optional[Callable[[Dict[str, float]], None]] = None
    history: List[Dict[str, float]] = field(default_factory=list)

    def evaluate_opportunity(self, market_state: MutableMapping[str, float]) -> Dict[str, float]:
        """Return a resonance snapshot for the current ``market_state``.

        The default scoring function operates on 5 canonical axes inspired by
        the blueprint (``psi``, ``rho``, ``omega``, ``alpha``, ``beta``).  The
        scoring function is fully pluggable to keep the class neutral with
        respect to concrete trading strategies.
        """

        score = self.scoring_func(self.params, market_state)
        response = {
            "cell_id": self.cell_id,
            "role": self.role,
            "score": float(score),
            "timestamp": time.time(),
        }
        self.history.append(response)
        return response

    def send_feedback(self, payload: Dict[str, float]) -> None:
        if self.feedback_sink:
            self.feedback_sink(payload)

    def act(self, market_state: MutableMapping[str, float]) -> Dict[str, float]:
        snapshot = self.evaluate_opportunity(market_state)
        self.send_feedback(snapshot)
        return snapshot


class GabrielCellSwarm:
    """A collection of :class:`GabrielCell` instances with shared state."""

    def __init__(self, cells: Iterable[GabrielCell], decay: float = 0.95) -> None:
        self.cells = list(cells)
        self.decay = float(decay)
        self._feedback_buffer: List[Dict[str, float]] = []

    def __iter__(self):
        return iter(self.cells)

    def broadcast_market(self, market_state: MutableMapping[str, float]) -> List[Dict[str, float]]:
        return [cell.act(market_state) for cell in self.cells]

    def attach_feedback_sink(self) -> Callable[[Dict[str, float]], None]:
        def sink(entry: Dict[str, float]) -> None:
            self._feedback_buffer.append(entry)

        return sink

    def collect_feedback(self) -> List[Dict[str, float]]:
        samples = list(self._feedback_buffer)
        self._feedback_buffer.clear()
        return samples

    def update_strategy(self, directive: Dict[str, float]) -> None:
        multiplier = directive.get("multiplier", 1.0)
        for cell in self.cells:
            for key, value in list(cell.params.items()):
                cell.params[key] = float(value) * multiplier * self.decay + random.random() * 0.01


# ---------------------------------------------------------------------------
# Kyberios Controller & Field Tensor Router
# ---------------------------------------------------------------------------


class KyberiosController:
    """Supervisor that aggregates swarm feedback and applies policies."""

    def __init__(self, swarm: GabrielCellSwarm, policy: "Policy") -> None:
        self.swarm = swarm
        self.policy = policy

    def run_cycle(self, global_state: MutableMapping[str, float]) -> Dict[str, float]:
        feedback_sink = self.swarm.attach_feedback_sink()
        for cell in self.swarm:
            cell.feedback_sink = feedback_sink

        responses = self.swarm.broadcast_market(global_state)
        swarm_feedback = self.swarm.collect_feedback()
        decision = self.policy.evaluate(global_state, swarm_feedback)

        if decision.get("action") == "trade":
            decision["executed"] = True
        else:
            decision["executed"] = False

        self.swarm.update_strategy(decision)
        return {"responses": responses, "decision": decision}


class FieldTensorRouter:
    """Ephemeral message router with resonance weighted routing."""

    def __init__(self, dissolution_rate: float = 0.1) -> None:
        self.dissolution_rate = float(dissolution_rate)
        self._transient_state: List[Dict[str, float]] = []

    def route(self, message: Dict[str, float], state: MutableMapping[str, float], target_criteria: Callable[[Dict[str, float]], bool]) -> bool:
        weight = self._resonance_weight(message, state)
        routed = False
        if weight >= 0.5 and target_criteria(message):
            self._transient_state.append({"message": message, "weight": weight, "timestamp": time.time()})
            routed = True
        self._apply_decay()
        return routed

    def _resonance_weight(self, message: Dict[str, float], state: MutableMapping[str, float]) -> float:
        sigma = float(state.get("volatility", 1.0))
        base = float(message.get("score", 0.0))
        if sigma <= 0:
            sigma = 1.0
        value = min(1.0, max(0.0, base / (1.0 + math.log1p(sigma))))
        return value

    def _apply_decay(self) -> None:
        now = time.time()
        self._transient_state = [entry for entry in self._transient_state if now - entry["timestamp"] < self.dissolution_rate * 10]

    def self_dissolve(self) -> None:
        self._transient_state.clear()


# ---------------------------------------------------------------------------
# Consensus Staircase Protocol (CSP)
# ---------------------------------------------------------------------------


class ShadowChain:
    """Minimal append-only log used by :class:`CSPStateMachine`."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, object]] = []

    def append(self, event: str, payload: Dict[str, object]) -> None:
        self._entries.append({"event": event, "payload": payload, "timestamp": time.time()})

    def entries(self) -> List[Dict[str, object]]:
        return list(self._entries)


class CSPStateMachine:
    """Implements the Consensus Staircase Protocol state transitions."""

    def __init__(self, shadow_chain: ShadowChain, quorum_gate: Callable[[Dict[str, Dict[str, float]]], bool], executors: Dict[str, Callable[[Iterable[Dict[str, float]]], bool]]) -> None:
        self.shadow_chain = shadow_chain
        self.quorum_gate = quorum_gate
        self.executors = executors
        self.state = "IDLE"
        self.cycle_id: Optional[str] = None
        self.intents: Dict[str, Dict[str, float]] = {}

    def open_intents(self, cycle_id: str, legs_meta: Iterable[str]) -> None:
        self.cycle_id = cycle_id
        self.state = "INTENT_OPEN"
        self.intents.clear()
        self.shadow_chain.append("intent_open", {"cycle": cycle_id, "legs": list(legs_meta)})

    def add_intent(self, leg_id: str, intent: Dict[str, float]) -> None:
        if self.state != "INTENT_OPEN":
            raise RuntimeError("Cannot add intent outside of INTENT_OPEN state")
        self.intents[leg_id] = intent
        self.shadow_chain.append("intent", {"cycle": self.cycle_id, "leg": leg_id, "intent": intent})

    def try_quorum(self, edge: float, tau_edge: float) -> bool:
        if self.state != "INTENT_OPEN":
            return False
        if self.quorum_gate(self.intents) and edge >= tau_edge:
            self.state = "INTENT_QUORUM"
            self.shadow_chain.append("intent_quorum", {"cycle": self.cycle_id, "edge": edge})
            return True
        return False

    def execute(self, legs_or_route: Iterable[Dict[str, float]], venue: str = "CEX") -> bool:
        if self.state != "INTENT_QUORUM":
            return False
        self.state = "EXEC_LOCKSTEP"
        executor = self.executors.get(venue.lower())
        if not executor:
            raise KeyError(f"No executor configured for venue '{venue}'")
        ok = bool(executor(legs_or_route))
        self.shadow_chain.append("exec_done", {"cycle": self.cycle_id, "ok": ok})
        self.state = "CONFIRM" if ok else "ABORT"
        return ok


# ---------------------------------------------------------------------------
# Policies & helper utilities
# ---------------------------------------------------------------------------


class Policy:
    """Simple pluggable policy interface used by :class:`KyberiosController`."""

    def evaluate(self, global_state: MutableMapping[str, float], feedback: Iterable[Dict[str, float]]) -> Dict[str, float]:
        raise NotImplementedError


class ThresholdPolicy(Policy):
    """Threshold-based policy leveraging aggregated feedback."""

    def __init__(self, threshold: float = 0.6) -> None:
        self.threshold = float(threshold)

    def evaluate(self, global_state: MutableMapping[str, float], feedback: Iterable[Dict[str, float]]) -> Dict[str, float]:
        scores = [entry.get("score", 0.0) for entry in feedback]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        action = "trade" if avg_score > self.threshold else "observe"
        return {
            "action": action,
            "avg_score": avg_score,
            "multiplier": 1.0 + max(0.0, avg_score - self.threshold),
            "volatility": global_state.get("volatility", 1.0),
        }


def default_scoring(params: MutableMapping[str, float], market_state: MutableMapping[str, float]) -> float:
    """Reference scoring function used in the default blueprint.

    The function reads five canonical axes from ``params`` and combines them
    with market information (volatility/liquidity) to emulate the blueprint's
    5D resonance scoring.
    """

    axes = [params.get(axis, 0.2) for axis in ("psi", "rho", "omega", "alpha", "beta")]
    weights = [1.0, 0.8, 0.9, 1.1, 0.7]
    score = sum(axis * weight for axis, weight in zip(axes, weights)) / len(weights)
    liquidity = float(market_state.get("liquidity", 1.0))
    volatility = float(market_state.get("volatility", 1.0))
    score *= 1.0 + 0.1 * liquidity
    score /= 1.0 + 0.05 * volatility
    return max(0.0, min(score, 1.0))


def build_default_swarm(num_cells: int = 3) -> GabrielCellSwarm:
    """Construct a :class:`GabrielCellSwarm` with sensible defaults."""

    roles = itertools.cycle(["Navigator", "Locker", "Stepper", "Watcher"])
    cells: List[GabrielCell] = []
    for idx in range(num_cells):
        params = {
            "psi": random.uniform(0.2, 0.8),
            "rho": random.uniform(0.2, 0.8),
            "omega": random.uniform(0.2, 0.8),
            "alpha": random.uniform(0.2, 0.8),
            "beta": random.uniform(0.2, 0.8),
        }
        cells.append(GabrielCell(f"cell-{idx}", next(roles), params, default_scoring))
    return GabrielCellSwarm(cells)


__all__ = [
    "GabrielCell",
    "GabrielCellSwarm",
    "KyberiosController",
    "FieldTensorRouter",
    "ShadowChain",
    "CSPStateMachine",
    "Policy",
    "ThresholdPolicy",
    "default_scoring",
    "build_default_swarm",
]

