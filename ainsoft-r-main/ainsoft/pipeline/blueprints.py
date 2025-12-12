"""Advanced blueprint modules for AinSOFT's adaptive pipelines."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence


class GabrielCell:
    """Self-organising cell that exchanges state with neighbours."""

    def __init__(self, state: float, neighbors: Optional[Iterable["GabrielCell"]] = None, learning_rate: float = 0.1):
        self.state = float(state)
        self.learning_rate = float(learning_rate)
        self.neighbors: List[GabrielCell] = list(neighbors or [])

    def perceive(self) -> float:
        if not self.neighbors:
            return self.state
        return float(sum(n.state for n in self.neighbors) / len(self.neighbors))

    def adapt(self) -> None:
        input_state = self.perceive()
        self.state += self.learning_rate * (input_state - self.state)

    def step(self) -> None:
        self.adapt()


class TripolarResonanceModule:
    """Tripolar resonance core based on vector norms."""

    def __init__(self, phases: Sequence[float]):
        self.phases = [float(phase) for phase in phases]

    def resonance(self) -> float:
        return math.sqrt(sum(phase * phase for phase in self.phases))

    def interfere(self, other_phases: Sequence[float]) -> float:
        other = [float(phase) for phase in other_phases]
        denom = self.resonance()
        if denom == 0.0:
            return 0.0
        numerator = sum(a * b for a, b in zip(self.phases, other))
        return numerator / denom

    def decide(self, threshold: float = 1.0) -> bool:
        return self.resonance() > threshold


class EmotionRegulationModule:
    """Adaptive valence/arousal pair used for feedback modulation."""

    def __init__(self, valence: float = 0.0, arousal: float = 0.0):
        self.valence = float(valence)
        self.arousal = float(arousal)

    def modulate(self, stimulus: float) -> None:
        self.valence += 0.1 * stimulus
        self.arousal = max(0.0, min(self.arousal + 0.05 * abs(stimulus), 1.0))

    def state(self) -> tuple[float, float]:
        return (self.valence, self.arousal)


class KyberiosCore:
    """Aggregates cognition, emotion, reflection, and decision cues."""

    def __init__(self, cognition: float, emotion: float, reflection: float, decision: float):
        self.cognition = float(cognition)
        self.emotion = float(emotion)
        self.reflection = float(reflection)
        self.decision = float(decision)

    def integrate(self) -> float:
        return (self.cognition + self.emotion + self.reflection + self.decision) / 4.0

    def act(self, threshold: float = 0.5) -> bool:
        return self.integrate() > threshold


class KyberiotesField:
    """Coordinates a swarm of :class:`GabrielCell` instances."""

    def __init__(self, agents: Iterable[GabrielCell]):
        self.agents: List[GabrielCell] = list(agents)

    def synchronize(self) -> None:
        if not self.agents:
            return
        mean_state = sum(agent.state for agent in self.agents) / len(self.agents)
        for agent in self.agents:
            agent.state += 0.05 * (mean_state - agent.state)


class TopologicalFieldAdapter:
    """Converts a continuous field state into a discrete actuator signal."""

    def adapt(self, field_state: float) -> int:
        return int(float(field_state) * 100)


class HDAGNode:
    """Hyperdimensional DAG node for semantic context."""

    def __init__(self, vector: Sequence[float], edges: Optional[Iterable["HDAGNode"]] = None):
        self.vector = list(vector)
        self.edges: List[HDAGNode] = list(edges or [])

    def connect(self, node: "HDAGNode") -> None:
        self.edges.append(node)

    def traverse(self, fn: Callable[["HDAGNode"], None]) -> None:
        fn(self)
        for edge in self.edges:
            edge.traverse(fn)


def vesica_overlap(vec_a: Sequence[float], vec_b: Sequence[float], threshold: float = 0.8) -> bool:
    a = [float(v) for v in vec_a]
    b = [float(v) for v in vec_b]
    norm_a = math.sqrt(sum(v * v for v in a))
    norm_b = math.sqrt(sum(v * v for v in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return False
    overlap = sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)
    return overlap >= threshold


class DTTModulator:
    """Dynamic Tripolarity Theory modulator for thresholds and scores."""

    def __init__(self, omega: float = 1.0, phase: float = 0.0, amplitude: float = 1.0, offset: float = 0.0, mode: str = "scaled"):
        self.omega = float(omega)
        self.phase = float(phase)
        self.amplitude = float(amplitude)
        self.offset = float(offset)
        self.mode = mode

    def value(self, t: Optional[float] = None) -> float:
        if t is None:
            t = time.time()
        v = self.amplitude * math.sin(self.omega * t + self.phase) + self.offset
        return 0.5 * (v + 1.0) if self.mode == "scaled" else v


class DTTWurmlochTrichter:
    """Score modulating wrapper for the Wurmloch-Trichter."""

    def __init__(self, base_score_func: Callable[[Any], float], dtt_modulator: DTTModulator):
        self.base_score_func = base_score_func
        self.dtt_modulator = dtt_modulator

    def apply(self, candidates: Sequence[Any]) -> Optional[Any]:
        if not candidates:
            return None
        t = time.time()
        weight = max(self.dtt_modulator.value(t), 0.0)
        return max(candidates, key=lambda c: float(self.base_score_func(c)) * weight)


class DTTThresholdOperator:
    """Applies an operator function using a modulated threshold."""

    def __init__(self, operator_func: Callable[[Any, float], Any], base_threshold: float, dtt_modulator: DTTModulator):
        self.operator_func = operator_func
        self.base_threshold = float(base_threshold)
        self.dtt_modulator = dtt_modulator

    def apply(self, data: Any) -> Any:
        t = time.time()
        threshold = self.base_threshold * max(self.dtt_modulator.value(t), 0.0)
        return self.operator_func(data, threshold)


def dk_decision(values: Sequence[float], threshold: float) -> bool:
    if len(values) < 2:
        return False
    return abs(values[0] - values[1]) < threshold


class DTT_TRM(TripolarResonanceModule):
    """Tripolar module with DTT scaling."""

    def __init__(self, phases: Sequence[float], dtt_modulator: DTTModulator):
        super().__init__(phases)
        self.dtt_modulator = dtt_modulator

    def resonance(self, t: Optional[float] = None) -> float:  # type: ignore[override]
        base = super().resonance()
        return base * max(self.dtt_modulator.value(t), 0.0)


class DTTGabrielCell(GabrielCell):
    """GabrielCell with dynamic DTT-controlled learning rate."""

    def __init__(self, state: float, dtt_modulator: DTTModulator, neighbors: Optional[Iterable[GabrielCell]] = None):
        super().__init__(state, neighbors=neighbors, learning_rate=0.1)
        self.dtt_modulator = dtt_modulator

    def adapt(self) -> None:  # type: ignore[override]
        input_state = self.perceive()
        lr = 0.1 * max(self.dtt_modulator.value(), 0.0)
        self.state += lr * (input_state - self.state)


def emit_if_phase_ok(data: Any, dispatcher: Callable[[Any], Any], dtt_modulator: DTTModulator, emission_threshold: float = 0.7) -> Optional[Any]:
    if dtt_modulator.value() > emission_threshold:
        return dispatcher(data)
    return None


def dtt_pipeline_step(data: Any, dtt_modulator: DTTModulator, action: Callable[[Any], Any], dtt_thresh: float = 0.6) -> Optional[Any]:
    if dtt_modulator.value() > dtt_thresh:
        return action(data)
    return None


def dtt_feedback(memory: Mapping[str, float], dtt_modulator: DTTModulator) -> Mapping[str, float]:
    updated = dict(memory)
    factor = max(dtt_modulator.value(), 0.1)
    if "lr" in updated:
        updated["lr"] *= factor
    if "threshold" in updated:
        updated["threshold"] = max(0.05, updated["threshold"] * factor)
    return updated


@dataclass
class DTT_HDGNode:
    """HDAG node with DTT-driven modulation."""

    vector: Sequence[float]
    dtt_modulator: DTTModulator
    edges: List["DTT_HDGNode"] = field(default_factory=list)

    def modulate(self) -> List[float]:
        factor = max(self.dtt_modulator.value(), 0.0)
        self.vector = [float(v) * factor for v in self.vector]
        return list(self.vector)

    def connect(self, node: "DTT_HDGNode") -> None:
        self.edges.append(node)

    def traverse(self, fn: Callable[["DTT_HDGNode"], None]) -> None:
        fn(self)
        for edge in self.edges:
            edge.traverse(fn)


__all__ = [
    "GabrielCell",
    "TripolarResonanceModule",
    "EmotionRegulationModule",
    "KyberiosCore",
    "KyberiotesField",
    "TopologicalFieldAdapter",
    "HDAGNode",
    "vesica_overlap",
    "DTTModulator",
    "DTTWurmlochTrichter",
    "DTTThresholdOperator",
    "dk_decision",
    "DTT_TRM",
    "DTTGabrielCell",
    "emit_if_phase_ok",
    "dtt_pipeline_step",
    "dtt_feedback",
    "DTT_HDGNode",
]
