//! Resonance calibrator - orchestration layer for network resonance research.
//!
//! The calibrator coordinates needle emission, harmonic scheduling, and spectral
//! analysis to perform comprehensive network resonance research.

use super::{
    HarmonicPattern, HarmonicScheduler, Needle, NeedleConfig, NeedleEmitter, NeedleType,
    SchedulerConfig, SpectralAnalyzer, SpectralConfig, SpectrumResult, TimingSlot,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// Resonance research mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ResonanceMode {
    /// Passive observation - minimal footprint
    #[default]
    Observe,
    /// Active calibration - find resonance points
    Calibrate,
    /// Mapping - build network topology model
    Map,
    /// Spectrum sweep - full frequency analysis
    Sweep,
    /// Adaptive - auto-adjust based on responses
    Adaptive,
}

impl ResonanceMode {
    /// Get recommended needle type for this mode.
    pub fn recommended_needle(&self) -> NeedleType {
        match self {
            ResonanceMode::Observe => NeedleType::Whisper,
            ResonanceMode::Calibrate => NeedleType::Touch,
            ResonanceMode::Map => NeedleType::Pulse,
            ResonanceMode::Sweep => NeedleType::Echo,
            ResonanceMode::Adaptive => NeedleType::Whisper,
        }
    }

    /// Get recommended harmonic pattern for this mode.
    pub fn recommended_pattern(&self) -> HarmonicPattern {
        match self {
            ResonanceMode::Observe => HarmonicPattern::Poisson,
            ResonanceMode::Calibrate => HarmonicPattern::Fibonacci,
            ResonanceMode::Map => HarmonicPattern::MultiModal,
            ResonanceMode::Sweep => HarmonicPattern::PinkNoise,
            ResonanceMode::Adaptive => HarmonicPattern::Brownian,
        }
    }
}

/// Configuration for resonance calibration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibratorConfig {
    /// Research mode
    pub mode: ResonanceMode,
    /// Needle configuration
    pub needle: NeedleConfig,
    /// Scheduler configuration
    pub scheduler: SchedulerConfig,
    /// Spectral analysis configuration
    pub spectral: SpectralConfig,
    /// Maximum probes per session
    pub max_probes: u64,
    /// Session timeout (seconds)
    pub session_timeout: f64,
    /// Enable auto-tuning based on responses
    pub auto_tune: bool,
    /// Resonance detection sensitivity (0.0 - 1.0)
    pub sensitivity: f64,
}

impl Default for CalibratorConfig {
    fn default() -> Self {
        let mode = ResonanceMode::Observe;
        Self {
            mode,
            needle: NeedleConfig {
                needle_type: mode.recommended_needle(),
                ..Default::default()
            },
            scheduler: SchedulerConfig {
                pattern: mode.recommended_pattern(),
                ..Default::default()
            },
            spectral: SpectralConfig::default(),
            max_probes: 1000,
            session_timeout: 300.0, // 5 minutes
            auto_tune: true,
            sensitivity: 0.5,
        }
    }
}

impl CalibratorConfig {
    /// Create config for a specific mode with defaults.
    pub fn for_mode(mode: ResonanceMode) -> Self {
        Self {
            mode,
            needle: NeedleConfig {
                needle_type: mode.recommended_needle(),
                ..Default::default()
            },
            scheduler: SchedulerConfig {
                pattern: mode.recommended_pattern(),
                ..Default::default()
            },
            ..Default::default()
        }
    }
}

/// Result of resonance calibration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibrationResult {
    /// Mode used
    pub mode: ResonanceMode,
    /// Target endpoints
    pub targets: Vec<String>,
    /// Total probes sent
    pub probes_sent: u64,
    /// Probes returned
    pub probes_returned: u64,
    /// Session duration (seconds)
    pub duration: f64,
    /// Mean latency (ms)
    pub mean_latency_ms: f64,
    /// Latency standard deviation
    pub latency_std_ms: f64,
    /// Detected resonance frequencies
    pub resonance_frequencies: Vec<f64>,
    /// Per-target statistics
    pub target_stats: HashMap<String, TargetStats>,
    /// Spectral analysis results
    pub spectrum: Option<SpectrumResult>,
    /// Auto-tuning adjustments made
    pub auto_tune_adjustments: Vec<String>,
}

/// Per-target statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TargetStats {
    pub probes: u64,
    pub returns: u64,
    pub mean_latency_ms: f64,
    pub min_latency_ms: f64,
    pub max_latency_ms: f64,
    pub jitter_ms: f64,
}

/// State of the calibration session.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionState {
    Idle,
    Running,
    Paused,
    Completed,
    Timeout,
}

/// Resonance calibrator - main orchestration component.
pub struct ResonanceCalibrator {
    config: CalibratorConfig,
    emitter: NeedleEmitter,
    scheduler: HarmonicScheduler,
    analyzer: SpectralAnalyzer,
    state: SessionState,
    start_time: Option<Instant>,
    pending_slots: Vec<TimingSlot>,
    target_latencies: HashMap<String, Vec<f64>>,
    auto_tune_log: Vec<String>,
}

impl Default for ResonanceCalibrator {
    fn default() -> Self {
        Self::new(CalibratorConfig::default())
    }
}

impl ResonanceCalibrator {
    /// Create a new resonance calibrator.
    pub fn new(config: CalibratorConfig) -> Self {
        Self {
            emitter: NeedleEmitter::new(config.needle.clone()),
            scheduler: HarmonicScheduler::new(config.scheduler.clone()),
            analyzer: SpectralAnalyzer::new(config.spectral.clone()),
            state: SessionState::Idle,
            start_time: None,
            pending_slots: Vec::new(),
            target_latencies: HashMap::new(),
            auto_tune_log: Vec::new(),
            config,
        }
    }

    /// Create calibrator for a specific mode.
    pub fn for_mode(mode: ResonanceMode) -> Self {
        Self::new(CalibratorConfig::for_mode(mode))
    }

    /// Add a target endpoint.
    pub fn add_target(&mut self, target: impl Into<String>) {
        let target = target.into();
        self.emitter.add_target(&target);
        self.target_latencies.insert(target, Vec::new());
    }

    /// Add multiple targets.
    pub fn add_targets<I, S>(&mut self, targets: I)
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        for target in targets {
            self.add_target(target);
        }
    }

    /// Start a calibration session.
    pub fn start(&mut self) {
        self.state = SessionState::Running;
        self.start_time = Some(Instant::now());

        // Pre-generate timing slots
        let initial_slots = (self.config.max_probes / 10).max(10) as usize;
        self.pending_slots = self.scheduler.generate_slots(initial_slots);
    }

    /// Pause the session.
    pub fn pause(&mut self) {
        if self.state == SessionState::Running {
            self.state = SessionState::Paused;
        }
    }

    /// Resume the session.
    pub fn resume(&mut self) {
        if self.state == SessionState::Paused {
            self.state = SessionState::Running;
        }
    }

    /// Get current session state.
    pub fn state(&self) -> SessionState {
        self.state
    }

    /// Check if session should continue.
    pub fn should_continue(&self) -> bool {
        if self.state != SessionState::Running {
            return false;
        }

        if self.emitter.stats().total_emitted >= self.config.max_probes {
            return false;
        }

        if let Some(start) = self.start_time {
            if start.elapsed().as_secs_f64() >= self.config.session_timeout {
                return false;
            }
        }

        true
    }

    /// Get the next timing slot.
    pub fn next_slot(&mut self) -> Option<TimingSlot> {
        if self.pending_slots.is_empty() {
            self.pending_slots = self.scheduler.generate_slots(10);
        }
        self.pending_slots.pop()
    }

    /// Get delay until next probe.
    pub fn next_delay(&mut self) -> Duration {
        if let Some(slot) = self.next_slot() {
            Duration::from_secs_f64(slot.delay)
        } else {
            Duration::from_millis(100)
        }
    }

    /// Emit a needle according to schedule.
    pub fn emit(&mut self) -> Option<Needle> {
        if !self.should_continue() {
            return None;
        }

        let slot = self.pending_slots.pop().or_else(|| {
            self.pending_slots = self.scheduler.generate_slots(10);
            self.pending_slots.pop()
        })?;

        self.emitter.emit_next(slot.harmonic_idx as u32, slot.phase)
    }

    /// Record a needle return.
    pub fn record_return(&mut self, needle_id: u64, target: &str, latency_ms: f64) {
        self.emitter.record_return(needle_id);

        // Record for per-target stats
        self.target_latencies
            .entry(target.to_string())
            .or_default()
            .push(latency_ms);

        // Feed to spectral analyzer
        let timestamp = self.start_time
            .map(|s| s.elapsed().as_secs_f64())
            .unwrap_or(0.0);
        self.analyzer.add_sample(latency_ms, timestamp);

        // Auto-tune if enabled
        if self.config.auto_tune {
            self.maybe_auto_tune(latency_ms);
        }
    }

    /// Auto-tune based on response characteristics.
    fn maybe_auto_tune(&mut self, latency_ms: f64) {
        let stats = self.emitter.stats();

        // If return rate drops, increase intervals
        if stats.total_emitted > 50 && stats.return_rate < 0.9 {
            self.scheduler.config.mean_interval *= 1.1;
            self.auto_tune_log.push(format!(
                "Increased interval to {:.2}s (return rate: {:.1}%)",
                self.scheduler.config.mean_interval,
                stats.return_rate * 100.0
            ));
        }

        // If latency is very stable, can probe faster
        if stats.total_returned > 20 && stats.std_dev_ms < 5.0 && stats.return_rate > 0.95 {
            self.scheduler.config.mean_interval *= 0.9;
            self.auto_tune_log.push(format!(
                "Decreased interval to {:.2}s (stable latency: {:.1}ms ± {:.1}ms)",
                self.scheduler.config.mean_interval,
                stats.mean_rtt_ms,
                stats.std_dev_ms
            ));
        }

        // Clamp to bounds
        self.scheduler.config.mean_interval = self.scheduler.config.mean_interval
            .clamp(self.scheduler.config.min_interval, self.scheduler.config.max_interval);
    }

    /// Run spectral analysis on collected data.
    pub fn analyze_spectrum(&mut self) -> Option<SpectrumResult> {
        self.analyzer.analyze()
    }

    /// Complete the session and get results.
    pub fn complete(&mut self) -> CalibrationResult {
        self.state = SessionState::Completed;

        let emitter_stats = self.emitter.stats();
        let duration = self.start_time
            .map(|s| s.elapsed().as_secs_f64())
            .unwrap_or(0.0);

        // Compute per-target stats
        let mut target_stats = HashMap::new();
        for (target, latencies) in &self.target_latencies {
            if latencies.is_empty() {
                continue;
            }

            let mean = latencies.iter().sum::<f64>() / latencies.len() as f64;
            let min = latencies.iter().cloned().fold(f64::INFINITY, f64::min);
            let max = latencies.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

            let variance = if latencies.len() > 1 {
                latencies.iter()
                    .map(|l| (l - mean).powi(2))
                    .sum::<f64>() / (latencies.len() - 1) as f64
            } else {
                0.0
            };

            target_stats.insert(target.clone(), TargetStats {
                probes: latencies.len() as u64,
                returns: latencies.len() as u64, // Only returned ones are recorded
                mean_latency_ms: mean,
                min_latency_ms: min,
                max_latency_ms: max,
                jitter_ms: variance.sqrt(),
            });
        }

        // Get final spectrum
        let spectrum = self.analyze_spectrum();

        // Extract resonance frequencies
        let resonance_frequencies = spectrum
            .as_ref()
            .map(|s| s.resonance_points.iter().map(|r| r.frequency).collect())
            .unwrap_or_default();

        CalibrationResult {
            mode: self.config.mode,
            targets: self.target_latencies.keys().cloned().collect(),
            probes_sent: emitter_stats.total_emitted,
            probes_returned: emitter_stats.total_returned,
            duration,
            mean_latency_ms: emitter_stats.mean_rtt_ms,
            latency_std_ms: emitter_stats.std_dev_ms,
            resonance_frequencies,
            target_stats,
            spectrum,
            auto_tune_adjustments: self.auto_tune_log.clone(),
        }
    }

    /// Reset for a new session.
    pub fn reset(&mut self) {
        self.emitter.reset();
        self.scheduler.reset();
        self.analyzer.reset();
        self.state = SessionState::Idle;
        self.start_time = None;
        self.pending_slots.clear();
        self.target_latencies.clear();
        self.auto_tune_log.clear();
    }

    /// Get current statistics.
    pub fn current_stats(&self) -> CalibratorStats {
        let emitter_stats = self.emitter.stats();
        let elapsed = self.start_time
            .map(|s| s.elapsed().as_secs_f64())
            .unwrap_or(0.0);

        CalibratorStats {
            state: self.state,
            elapsed_secs: elapsed,
            probes_sent: emitter_stats.total_emitted,
            probes_returned: emitter_stats.total_returned,
            probes_lost: emitter_stats.total_lost,
            mean_latency_ms: emitter_stats.mean_rtt_ms,
            return_rate: emitter_stats.return_rate,
            spectral_analyses: self.analyzer.analysis_count(),
        }
    }
}

/// Current calibrator statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CalibratorStats {
    pub state: SessionState,
    pub elapsed_secs: f64,
    pub probes_sent: u64,
    pub probes_returned: u64,
    pub probes_lost: u64,
    pub mean_latency_ms: f64,
    pub return_rate: f64,
    pub spectral_analyses: u64,
}

// Implement Serialize/Deserialize for SessionState
impl Serialize for SessionState {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        let s = match self {
            SessionState::Idle => "idle",
            SessionState::Running => "running",
            SessionState::Paused => "paused",
            SessionState::Completed => "completed",
            SessionState::Timeout => "timeout",
        };
        serializer.serialize_str(s)
    }
}

impl<'de> Deserialize<'de> for SessionState {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let s = String::deserialize(deserializer)?;
        match s.as_str() {
            "idle" => Ok(SessionState::Idle),
            "running" => Ok(SessionState::Running),
            "paused" => Ok(SessionState::Paused),
            "completed" => Ok(SessionState::Completed),
            "timeout" => Ok(SessionState::Timeout),
            _ => Err(serde::de::Error::unknown_variant(&s, &["idle", "running", "paused", "completed", "timeout"])),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calibrator_creation() {
        let calibrator = ResonanceCalibrator::default();
        assert_eq!(calibrator.state(), SessionState::Idle);
    }

    #[test]
    fn test_mode_recommendations() {
        assert_eq!(ResonanceMode::Observe.recommended_needle(), NeedleType::Whisper);
        assert_eq!(ResonanceMode::Sweep.recommended_pattern(), HarmonicPattern::PinkNoise);
    }

    #[test]
    fn test_session_lifecycle() {
        let mut calibrator = ResonanceCalibrator::for_mode(ResonanceMode::Observe);
        calibrator.add_target("localhost");

        assert_eq!(calibrator.state(), SessionState::Idle);

        calibrator.start();
        assert_eq!(calibrator.state(), SessionState::Running);

        calibrator.pause();
        assert_eq!(calibrator.state(), SessionState::Paused);

        calibrator.resume();
        assert_eq!(calibrator.state(), SessionState::Running);

        let result = calibrator.complete();
        assert_eq!(result.mode, ResonanceMode::Observe);
    }

    #[test]
    fn test_config_for_mode() {
        let config = CalibratorConfig::for_mode(ResonanceMode::Calibrate);
        assert_eq!(config.mode, ResonanceMode::Calibrate);
        assert_eq!(config.needle.needle_type, NeedleType::Touch);
        assert_eq!(config.scheduler.pattern, HarmonicPattern::Fibonacci);
    }
}
