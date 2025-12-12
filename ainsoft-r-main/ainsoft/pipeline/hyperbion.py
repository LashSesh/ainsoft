"""Hyperbion and 5D sensorium blueprints for AinSOFT."""

from __future__ import annotations

import json
import math
import pickle
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence


def _rand_vector(dim: int) -> List[float]:
    return [random.random() for _ in range(dim)]


def _add(vec_a: Sequence[float], vec_b: Sequence[float]) -> List[float]:
    return [float(a) + float(b) for a, b in zip(vec_a, vec_b)]


def _sub(vec_a: Sequence[float], vec_b: Sequence[float]) -> List[float]:
    return [float(a) - float(b) for a, b in zip(vec_a, vec_b)]


def _scale(vec: Sequence[float], factor: float) -> List[float]:
    return [float(v) * factor for v in vec]


def _mean(vectors: Iterable[Sequence[float]]) -> List[float]:
    vectors = [list(v) for v in vectors]
    if not vectors:
        return []
    dim = len(vectors[0])
    sums = [0.0] * dim
    for vec in vectors:
        for idx, value in enumerate(vec):
            sums[idx] += float(value)
    count = float(len(vectors))
    return [value / count for value in sums]


def _norm(vec: Sequence[float]) -> float:
    return math.sqrt(sum(float(v) ** 2 for v in vec))


def _to_vector(value: Any, dim: int) -> List[float]:
    if isinstance(value, (list, tuple)):
        return [float(v) for v in value]
    return [float(value)] * dim


class HyperbionModule:
    """Bio-resonant subsystem capable of growth, mutation, and fusion."""

    def __init__(
        self,
        state_dim: int = 5,
        phase: float = 0.0,
        memory: Optional[List[List[float]]] = None,
        name: str = "Module",
    ) -> None:
        self.name = name
        self.state = _rand_vector(state_dim)
        self.phase = float(phase)
        self.memory: List[List[float]] = list(memory or [])
        self.children: List[HyperbionModule] = []
        self.active = True

    def grow(self) -> "HyperbionModule":
        """Spawn a new child module linked to this one."""

        child = HyperbionModule(
            len(self.state),
            phase=self.phase + random.random(),
            name=f"{self.name}_child{len(self.children)}",
        )
        self.children.append(child)
        return child

    def mutate(self, rate: float = 0.05) -> None:
        """Introduce stochastic variation and persist the snapshot."""

        noise = [(random.random() - 0.5) * rate for _ in self.state]
        self.state = [value + delta for value, delta in zip(self.state, noise)]
        self.memory.append(list(self.state))

    def fuse(self, other: "HyperbionModule") -> "HyperbionModule":
        """Fuse with another module by averaging states and phases."""

        fused_state = [
            (a + b) / 2.0 for a, b in zip(self.state, other.state)
        ]
        fused_phase = (self.phase + other.phase) / 2.0
        fused = HyperbionModule(
            len(self.state),
            phase=fused_phase,
            memory=self.memory + other.memory,
            name=f"{self.name}_fused_{other.name}",
        )
        fused.state = fused_state
        return fused

    def split(self) -> tuple["HyperbionModule", "HyperbionModule"]:
        """Split the module into two variants with small divergence."""

        if not self.state:
            raise ValueError("Cannot split module without state dimensions")
        idx = random.randrange(len(self.state))
        state1 = list(self.state)
        state2 = list(self.state)
        state1[idx] += 0.1
        state2[idx] -= 0.1
        child1 = HyperbionModule(len(self.state), phase=self.phase, name=f"{self.name}_split1")
        child2 = HyperbionModule(len(self.state), phase=self.phase, name=f"{self.name}_split2")
        child1.state = state1
        child2.state = state2
        return child1, child2

    def deactivate(self) -> None:
        """Disable the module."""

        self.active = False


class SensoriumCell:
    """5D sensorium node that exchanges resonance with its neighbours."""

    def __init__(self, state_dim: int = 5) -> None:
        self.state = _rand_vector(state_dim)
        self.neighbors: List[SensoriumCell] = []
        self.resonance: float = 0.0
        self.memory: List[List[float]] = []

    def add_neighbor(self, cell: "SensoriumCell") -> None:
        if cell not in self.neighbors:
            self.neighbors.append(cell)

    def measure_resonance(self) -> float:
        if not self.neighbors:
            self.resonance = 0.0
            return 0.0
        diffs = [_norm(_sub(self.state, n.state)) for n in self.neighbors]
        resonance = 1.0 / (1.0 + sum(diffs) / len(diffs))
        self.resonance = resonance
        return resonance

    def update_state(self, rate: float = 0.1) -> None:
        if not self.neighbors:
            return
        mean_neighbor = _mean(n.state for n in self.neighbors)
        delta = _scale(_sub(mean_neighbor, self.state), rate)
        self.state = _add(self.state, delta)
        self.memory.append(list(self.state))


class FSMCore:
    """Field-state machine that only fires upon proof-of-resonance."""

    def __init__(self, threshold: float = 0.8) -> None:
        self.threshold = float(threshold)
        self.audit_log: List[Dict[str, Any]] = []

    def proof_of_resonance(self, cell: SensoriumCell) -> bool:
        resonance = cell.measure_resonance()
        event = {"t": time.time(), "cell": id(cell), "resonance": resonance}
        self.audit_log.append(event)
        return resonance > self.threshold

    def double_kick(self, cell1: SensoriumCell, cell2: SensoriumCell) -> None:
        if self.proof_of_resonance(cell1) and self.proof_of_resonance(cell2):
            kick = _scale(_sub(cell1.state, cell2.state), 0.2)
            cell1.state = _sub(cell1.state, kick)
            cell2.state = _add(cell2.state, kick)
            self.audit_log.append({"t": time.time(), "event": "double_kick", "kick": kick})

    def gate(self, cell: SensoriumCell) -> None:
        if self.proof_of_resonance(cell):
            self.audit_log.append({"t": time.time(), "event": "gate", "cell": id(cell)})

    def get_audit(self) -> List[Dict[str, Any]]:
        return list(self.audit_log)


class MandorlaField:
    """Overlap field integrating perception and intention vectors."""

    def __init__(self, dim: int = 5) -> None:
        self.perception = _rand_vector(dim)
        self.intention = _rand_vector(dim)
        self.memory: List[List[float]] = []

    def update(self, new_perception: Sequence[float], new_intention: Sequence[float], rate: float = 0.1) -> List[float]:
        perc = _to_vector(new_perception, len(self.perception))
        inten = _to_vector(new_intention, len(self.intention))
        self.perception = _add(self.perception, _scale(_sub(perc, self.perception), rate))
        self.intention = _add(self.intention, _scale(_sub(inten, self.intention), rate))
        mandorla = _scale(_add(self.perception, self.intention), 0.5)
        self.memory.append(list(mandorla))
        return mandorla


class Oriphiel5DMemory:
    """Spiral memory structure that drifts through the ND space."""

    def __init__(self, dim: int = 5) -> None:
        self.states: List[List[float]] = []
        self.theta: float = 0.0
        self.dim = dim

    def add_state(self, state: Sequence[float]) -> List[float]:
        self.theta += math.pi / 7.0
        spiral = [math.cos(self.theta + i) for i in range(self.dim)]
        new_state = _add(_to_vector(state, self.dim), _scale(spiral, 0.1))
        self.states.append(new_state)
        return new_state

    def last(self) -> Optional[List[float]]:
        return self.states[-1] if self.states else None


class SeraphicFeedbackModule:
    """Transforms arbitrary stimuli into resonance pulses for the system."""

    def __init__(self, embed_func: Optional[Callable[[Any], List[float]]] = None) -> None:
        self.embed_func = embed_func if embed_func is not None else self.default_embed
        self.feedback_log: List[Dict[str, Any]] = []

    def default_embed(self, value: Any) -> List[float]:
        if isinstance(value, (list, tuple)):
            norm = _norm(value)
            if norm == 0.0:
                return [0.0 for _ in value]
            return [float(v) / norm for v in value]
        try:
            number = float(value)
        except Exception:
            number = float(len(str(value)) % 7) / 7.0
        return [number] * 5

    def process_feedback(self, value: Any) -> List[float]:
        pulse = self.embed_func(value)
        self.feedback_log.append({"t": time.time(), "feedback": value, "pulse": list(pulse)})
        return pulse


class AuditTrail:
    """Append-only audit trail stored as JSON lines."""

    def __init__(self, filename: str = "audit_log.jsonl") -> None:
        self.filename = filename

    def log(self, record: Dict[str, Any]) -> None:
        with open(self.filename, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


@dataclass
class ModuleRegistry:
    """Simple plug-in registry for Hyperbion subsystems."""

    modules: Dict[str, Any] = field(default_factory=dict)

    def register(self, name: str, module: Any) -> None:
        self.modules[name] = module

    def get(self, name: str) -> Any:
        return self.modules.get(name)


def export_state(filename: str, *objects: Any) -> None:
    """Persist arbitrary objects to disk using pickle."""

    with open(filename, "wb") as handle:
        pickle.dump(objects, handle)


def import_state(filename: str) -> Any:
    """Load previously persisted objects."""

    with open(filename, "rb") as handle:
        return pickle.load(handle)


__all__ = [
    "HyperbionModule",
    "SensoriumCell",
    "FSMCore",
    "MandorlaField",
    "Oriphiel5DMemory",
    "SeraphicFeedbackModule",
    "AuditTrail",
    "ModuleRegistry",
    "export_state",
    "import_state",
]
