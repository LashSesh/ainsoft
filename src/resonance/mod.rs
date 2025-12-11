//! Network Resonance Module - Spectral calibration and harmonic analysis.
//!
//! This module provides precision network research tools inspired by the Shaolin principle:
//! minimal, precise actions that blend naturally with the environment.
//!
//! ## Components
//!
//! - **NeedleEmitter**: Precision micro-probes with sub-millisecond timing control
//! - **SpectralAnalyzer**: Frequency-domain analysis of network response patterns
//! - **HarmonicScheduler**: Traffic-blending timing that mimics natural patterns
//! - **ResonanceCalibrator**: Orchestration layer for network resonance research
//!
//! ## Philosophy
//!
//! Unlike brute-force approaches, resonance calibration works through:
//! - **Precision**: Single-packet probes that gather maximum information
//! - **Harmony**: Timing patterns that blend with ambient traffic
//! - **Spectrum**: Analysis in the frequency domain to detect network characteristics
//! - **Resonance**: Finding natural frequencies where networks respond

mod needle;
mod spectral;
mod harmonic;
mod calibrator;

pub use needle::{Needle, NeedleEmitter, NeedleConfig, NeedleType};
pub use spectral::{SpectralAnalyzer, FrequencyBin, SpectrumResult, SpectralConfig};
pub use harmonic::{HarmonicScheduler, HarmonicPattern, TimingSlot, SchedulerConfig};
pub use calibrator::{ResonanceCalibrator, CalibrationResult, CalibratorConfig, ResonanceMode};
