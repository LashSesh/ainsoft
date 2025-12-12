"""Quantenbionische Feldintegration for AinSOFT.

This module captures the "AinSOFT Resonanzkern: Quantenbionische &\nCHAIOT-QDASH Integration" blueprint.  The goal is to provide a
field-centric operator model where every component participates in a
shared resonance field instead of acting as a linear pipeline stage.

The implementation keeps the numerics intentionally light so the
classes remain easy to unit-test while still mirroring the blueprint's
terminology (Gabriel-Zellen, Mandorla, Oriphiel5D, QLOGIC …).  All
operators share a common ``__call__`` signature allowing hot-swapping
and dynamic registration via :class:`OperatorRegistry`.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import time
from typing import Any, Callable, Dict, Iterable, List, MutableMapping, Optional


# ---------------------------------------------------------------------------
# Field primitives
# ---------------------------------------------------------------------------


class FieldState(MutableMapping[str, Any]):
    """Minimal mapping to hold field variables.

    Using a dedicated mapping subclass makes it easy to share mutable
    state between operators and provides a single place for helper
    utilities such as entropy calculation.
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = dict(initial or {})

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._data)

    # Convenience helpers -------------------------------------------------

    def entropy(self) -> float:
        """Return a Shannon-style proxy based on numeric values."""

        values = [float(v) for v in self._data.values() if isinstance(v, (int, float))]
        if not values:
            return 0.0
        total = sum(abs(v) for v in values)
        if total == 0.0:
            return 0.0
        probs = [abs(v) / total for v in values]
        return -sum(p * math.log2(max(p, 1e-9)) for p in probs)


class FieldOperator:
    """Common call signature for every field participant."""

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> Any:  # pragma: no cover - interface
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Core blueprint modules
# ---------------------------------------------------------------------------


class Oriphiel5DMemory:
    """Spiral memory that validates states via proof-of-resonance."""

    def __init__(self, dimension: int = 5) -> None:
        self.dimension = int(dimension)
        self.theta = 0.0
        self._states: List[List[float]] = []

    def update(self, vector: Iterable[float]) -> List[float]:
        values = [float(v) for v in vector]
        if len(values) != self.dimension:
            raise ValueError(f"Expected {self.dimension} dimensions, got {len(values)}")
        self.theta += math.pi / 7.0
        spiral = [math.sin(self.theta + i) for i in range(self.dimension)]
        stamped = [v + 0.05 * s for v, s in zip(values, spiral)]
        self._states.append(stamped)
        return stamped

    def proof_of_resonance(self, threshold: float = 0.5) -> bool:
        if not self._states:
            return False
        latest = self._states[-1]
        norm = math.sqrt(sum(v * v for v in latest))
        return norm >= threshold

    def history(self) -> List[List[float]]:
        return list(self._states)


class MandorlaConvergenceField:
    """Overlap computation between perception and intention vectors."""

    def __init__(self, dimension: int = 5) -> None:
        self.dimension = int(dimension)
        self.perception = [random.random() for _ in range(dimension)]
        self.intention = [random.random() for _ in range(dimension)]
        self._log: List[Dict[str, List[float]]] = []

    def project(self, vector: Iterable[float], rate: float = 0.1) -> List[float]:
        vec = [float(v) for v in vector]
        if len(vec) != self.dimension:
            raise ValueError("Vector dimensionality mismatch")
        self.perception = [p + rate * (v - p) for p, v in zip(self.perception, vec)]
        self.intention = [i + rate * (v - i) for i, v in zip(self.intention, vec)]
        mandorla = [(p + i) * 0.5 for p, i in zip(self.perception, self.intention)]
        self._log.append({"vector": vec, "mandorla": mandorla})
        return mandorla

    def overlap(self) -> float:
        num = sum(p * i for p, i in zip(self.perception, self.intention))
        denom = math.sqrt(sum(p * p for p in self.perception)) * math.sqrt(sum(i * i for i in self.intention))
        if denom == 0.0:
            return 0.0
        return num / denom

    def log(self) -> List[Dict[str, List[float]]]:
        return list(self._log)


class TripolarResonanceKernel(FieldOperator):
    """Implements the tripolar differential from the blueprint."""

    def __init__(self, kappa_a: float = 0.3, kappa_b: float = 0.25):
        self.kappa_a = float(kappa_a)
        self.kappa_b = float(kappa_b)
        self.phase = 0.0

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> float:
        psi, rho = float(context.get("psi", 0.5)), float(context.get("rho", 0.5))
        omega = float(field_state.get("omega", 1.0))
        theta_a = float(context.get("theta_a", 0.0))
        theta_b = float(context.get("theta_b", math.pi / 4.0))
        self.phase += omega + self.kappa_a * psi * math.sin(theta_a - self.phase)
        self.phase += self.kappa_b * rho * math.sin(theta_b - self.phase)
        signal = math.sin(self.phase)
        field_state["tripolar_output"] = signal
        return signal


class FieldTopologicalAdapter(FieldOperator):
    """Converts field gradients into discrete actuator values."""

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> int:
        gradient = float(field_state.get("tripolar_output", 0.0))
        return int(max(-1.0, min(1.0, gradient)) * 100)


class TINTATransducer(FieldOperator):
    """Transforms field tension into intention/impulse tuples."""

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> Dict[str, float]:
        entropy = field_state.entropy()
        pulse = float(field_state.get("tripolar_output", 0.0))
        return {"intention": pulse, "tension": entropy}


class GabrielFieldCell(FieldOperator):
    """Field-based Gabriel-Zelle with pluggable trident operator."""

    def __init__(self, trident: Callable[[Any, FieldState], Iterable[float]], memory: Oriphiel5DMemory,
                 field: MandorlaConvergenceField, modulator: Callable[[float, FieldState], float]) -> None:
        self.trident = trident
        self.memory = memory
        self.field = field
        self.modulator = modulator

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> Dict[str, Any]:
        psi, rho, omega = self.trident(input_data, context)
        resonance = psi * rho * omega
        scaled = self.modulator(resonance, field_state)
        imprint = self.memory.update([psi, rho, omega, scaled, field_state.entropy()])
        mandorla = self.field.project(imprint)
        return {"resonance": resonance, "scaled": scaled, "mandorla": mandorla}


def default_trident(input_data: Any, context: FieldState) -> List[float]:
    base = float(context.get("baseline", 0.5))
    spectrum = float(context.get("spectrum", 0.75))
    drift = float(context.get("drift", 0.1))
    psi = base + 0.1 * math.sin(time.time())
    rho = spectrum + 0.05 * math.cos(time.time())
    omega = 0.5 + drift
    return [psi, rho, omega]


def default_modulator(resonance: float, field_state: FieldState) -> float:
    phase = float(field_state.get("phase_bias", 0.5))
    return resonance * (0.5 + phase)


# ---------------------------------------------------------------------------
# QLOGIC / O.P.H.A.N. / Epigenetic Operators
# ---------------------------------------------------------------------------


class QLogicKernel(FieldOperator):
    """Spectral-logical self-modelling and entropy monitor."""

    def __init__(self) -> None:
        self.entropy_trace: List[float] = []

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> Dict[str, float]:
        ent = field_state.entropy()
        self.entropy_trace.append(ent)
        drift = statistics.fmean(self.entropy_trace[-5:]) if self.entropy_trace else ent
        threshold = 0.3 + min(0.4, drift * 0.1)
        field_state["qlogic_threshold"] = threshold
        return {"entropy": ent, "threshold": threshold}


class OphanKernel(FieldOperator):
    """Triggers singularity events when thresholds are exceeded."""

    def __init__(self, trigger: Callable[[FieldState], None]):
        self.trigger = trigger

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> Optional[str]:
        signal = float(field_state.get("tripolar_output", 0.0))
        threshold = float(field_state.get("qlogic_threshold", 0.5))
        if abs(signal) > threshold:
            self.trigger(field_state)
            return "singularity"
        return None


class FieldEmotionRegulationModule(FieldOperator):
    """Phase-based valence/arousal regulator."""

    def __init__(self, valence: float = 0.0, arousal: float = 0.0):
        self.valence = float(valence)
        self.arousal = float(arousal)

    def __call__(self, input_data: Any, context: FieldState, field_state: FieldState) -> Dict[str, float]:
        stimulus = float(input_data if isinstance(input_data, (int, float)) else 0.0)
        self.valence += 0.1 * stimulus
        self.arousal = max(0.0, min(self.arousal + 0.05 * abs(stimulus), 1.0))
        field_state["emotion"] = (self.valence, self.arousal)
        return {"valence": self.valence, "arousal": self.arousal}


class EpigeneticOperator:
    """Meta-layer that can mutate operator registries on demand."""

    def mutate(self, registry: "FieldOperatorRegistry", seed: Optional[int] = None) -> None:
        rng = random.Random(seed)
        if not registry.operators:
            return
        name = rng.choice(list(registry.operators))
        operator = registry.operators[name]
        registry.operators[name] = lambda *args, _op=operator, _factor=rng.uniform(0.8, 1.2), **kwargs: _scale_call(
            _op, _factor, *args, **kwargs
        )


def _scale_call(operator: FieldOperator, factor: float, *args: Any, **kwargs: Any) -> Any:
    result = operator(*args, **kwargs)
    if isinstance(result, (int, float)):
        return result * factor
    return result


class CubeZoomLayer:
    """Dynamic overlay mechanism for strategy switching."""

    def __init__(self) -> None:
        self.layers: List[Dict[str, Any]] = []

    def mount(self, field_state: FieldState, payload: Dict[str, Any], mode: str = "overlay") -> None:
        entry = {"mode": mode, "payload": payload, "timestamp": time.time()}
        self.layers.append(entry)
        if mode == "inline":
            field_state.update(payload)

    def unmount(self, field_state: FieldState) -> None:
        if not self.layers:
            return
        layer = self.layers.pop()
        if layer["mode"] == "inline":
            for key in layer["payload"]:
                field_state.pop(key, None)


# ---------------------------------------------------------------------------
# Operator registry and orchestration helpers
# ---------------------------------------------------------------------------


class FieldOperatorRegistry:
    """Runtime registry for field participants."""

    def __init__(self) -> None:
        self.operators: Dict[str, FieldOperator] = {}

    def register(self, name: str, operator: FieldOperator) -> None:
        self.operators[name] = operator

    def get(self, name: str) -> FieldOperator:
        return self.operators[name]

    def __contains__(self, item: str) -> bool:
        return item in self.operators


def mount_layer(field: MandorlaConvergenceField, layer: CubeZoomLayer, payload: Dict[str, Any], mode: str = "overlay") -> None:
    layer.mount(FieldState(), payload, mode)
    numeric_values = [float(v) for v in payload.values() if isinstance(v, (int, float))]
    if not numeric_values:
        numeric_values = [0.0] * field.dimension
    if len(numeric_values) < field.dimension:
        numeric_values.extend([numeric_values[-1]] * (field.dimension - len(numeric_values)))
    elif len(numeric_values) > field.dimension:
        numeric_values = numeric_values[: field.dimension]
    field.project(numeric_values)


def export_field_state(field_state: FieldState) -> str:
    """Serialize the field state into JSON for the audit trail."""

    return json.dumps(dict(field_state))


__all__ = [
    "CubeZoomLayer",
    "FieldEmotionRegulationModule",
    "EpigeneticOperator",
    "FieldOperator",
    "FieldOperatorRegistry",
    "FieldState",
    "FieldTopologicalAdapter",
    "GabrielFieldCell",
    "MandorlaConvergenceField",
    "mount_layer",
    "OphanKernel",
    "Oriphiel5DMemory",
    "QLogicKernel",
    "TINTATransducer",
    "TripolarResonanceKernel",
    "default_modulator",
    "default_trident",
    "export_field_state",
]

