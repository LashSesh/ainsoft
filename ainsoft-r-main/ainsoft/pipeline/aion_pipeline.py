"""Pipeline orchestration utilities for AinSOFT."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from ainsoft.core.network import ProxyConfig

Generator = Callable[[], Any]
Transformer = Callable[[Any], Any]
Dispatcher = Callable[[Any, Optional[ProxyConfig]], Any]


def load_pipeline_config(path: str = "ainsoft/config/schema.yaml") -> Mapping[str, Any]:
    """Load the pipeline and fixpunkt configuration from a YAML file."""

    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - exercised in offline environments
        from ainsoft.config.defaults import DEFAULT_PIPELINE_CONFIG

        return DEFAULT_PIPELINE_CONFIG

    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return {
        "pipeline": data.get("pipeline", {}),
        "fixpunkt": data.get("fixpunkt", {}),
    }


def _resolve_callable(spec: Any) -> Callable:
    if callable(spec):
        return spec
    if not isinstance(spec, str):
        raise TypeError(f"Cannot resolve callable from {spec!r}")
    if ":" in spec:
        module_name, attr = spec.split(":", 1)
    else:
        module_name, attr = spec.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, attr)


class PipelineOrchestrator:
    """Kaskadiert Generatoren, Transformer und Dispatcher flexibel."""

    def __init__(
        self,
        generators: Sequence[Generator],
        transformers: Sequence[Transformer] | None = None,
        dispatchers: Sequence[Dispatcher] | None = None,
    ) -> None:
        self.generators = list(generators)
        self.transformers = list(transformers or [])
        self.dispatchers = list(dispatchers or [])
        self.history: List[Mapping[str, Any]] = []

    def run(self, proxy_cfg: Optional[ProxyConfig] = None) -> List[Mapping[str, Any]]:
        """Execute the pipeline and return execution artefacts."""

        results: List[Mapping[str, Any]] = []
        for generator in self.generators:
            payload = generator()
            stages = [payload]
            transformed = payload
            for transformer in self.transformers:
                transformed = transformer(transformed)
                stages.append(transformed)

            dispatch_results: List[Any] = []
            final_payload = transformed
            for dispatcher in self.dispatchers:
                dispatch_output = dispatcher(final_payload, proxy_cfg)
                dispatch_results.append(dispatch_output)
                if dispatch_output is not None and not isinstance(dispatch_output, Mapping):
                    final_payload = dispatch_output
                elif isinstance(dispatch_output, Mapping) and "payload" in dispatch_output:
                    final_payload = dispatch_output["payload"]

            results.append(
                {
                    "generator": getattr(generator, "__name__", repr(generator)),
                    "stages": stages,
                    "dispatch": dispatch_results,
                    "final": final_payload,
                }
            )
        self.history = results
        return results

    def generate_candidates(self, proxy_cfg: Optional[ProxyConfig] = None) -> List[Any]:
        """Helper to obtain final payloads suitable for FixpunktAttraktorEngine."""

        executions = self.run(proxy_cfg=proxy_cfg)
        return [item["final"] for item in executions]


def build_orchestrator_from_config(config: Mapping[str, Any]) -> PipelineOrchestrator:
    generators = [_resolve_callable(item) for item in config.get("generators", [])]
    transformers = [_resolve_callable(item) for item in config.get("transformers", [])]
    dispatchers = [_resolve_callable(item) for item in config.get("dispatchers", [])]
    return PipelineOrchestrator(generators, transformers, dispatchers)


def build_fixpunkt_engine_from_config(
    config: Mapping[str, Any],
    *,
    proxy_cfg: Optional[ProxyConfig] = None,
) -> "FixpunktAttraktorEngine":
    from .blueprints import DTTModulator, DTT_TRM, EmotionRegulationModule, TripolarResonanceModule
    from .fixpunktattraktor import (
        FixpunktAttraktorEngine,
        FixpunktCandidate,
        FixpunktState,
        mandorla_consensus,
        spectral_threshold_evaluator,
    )
    from .triton_scorer import triton_scorer

    pipeline_cfg = config.get("pipeline", {})
    fixpunkt_cfg = config.get("fixpunkt", {})

    orchestrator = build_orchestrator_from_config(pipeline_cfg)

    scorer_spec = fixpunkt_cfg.get("scorer")
    scorer = _resolve_callable(scorer_spec) if scorer_spec else triton_scorer

    impulse_specs = fixpunkt_cfg.get("impulses", [])
    threshold_range = fixpunkt_cfg.get("threshold_range", [])
    evaluator_spec = fixpunkt_cfg.get("threshold_evaluator")

    impulse_funcs = [_resolve_callable(spec) for spec in impulse_specs]
    if len(impulse_funcs) < 2:
        identity = lambda payload, *_: payload  # noqa: E731 - simple fallback helper
        while len(impulse_funcs) < 2:
            impulse_funcs.append(identity)
    evaluator = _resolve_callable(evaluator_spec) if evaluator_spec else spectral_threshold_evaluator

    modulators_cfg = fixpunkt_cfg.get("dtt")
    modulators: Dict[str, DTTModulator] = {}
    if isinstance(modulators_cfg, Mapping):
        for key, params in modulators_cfg.items():
            if not isinstance(params, Mapping):
                continue
            init_kwargs = {k: params[k] for k in ("omega", "phase", "amplitude", "offset", "mode") if k in params}
            modulators[str(key)] = DTTModulator(**init_kwargs)

    resonance_spec = fixpunkt_cfg.get("resonance_module")
    resonance_module: Optional[TripolarResonanceModule] = None
    if resonance_spec:
        if isinstance(resonance_spec, Mapping):
            phases = resonance_spec.get("phases", [])
            if phases:
                if "dtt" in resonance_spec and isinstance(resonance_spec["dtt"], Mapping):
                    mod_params = {k: resonance_spec["dtt"][k] for k in ("omega", "phase", "amplitude", "offset", "mode") if k in resonance_spec["dtt"]}
                    resonance_module = DTT_TRM(phases, DTTModulator(**mod_params))
                else:
                    resonance_module = TripolarResonanceModule(phases)
        else:
            factory = _resolve_callable(resonance_spec)
            resonance_module = factory()

    emotion_spec = fixpunkt_cfg.get("emotion_module")
    emotion_module: Optional[EmotionRegulationModule] = None
    if emotion_spec:
        if isinstance(emotion_spec, Mapping):
            kwargs = {k: float(emotion_spec[k]) for k in ("valence", "arousal") if k in emotion_spec}
            emotion_module = EmotionRegulationModule(**kwargs)
        else:
            factory = _resolve_callable(emotion_spec)
            emotion_module = factory()

    consensus_cfg = fixpunkt_cfg.get("consensus")
    consensus_fn: Optional[Callable[[Any, Any], Optional[FixpunktCandidate]]] = None
    if consensus_cfg:
        if isinstance(consensus_cfg, Mapping):
            callable_spec = consensus_cfg.get("callable")
            kwargs = consensus_cfg.get("kwargs", {}) if isinstance(consensus_cfg.get("kwargs"), Mapping) else {}
            if callable_spec:
                consensus_callable = _resolve_callable(callable_spec)

                def _wrapped(state_primal: FixpunktState, state_dual: FixpunktState, *, _fn=consensus_callable, _kwargs=kwargs):
                    return _fn(state_primal, state_dual, **_kwargs)

                consensus_fn = _wrapped
        else:
            consensus_callable = _resolve_callable(consensus_cfg)
            consensus_fn = consensus_callable
    if consensus_fn is None and modulators:
        consensus_fn = mandorla_consensus

    def candidate_generator() -> Iterable[FixpunktCandidate]:
        final_payloads = orchestrator.generate_candidates(proxy_cfg=proxy_cfg)
        return [FixpunktCandidate(payload) for payload in final_payloads]

    return FixpunktAttraktorEngine(
        candidate_generator=candidate_generator,
        scorer=scorer,
        impulse_funcs=impulse_funcs,
        threshold_evaluator=evaluator,
        threshold_range=list(threshold_range),
        dtt_modulators=modulators or None,
        resonance_module=resonance_module,
        emotion_module=emotion_module,
        consensus_fn=consensus_fn,
    )


__all__ = [
    "PipelineOrchestrator",
    "load_pipeline_config",
    "build_orchestrator_from_config",
    "build_fixpunkt_engine_from_config",
]
