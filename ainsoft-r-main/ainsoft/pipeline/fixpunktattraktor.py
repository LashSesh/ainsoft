"""Fixpunktattraktor engine and operators for AinSOFT.

This module implements the singularity-channel pipeline described in the
specification.  It combines multiple operators – Wurmloch-Trichter, Doppelkick,
Pfadinvarianz, and Schwellen-Sweep – inside a consensus gate that executes the
primal and dual Simplex passes.  The operators work on :class:`FixpunktCandidate`
objects and transparently propagate metadata while remaining agnostic of the
actual payload type.

All network interactions in the wider system can supply an optional SOCKS5 proxy
configuration; the fixpunkt pipeline therefore only focuses on candidate
selection and remains transport independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

try:  # pragma: no cover - optional dependency
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

from .blueprints import (
    DTTModulator,
    EmotionRegulationModule,
    TripolarResonanceModule,
    vesica_overlap,
)

@dataclass
class FixpunktCandidate:
    """Container for payloads that traverse the operator chain.

    The metadata dictionary allows transformers to store arbitrary contextual
    information (e.g. path signatures, threshold hits).  Candidates are treated
    as immutable – helper methods return shallow copies with updated metadata so
    different branches can evolve independently.
    """

    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "FixpunktCandidate":
        return FixpunktCandidate(self.value, dict(self.metadata))

    def with_metadata(self, **updates: Any) -> "FixpunktCandidate":
        merged = dict(self.metadata)
        merged.update(updates)
        return FixpunktCandidate(self.value, merged)


@dataclass
class FixpunktState:
    """Represents the intermediate state of the operator chain."""

    candidates: List[FixpunktCandidate]
    selected: Optional[FixpunktCandidate] = None
    threshold_hits: Dict[int, List[float]] = field(default_factory=dict)

    def clone(self) -> "FixpunktState":
        return FixpunktState(
            candidates=[candidate.copy() for candidate in self.candidates],
            selected=self.selected.copy() if self.selected else None,
            threshold_hits={k: list(v) for k, v in self.threshold_hits.items()},
        )

    def evolve(
        self,
        *,
        candidates: Optional[Iterable[FixpunktCandidate]] = None,
        selected: Optional[FixpunktCandidate] = None,
        threshold_hits: Optional[Dict[int, List[float]]] = None,
    ) -> "FixpunktState":
        return FixpunktState(
            candidates=list(candidates) if candidates is not None else self.candidates,
            selected=selected if selected is not None else self.selected,
            threshold_hits=threshold_hits if threshold_hits is not None else self.threshold_hits,
        )


def _call_with_candidate(func: Callable[..., Any], candidate: FixpunktCandidate, *args: Any) -> Any:
    """Invoke *func* with a candidate while gracefully handling signatures."""

    try:
        return func(candidate, *args)
    except TypeError:
        return func(candidate.value, *args)


class WurmlochTrichter:
    """Selects the candidate with the strongest score."""

    def __init__(self, scoring_func: Callable[[Any], float]):
        self.scoring_func = scoring_func

    def apply(self, state: FixpunktState) -> FixpunktState:
        if not state.candidates:
            return state.evolve(selected=None)

        def resolve_score(candidate: FixpunktCandidate) -> float:
            score = _call_with_candidate(self.scoring_func, candidate)
            return float(score)

        best = max(state.candidates, key=resolve_score)
        return state.evolve(selected=best)


class Doppelkick:
    """Filters candidates where two impulses agree on the transformation."""

    def __init__(self, impulse_a: Callable[[Any], Any], impulse_b: Callable[[Any], Any]):
        self.impulse_a = impulse_a
        self.impulse_b = impulse_b

    def apply(self, state: FixpunktState) -> FixpunktState:
        if not state.candidates:
            return state

        stable: List[FixpunktCandidate] = []
        for candidate in state.candidates:
            result_a = _call_with_candidate(self.impulse_a, candidate)
            result_b = _call_with_candidate(self.impulse_b, candidate)
            if result_a == result_b:
                stable.append(candidate.with_metadata(doppelkick_signature=result_a))
        return state.evolve(candidates=stable)


class Pfadinvarianz:
    """Ensures that every path function converges to the same representation."""

    def __init__(self, path_funcs: List[Callable[[Any], Any]]):
        self.path_funcs = path_funcs

    def apply(self, state: FixpunktState) -> FixpunktState:
        if not state.candidates or not self.path_funcs:
            return state

        invariant: List[FixpunktCandidate] = []
        for candidate in state.candidates:
            signatures = [_call_with_candidate(func, candidate) for func in self.path_funcs]
            if not signatures:
                continue
            if all(sig == signatures[0] for sig in signatures[1:]):
                invariant.append(candidate.with_metadata(path_signature=signatures[0]))
        return state.evolve(candidates=invariant)


class SchwellenSweep:
    """Evaluates candidates across a sweep of thresholds."""

    def __init__(self, threshold_range: List[float], evaluator: Callable[[Any, float], bool]):
        self.threshold_range = threshold_range
        self.evaluator = evaluator

    def apply(self, state: FixpunktState) -> FixpunktState:
        if not state.candidates or not self.threshold_range:
            return state

        retained: List[FixpunktCandidate] = []
        hits: Dict[int, List[float]] = {}
        for idx, candidate in enumerate(state.candidates):
            passed = [thr for thr in self.threshold_range if _call_with_candidate(self.evaluator, candidate, thr)]
            if passed:
                retained.append(candidate.with_metadata(threshold_hits=passed))
                hits[idx] = passed
        return state.evolve(candidates=retained, threshold_hits=hits)


class _DTTWurmlochTrichter(WurmlochTrichter):
    """DTT enhanced variant of :class:`WurmlochTrichter`."""

    def __init__(self, scoring_func: Callable[[Any], float], modulator: DTTModulator):
        super().__init__(scoring_func)
        self.modulator = modulator

    def apply(self, state: FixpunktState) -> FixpunktState:  # type: ignore[override]
        if not state.candidates:
            return state.evolve(selected=None)

        weight = max(self.modulator.value(), 0.0)
        if weight == 0.0:
            weight = 1e-6

        def resolve(candidate: FixpunktCandidate) -> float:
            base_score = float(_call_with_candidate(self.scoring_func, candidate))
            return base_score * weight

        best = max(state.candidates, key=resolve)
        selected = best.with_metadata(dtt_weight=weight, dtt_score=resolve(best))
        return state.evolve(selected=selected)


class _DTTSchwellenSweep(SchwellenSweep):
    """DTT enhanced threshold sweep with dynamic range modulation."""

    def __init__(
        self,
        threshold_range: List[float],
        evaluator: Callable[[Any, float], bool],
        modulator: DTTModulator,
    ) -> None:
        super().__init__(threshold_range, evaluator)
        self.modulator = modulator

    def apply(self, state: FixpunktState) -> FixpunktState:  # type: ignore[override]
        if not state.candidates or not self.threshold_range:
            return state

        factor = max(self.modulator.value(), 0.0)
        if factor == 0.0:
            factor = 1e-6
        dynamic_range = [min(max(thr * factor, 0.0), 1.0) for thr in self.threshold_range]

        retained: List[FixpunktCandidate] = []
        hits: Dict[int, List[float]] = {}
        for idx, candidate in enumerate(state.candidates):
            passed = [thr for thr in dynamic_range if _call_with_candidate(self.evaluator, candidate, thr)]
            if passed:
                retained.append(candidate.with_metadata(threshold_hits=passed, dtt_thresholds=passed, dtt_factor=factor))
                hits[idx] = passed
        return state.evolve(candidates=retained, threshold_hits=hits)


class MerkabaKonsensGate:
    """Executes primal and dual passes and checks for consensus."""

    def __init__(
        self,
        operatoren: Dict[str, Callable[[FixpunktState], FixpunktState]],
        *,
        consensus_fn: Optional[Callable[[FixpunktState, FixpunktState], Optional[FixpunktCandidate]]] = None,
    ):
        self.operatoren = operatoren
        self.consensus_fn = consensus_fn

    def _execute(self, sequence: List[str], window: FixpunktState) -> FixpunktState:
        state = window.clone()
        for key in sequence:
            operator = self.operatoren[key]
            state = operator(state)
            if not state.candidates and state.selected is None:
                break
        return state

    def process(self, window: Iterable[FixpunktCandidate]) -> Optional[FixpunktCandidate]:
        initial_state = FixpunktState(list(window))

        primal_order = ["DK", "SW", "PI", "WT"]
        dual_order = ["WT", "PI", "SW", "DK"]

        state_primal = self._execute(primal_order, initial_state)
        state_dual = self._execute(dual_order, initial_state)

        candidate_primal = state_primal.selected or (state_primal.candidates[0] if state_primal.candidates else None)
        candidate_dual = state_dual.selected or (state_dual.candidates[0] if state_dual.candidates else None)

        if self.consensus_fn:
            consensus_candidate = self.consensus_fn(state_primal, state_dual)
            if consensus_candidate is not None:
                return consensus_candidate

        if candidate_primal and candidate_dual and candidate_primal.value == candidate_dual.value:
            return candidate_primal
        return None


class FixpunktAttraktorEngine:
    """High-level engine that feeds candidates through the consensus gate."""

    def __init__(
        self,
        candidate_generator: Callable[[], Iterable[Any]],
        scorer: Callable[[Any], float],
        impulse_funcs: List[Callable[[Any], Any]],
        threshold_evaluator: Callable[[Any, float], bool],
        threshold_range: List[float],
        *,
        dtt_modulators: Optional[Mapping[str, DTTModulator]] = None,
        resonance_module: Optional[TripolarResonanceModule] = None,
        emotion_module: Optional[EmotionRegulationModule] = None,
        consensus_fn: Optional[Callable[[FixpunktState, FixpunktState], Optional[FixpunktCandidate]]] = None,
    ):
        if len(impulse_funcs) < 2:
            raise ValueError("At least two impulse functions are required for Doppelkick")

        self.candidate_generator = candidate_generator
        self.scorer = scorer
        self.impulse_funcs = impulse_funcs
        self.threshold_evaluator = threshold_evaluator
        self.threshold_range = threshold_range

        self.modulators = {str(key).lower(): value for key, value in (dtt_modulators or {}).items()}
        self.resonance_module = resonance_module
        self.emotion_module = emotion_module

        self.wt = self._build_wurmloch()
        self.dk = Doppelkick(self.impulse_funcs[0], self.impulse_funcs[1])
        self.pi = Pfadinvarianz(self.impulse_funcs)
        self.sw = self._build_schwelle()
        self.gate = MerkabaKonsensGate(
            {
                "WT": self.wt.apply,
                "DK": self.dk.apply,
                "PI": self.pi.apply,
                "SW": self.sw.apply,
            },
            consensus_fn=consensus_fn,
        )

    def _normalise_candidates(self, items: Iterable[Any]) -> List[FixpunktCandidate]:
        normalised: List[FixpunktCandidate] = []
        for item in items:
            if isinstance(item, FixpunktCandidate):
                normalised.append(item.copy())
            else:
                normalised.append(FixpunktCandidate(item))
        return normalised

    def _modulator_for(self, *aliases: str) -> Optional[DTTModulator]:
        for alias in aliases:
            key = alias.lower()
            if key in self.modulators:
                return self.modulators[key]
        return None

    def _build_wurmloch(self) -> WurmlochTrichter:
        modulator = self._modulator_for("wt", "wurmloch", "wurmloch_trichter")
        if modulator:
            return _DTTWurmlochTrichter(self.scorer, modulator)
        return WurmlochTrichter(self.scorer)

    def _build_schwelle(self) -> SchwellenSweep:
        modulator = self._modulator_for("sw", "threshold", "schwelle")
        if modulator:
            return _DTTSchwellenSweep(self.threshold_range, self.threshold_evaluator, modulator)
        return SchwellenSweep(self.threshold_range, self.threshold_evaluator)

    def _finalise_candidate(self, candidate: Optional[FixpunktCandidate]) -> Optional[FixpunktCandidate]:
        if candidate is None:
            if self.emotion_module:
                self.emotion_module.modulate(-1.0)
            return None

        updates: Dict[str, Any] = {}
        if self.resonance_module:
            updates["resonance"] = self.resonance_module.resonance()
        if self.emotion_module:
            self.emotion_module.modulate(1.0)
        if self.emotion_module:
            updates["emotion_state"] = self.emotion_module.state()
        if updates:
            candidate = candidate.with_metadata(**updates)
        return candidate

    def run(self) -> Optional[FixpunktCandidate]:
        candidates = self.candidate_generator()
        normalised = self._normalise_candidates(candidates)
        selected = self.gate.process(normalised)
        return self._finalise_candidate(selected)


__all__ = [
    "FixpunktAttraktorEngine",
    "FixpunktCandidate",
    "FixpunktState",
    "MerkabaKonsensGate",
    "Pfadinvarianz",
    "SchwellenSweep",
    "WurmlochTrichter",
    "Doppelkick",
]


def _extract_vector(candidate: FixpunktCandidate) -> Optional[Sequence[float]]:
    value = candidate.value
    metadata = candidate.metadata

    if isinstance(metadata, Mapping):
        meta_vector = metadata.get("vector") or metadata.get("phase_vector")
        if meta_vector is not None:
            return [float(x) for x in meta_vector]

    if isinstance(value, Mapping):
        raw = value.get("vector") or value.get("phases") or value.get("phase_vector")
        if raw is not None:
            return [float(x) for x in raw]

    if np is not None and isinstance(value, np.ndarray):
        return [float(x) for x in value.tolist()]

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        try:
            return [float(x) for x in value]
        except (TypeError, ValueError):
            return None

    return None


def mandorla_consensus(
    state_primal: FixpunktState,
    state_dual: FixpunktState,
    *,
    threshold: float = 0.8,
) -> Optional[FixpunktCandidate]:
    """Consensus helper that uses :func:`vesica_overlap` to collapse states."""

    candidate_primal = state_primal.selected or (state_primal.candidates[0] if state_primal.candidates else None)
    candidate_dual = state_dual.selected or (state_dual.candidates[0] if state_dual.candidates else None)

    if not candidate_primal or not candidate_dual:
        return None

    vector_a = _extract_vector(candidate_primal)
    vector_b = _extract_vector(candidate_dual)

    if vector_a is None or vector_b is None:
        if candidate_primal.value == candidate_dual.value:
            return candidate_primal
        return None

    if vesica_overlap(vector_a, vector_b, threshold=threshold):
        if candidate_primal.value == candidate_dual.value:
            return candidate_primal.with_metadata(mandorla_overlap=True, mandorla_threshold=threshold)

        merged_metadata = dict(candidate_primal.metadata)
        merged_metadata.update(candidate_dual.metadata)
        merged_metadata.update({"mandorla_overlap": True, "mandorla_threshold": threshold})
        return FixpunktCandidate(candidate_primal.value, merged_metadata)

    return None


def spectral_threshold_evaluator(candidate: Any, threshold: float) -> bool:
    """Evaluate a candidate using the :func:`triton_scorer` helper."""

    from .triton_scorer import triton_scorer

    score = triton_scorer(candidate)
    return score >= threshold


__all__.extend(["spectral_threshold_evaluator", "mandorla_consensus"])
