//! Resonance pipeline orchestration for AinSOFT.
//!
//! The pipeline module mirrors the original Python pipeline so the Rust
//! implementation can run the resonance laboratory without any Web3
//! dependencies. It provides:
//!
//! - `PipelineOrchestrator` to cascade generators, transformers, and dispatchers
//! - `FixpunktAttraktorEngine` to score and threshold pipeline candidates
//! - Config helpers that load the legacy YAML schema (`pipeline` + `fixpunkt`)
//!
//! All payloads are represented as `serde_json::Value` to stay flexible and to
//! interoperate with the mesh and phantomload modules.

use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex};

use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::core::ProxyConfig;
use crate::DEFAULT_TICK_INTERVAL;

/// General pipeline error type.
#[derive(Debug, thiserror::Error)]
pub enum PipelineError {
    /// Configuration or IO failure.
    #[error("config error: {0}")]
    Config(String),
    /// Builder resolution failure.
    #[error("unknown callable: {0}")]
    UnknownCallable(String),
}

/// Type aliases for pipeline callables.
pub type Generator = Arc<dyn Fn() -> Value + Send + Sync>;
pub type Transformer = Arc<dyn Fn(Value) -> Value + Send + Sync>;
pub type Dispatcher = Arc<dyn Fn(Value, Option<&ProxyConfig>) -> Option<Value> + Send + Sync>;

/// Execution artefacts for a single generator run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineExecution {
    pub generator: String,
    pub stages: Vec<Value>,
    pub dispatch: Vec<Option<Value>>,
    pub final_payload: Value,
}

/// Cascades generators, transformers, and dispatchers.
pub struct PipelineOrchestrator {
    generators: Vec<(String, Generator)>,
    transformers: Vec<(String, Transformer)>,
    dispatchers: Vec<(String, Dispatcher)>,
    pub history: Vec<PipelineExecution>,
}

impl Default for PipelineOrchestrator {
    fn default() -> Self {
        Self {
            generators: Vec::new(),
            transformers: Vec::new(),
            dispatchers: Vec::new(),
            history: Vec::new(),
        }
    }
}

impl PipelineOrchestrator {
    /// Create an empty orchestrator.
    pub fn new() -> Self {
        Self::default()
    }

    /// Register a generator.
    pub fn with_generator(mut self, name: impl Into<String>, f: Generator) -> Self {
        self.generators.push((name.into(), f));
        self
    }

    /// Register a transformer.
    pub fn with_transformer(mut self, name: impl Into<String>, f: Transformer) -> Self {
        self.transformers.push((name.into(), f));
        self
    }

    /// Register a dispatcher.
    pub fn with_dispatcher(mut self, name: impl Into<String>, f: Dispatcher) -> Self {
        self.dispatchers.push((name.into(), f));
        self
    }

    /// Run the pipeline and return execution artefacts.
    pub fn run(&mut self, proxy_cfg: Option<&ProxyConfig>) -> Vec<PipelineExecution> {
        let mut results = Vec::new();

        for (gen_name, generator) in &self.generators {
            let mut stages = Vec::new();
            let mut payload = generator();
            stages.push(payload.clone());

            for (_, transformer) in &self.transformers {
                payload = transformer(payload);
                stages.push(payload.clone());
            }

            let mut dispatch_results = Vec::new();
            let mut final_payload = payload.clone();
            for (_, dispatcher) in &self.dispatchers {
                let output = dispatcher(final_payload.clone(), proxy_cfg);
                if let Some(ref new_payload) = output {
                    final_payload = new_payload.clone();
                }
                dispatch_results.push(output);
            }

            results.push(PipelineExecution {
                generator: gen_name.clone(),
                stages,
                dispatch: dispatch_results,
                final_payload,
            });
        }

        self.history = results.clone();
        results
    }

    /// Convenience helper to obtain only the final payloads (used by Fixpunkt).
    pub fn generate_candidates(&mut self, proxy_cfg: Option<&ProxyConfig>) -> Vec<Value> {
        self.run(proxy_cfg)
            .into_iter()
            .map(|item| item.final_payload)
            .collect()
    }
}

/// Fixpunkt candidate (wrapper around the pipeline payload).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixpunktCandidate {
    pub payload: Value,
}

/// Fixpunkt evaluation state for a single impulse branch.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixpunktState {
    pub payload: Value,
    pub score: f64,
    pub impulse: f64,
    pub stage: String,
}

/// Scoring function.
pub type ScoreFn = Arc<dyn Fn(&FixpunktCandidate) -> f64 + Send + Sync>;
/// Impulse function.
pub type ImpulseFn = Arc<dyn Fn(&FixpunktCandidate, f64) -> FixpunktState + Send + Sync>;
/// Threshold evaluator; returns true if candidate passes thresholds.
pub type ThresholdEvaluator =
    Arc<dyn Fn(&FixpunktState, &FixpunktState, &[f64]) -> bool + Send + Sync>;
/// Consensus function to merge primal/dual states.
pub type ConsensusFn =
    Arc<dyn Fn(&FixpunktState, &FixpunktState) -> Option<FixpunktCandidate> + Send + Sync>;

/// Fixpunkt result record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixpunktResult {
    pub candidates: Vec<FixpunktReport>,
    pub accepted: Vec<FixpunktCandidate>,
}

/// Detailed execution report for a single candidate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixpunktReport {
    pub candidate: FixpunktCandidate,
    pub score: f64,
    pub primal: FixpunktState,
    pub dual: FixpunktState,
    pub accepted: bool,
    pub consensus: Option<FixpunktCandidate>,
}

/// Fixpunkt Attraktor engine for resonance calibration.
pub struct FixpunktAttraktorEngine {
    candidate_generator: Arc<dyn Fn() -> Vec<FixpunktCandidate> + Send + Sync>,
    scorer: ScoreFn,
    impulse_funcs: Vec<ImpulseFn>,
    threshold_evaluator: ThresholdEvaluator,
    threshold_range: Vec<f64>,
    consensus_fn: Option<ConsensusFn>,
}

impl FixpunktAttraktorEngine {
    /// Build a new engine.
    pub fn new(
        candidate_generator: Arc<dyn Fn() -> Vec<FixpunktCandidate> + Send + Sync>,
        scorer: ScoreFn,
        impulse_funcs: Vec<ImpulseFn>,
        threshold_evaluator: ThresholdEvaluator,
        threshold_range: Vec<f64>,
        consensus_fn: Option<ConsensusFn>,
    ) -> Self {
        let mut impulses = impulse_funcs;
        if impulses.is_empty() {
            impulses.push(default_impulse());
        }
        if impulses.len() == 1 {
            impulses.push(impulses[0].clone());
        }

        Self {
            candidate_generator,
            scorer,
            impulse_funcs: impulses,
            threshold_evaluator,
            threshold_range,
            consensus_fn,
        }
    }

    /// Execute the Fixpunkt evaluation.
    pub fn run(&self) -> FixpunktResult {
        let mut reports = Vec::new();
        let mut accepted = Vec::new();

        for candidate in (self.candidate_generator)() {
            let score = (self.scorer)(&candidate);
            let primal = (self.impulse_funcs[0])(&candidate, score);
            let dual = (self.impulse_funcs[1])(&candidate, score);
            let passes = (self.threshold_evaluator)(&primal, &dual, &self.threshold_range);

            let consensus = self.consensus_fn.as_ref().and_then(|f| f(&primal, &dual));

            if passes {
                if let Some(ref merged) = consensus {
                    accepted.push(merged.clone());
                } else {
                    accepted.push(candidate.clone());
                }
            }

            reports.push(FixpunktReport {
                candidate: candidate.clone(),
                score,
                primal,
                dual,
                accepted: passes,
                consensus,
            });
        }

        FixpunktResult {
            candidates: reports,
            accepted,
        }
    }
}

/// Default impulse uses the score as spectral amplitude and encodes a small
/// phase shift derived from the payload entropy.
pub fn default_impulse() -> ImpulseFn {
    Arc::new(|candidate, score| {
        let entropy = payload_entropy(&candidate.payload);
        let phase = (entropy % 1.0) * std::f64::consts::PI;
        let impulse = score * (phase.cos() + DEFAULT_TICK_INTERVAL);
        FixpunktState {
            payload: candidate.payload.clone(),
            score,
            impulse,
            stage: "default".to_string(),
        }
    })
}

/// Default scorer inspired by the legacy Triton scorer.
pub fn triton_scorer(candidate: &FixpunktCandidate) -> f64 {
    match &candidate.payload {
        Value::Array(items) => {
            let sum = items
                .iter()
                .filter_map(|v| v.as_f64())
                .fold(0.0, |acc, v| acc + v.abs());
            let norm = (sum / items.len().max(1) as f64).sqrt();
            (norm.tanh() + 1.0) / 2.0
        }
        Value::Object(map) => {
            let mut sum = 0.0;
            for v in map.values() {
                if let Some(num) = v.as_f64() {
                    sum += num.abs();
                }
            }
            (sum.log10().tanh() + 1.0) / 2.0
        }
        _ => 0.5,
    }
}

/// Spectral evaluator compares impulse symmetry against configured thresholds.
pub fn spectral_threshold_evaluator(
    primal: &FixpunktState,
    dual: &FixpunktState,
    thresholds: &[f64],
) -> bool {
    let average = (primal.impulse.abs() + dual.impulse.abs()) / 2.0;
    let spread = (primal.impulse - dual.impulse).abs();
    let level = thresholds
        .get(1)
        .copied()
        .or_else(|| thresholds.first().copied())
        .unwrap_or(0.5);
    average >= level && spread <= level
}

/// Merge primal and dual states when they resonate closely.
pub fn mandorla_consensus(
    primal: &FixpunktState,
    dual: &FixpunktState,
) -> Option<FixpunktCandidate> {
    let delta = (primal.impulse - dual.impulse).abs();
    if delta <= 0.05 {
        let merged = match (&primal.payload, &dual.payload) {
            (Value::Array(a), Value::Array(b)) if a.len() == b.len() => {
                let blended: Vec<Value> = a
                    .iter()
                    .zip(b.iter())
                    .map(|(x, y)| match (x.as_f64(), y.as_f64()) {
                        (Some(xv), Some(yv)) => Value::from((xv + yv) / 2.0),
                        _ => x.clone(),
                    })
                    .collect();
                Value::Array(blended)
            }
            _ => primal.payload.clone(),
        };
        Some(FixpunktCandidate { payload: merged })
    } else {
        None
    }
}

/// Simple entropy estimator to preserve the spirit of the legacy resonance logic.
fn payload_entropy(payload: &Value) -> f64 {
    match payload {
        Value::Array(items) => {
            let mut histogram = HashMap::new();
            for item in items {
                let key = item.to_string();
                *histogram.entry(key).or_insert(0usize) += 1;
            }
            shannon_entropy(histogram.values().map(|count| *count as f64).collect())
        }
        Value::Object(map) => shannon_entropy(map.values().filter_map(|v| v.as_f64()).collect()),
        _ => 0.0,
    }
}

fn shannon_entropy(samples: Vec<f64>) -> f64 {
    if samples.is_empty() {
        return 0.0;
    }
    let sum: f64 = samples.iter().copied().sum();
    if sum == 0.0 {
        return 0.0;
    }
    samples
        .iter()
        .filter(|&&v| v > 0.0)
        .map(|&v| {
            let p = v / sum;
            -p * p.log2()
        })
        .sum()
}

/// Pipeline configuration section (legacy schema compatibility).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PipelineSectionConfig {
    #[serde(default)]
    pub generators: Vec<String>,
    #[serde(default)]
    pub transformers: Vec<String>,
    #[serde(default)]
    pub dispatchers: Vec<String>,
}

/// Fixpunkt configuration section (legacy schema compatibility).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct FixpunktSectionConfig {
    #[serde(default)]
    pub scorer: Option<String>,
    #[serde(default)]
    pub impulses: Vec<String>,
    #[serde(default)]
    pub threshold_range: Vec<f64>,
    #[serde(default)]
    pub threshold_evaluator: Option<String>,
    #[serde(default)]
    pub consensus: Option<String>,
}

/// Root pipeline document containing both sections.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PipelineDocument {
    #[serde(default)]
    pub pipeline: PipelineSectionConfig,
    #[serde(default)]
    pub fixpunkt: FixpunktSectionConfig,
}

impl PipelineDocument {
    /// Load the document from a YAML file.
    pub fn from_path(path: impl AsRef<Path>) -> Result<Self, PipelineError> {
        let content =
            fs::read_to_string(path.as_ref()).map_err(|e| PipelineError::Config(e.to_string()))?;
        serde_yaml::from_str(&content).map_err(|e| PipelineError::Config(e.to_string()))
    }
}

/// Registry for resolving callables from configuration.
#[derive(Default)]
pub struct PipelineRegistry {
    pub generators: HashMap<String, Generator>,
    pub transformers: HashMap<String, Transformer>,
    pub dispatchers: HashMap<String, Dispatcher>,
    pub scorers: HashMap<String, ScoreFn>,
    pub impulses: HashMap<String, ImpulseFn>,
    pub threshold_evaluators: HashMap<String, ThresholdEvaluator>,
    pub consensus: HashMap<String, ConsensusFn>,
}

impl PipelineRegistry {
    /// Pre-populate the registry with useful defaults.
    pub fn with_defaults() -> Self {
        let mut registry = Self::default();
        {
            registry
                .register_generator(
                    "random_vector",
                    Arc::new(|| {
                        let mut rng = rand::thread_rng();
                        let dims = 5;
                        let values: Vec<Value> = (0..dims)
                            .map(|_| Value::from(rng.gen_range(0.0..1.0)))
                            .collect();
                        Value::Array(values)
                    }),
                )
                .register_transformer(
                    "normalize",
                    Arc::new(|payload| match payload {
                        Value::Array(values) => {
                            let sum: f64 = values.iter().filter_map(|v| v.as_f64()).sum();
                            if sum == 0.0 {
                                Value::Array(values)
                            } else {
                                Value::Array(
                                    values
                                        .iter()
                                        .map(|v| {
                                            v.as_f64()
                                                .map(|f| Value::from(f / sum))
                                                .unwrap_or_else(|| v.clone())
                                        })
                                        .collect(),
                                )
                            }
                        }
                        other => other,
                    }),
                )
                .register_dispatcher("echo", Arc::new(|payload, _| Some(payload)))
                .register_scorer("triton_scorer", Arc::new(triton_scorer))
                .register_impulse("default", default_impulse())
                .register_threshold_evaluator("spectral", Arc::new(spectral_threshold_evaluator))
                .register_consensus("mandorla", Arc::new(mandorla_consensus));
        }
        registry
    }

    pub fn register_generator(&mut self, name: impl Into<String>, gen: Generator) -> &mut Self {
        self.generators.insert(name.into(), gen);
        self
    }

    pub fn register_transformer(&mut self, name: impl Into<String>, tr: Transformer) -> &mut Self {
        self.transformers.insert(name.into(), tr);
        self
    }

    pub fn register_dispatcher(&mut self, name: impl Into<String>, disp: Dispatcher) -> &mut Self {
        self.dispatchers.insert(name.into(), disp);
        self
    }

    pub fn register_scorer(&mut self, name: impl Into<String>, scorer: ScoreFn) -> &mut Self {
        self.scorers.insert(name.into(), scorer);
        self
    }

    pub fn register_impulse(&mut self, name: impl Into<String>, impulse: ImpulseFn) -> &mut Self {
        self.impulses.insert(name.into(), impulse);
        self
    }

    pub fn register_threshold_evaluator(
        &mut self,
        name: impl Into<String>,
        evaluator: ThresholdEvaluator,
    ) -> &mut Self {
        self.threshold_evaluators.insert(name.into(), evaluator);
        self
    }

    pub fn register_consensus(
        &mut self,
        name: impl Into<String>,
        consensus: ConsensusFn,
    ) -> &mut Self {
        self.consensus.insert(name.into(), consensus);
        self
    }
}

/// Build an orchestrator from configuration and registry.
pub fn orchestrator_from_config(
    config: &PipelineSectionConfig,
    registry: &PipelineRegistry,
) -> Result<PipelineOrchestrator, PipelineError> {
    let mut orchestrator = PipelineOrchestrator::new();
    for name in &config.generators {
        let gen = registry
            .generators
            .get(name)
            .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))?;
        orchestrator = orchestrator.with_generator(name, gen.clone());
    }
    for name in &config.transformers {
        let tr = registry
            .transformers
            .get(name)
            .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))?;
        orchestrator = orchestrator.with_transformer(name, tr.clone());
    }
    for name in &config.dispatchers {
        let disp = registry
            .dispatchers
            .get(name)
            .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))?;
        orchestrator = orchestrator.with_dispatcher(name, disp.clone());
    }
    Ok(orchestrator)
}

/// Build a Fixpunkt engine using pipeline output as candidate generator.
pub fn fixpunkt_from_config(
    config: &FixpunktSectionConfig,
    registry: &PipelineRegistry,
    mut orchestrator: PipelineOrchestrator,
    proxy_cfg: Option<ProxyConfig>,
) -> Result<FixpunktAttraktorEngine, PipelineError> {
    let scorer = if let Some(name) = &config.scorer {
        registry
            .scorers
            .get(name)
            .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))?
            .clone()
    } else {
        Arc::new(triton_scorer)
    };

    let impulses: Vec<ImpulseFn> = if config.impulses.is_empty() {
        vec![default_impulse()]
    } else {
        config
            .impulses
            .iter()
            .map(|name| {
                registry
                    .impulses
                    .get(name)
                    .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))
                    .cloned()
            })
            .collect::<Result<_, _>>()?
    };

    let threshold_evaluator = if let Some(name) = &config.threshold_evaluator {
        registry
            .threshold_evaluators
            .get(name)
            .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))?
            .clone()
    } else {
        Arc::new(spectral_threshold_evaluator)
    };

    let consensus_fn = if let Some(name) = &config.consensus {
        Some(
            registry
                .consensus
                .get(name)
                .ok_or_else(|| PipelineError::UnknownCallable(name.clone()))?
                .clone(),
        )
    } else {
        None
    };

    let threshold_range = if config.threshold_range.is_empty() {
        vec![0.35, 0.55, 0.85]
    } else {
        config.threshold_range.clone()
    };

    let orchestrator = Arc::new(Mutex::new(orchestrator));
    let generator = Arc::new(move || {
        let mut guard = orchestrator
            .lock()
            .expect("pipeline orchestrator mutex poisoned");
        guard
            .generate_candidates(proxy_cfg.as_ref())
            .into_iter()
            .map(|payload| FixpunktCandidate { payload })
            .collect::<Vec<_>>()
    });

    Ok(FixpunktAttraktorEngine::new(
        generator,
        scorer,
        impulses,
        threshold_evaluator,
        threshold_range,
        consensus_fn,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn orchestrator_runs_pipeline() {
        let registry = PipelineRegistry::with_defaults();
        let config = PipelineSectionConfig {
            generators: vec!["random_vector".into()],
            transformers: vec!["normalize".into()],
            dispatchers: vec!["echo".into()],
        };

        let mut orchestrator = orchestrator_from_config(&config, &registry).unwrap();
        let executions = orchestrator.run(None);
        assert_eq!(executions.len(), 1);
        assert!(!executions[0].stages.is_empty());
    }

    #[test]
    fn fixpunkt_accepts_resonant_candidates() {
        let registry = PipelineRegistry::with_defaults();
        let pipeline_cfg = PipelineSectionConfig {
            generators: vec!["random_vector".into()],
            transformers: vec!["normalize".into()],
            dispatchers: vec!["echo".into()],
        };
        let fixpunkt_cfg = FixpunktSectionConfig {
            threshold_range: vec![0.1, 0.2, 0.3],
            consensus: Some("mandorla".into()),
            ..Default::default()
        };

        let orchestrator = orchestrator_from_config(&pipeline_cfg, &registry).unwrap();
        let engine = fixpunkt_from_config(&fixpunkt_cfg, &registry, orchestrator, None).unwrap();
        let result = engine.run();

        assert_eq!(result.candidates.len(), 1);
        assert!(!result.accepted.is_empty());
    }

    #[test]
    fn spectral_threshold_rejects_divergent_impulses() {
        let candidate = FixpunktCandidate {
            payload: Value::Null,
        };
        let primal = FixpunktState {
            payload: Value::Null,
            score: 0.5,
            impulse: 1.0,
            stage: "p".into(),
        };
        let dual = FixpunktState {
            payload: Value::Null,
            score: 0.5,
            impulse: -1.0,
            stage: "d".into(),
        };
        let pass = spectral_threshold_evaluator(&primal, &dual, &[0.5]);
        let generator_candidate = candidate.clone();
        let impulse_primal = Arc::new(|cand: &FixpunktCandidate, score: f64| FixpunktState {
            payload: cand.payload.clone(),
            score,
            impulse: 1.0,
            stage: "p".into(),
        });
        let impulse_dual = Arc::new(|cand: &FixpunktCandidate, score: f64| FixpunktState {
            payload: cand.payload.clone(),
            score,
            impulse: -1.0,
            stage: "d".into(),
        });
        let engine = FixpunktAttraktorEngine::new(
            Arc::new(move || vec![generator_candidate.clone()]),
            Arc::new(|_| 0.5),
            vec![impulse_primal, impulse_dual],
            Arc::new(spectral_threshold_evaluator),
            vec![0.5],
            None,
        );
        let result = engine.run();
        assert_eq!(pass, false);
        assert!(result.accepted.is_empty());
    }
}
