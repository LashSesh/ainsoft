//! Spectral analysis for network resonance patterns.
//!
//! Analyzes network response patterns in the frequency domain to detect
//! characteristic signatures, periodic behaviors, and resonance points.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::f64::consts::PI;

/// Configuration for spectral analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpectralConfig {
    /// Number of samples for FFT (should be power of 2)
    pub window_size: usize,
    /// Overlap between windows (0.0 - 1.0)
    pub overlap: f64,
    /// Minimum frequency of interest (Hz)
    pub min_freq_hz: f64,
    /// Maximum frequency of interest (Hz)
    pub max_freq_hz: f64,
    /// Threshold for peak detection (relative to mean)
    pub peak_threshold: f64,
    /// Smoothing factor for spectrum averaging
    pub smoothing: f64,
}

impl Default for SpectralConfig {
    fn default() -> Self {
        Self {
            window_size: 256,
            overlap: 0.5,
            min_freq_hz: 0.1,
            max_freq_hz: 50.0,
            peak_threshold: 2.0,
            smoothing: 0.3,
        }
    }
}

/// A frequency bin in the spectrum.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FrequencyBin {
    /// Center frequency (Hz)
    pub frequency: f64,
    /// Magnitude (power)
    pub magnitude: f64,
    /// Phase (radians)
    pub phase: f64,
    /// Whether this bin represents a peak
    pub is_peak: bool,
}

/// Result of spectral analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpectrumResult {
    /// Frequency bins
    pub bins: Vec<FrequencyBin>,
    /// Dominant frequency (Hz)
    pub dominant_freq: f64,
    /// Total spectral energy
    pub total_energy: f64,
    /// Spectral centroid (center of mass)
    pub centroid: f64,
    /// Spectral spread (bandwidth)
    pub spread: f64,
    /// Detected resonance points
    pub resonance_points: Vec<ResonancePoint>,
    /// Sample rate used for analysis
    pub sample_rate: f64,
}

/// A detected resonance point in the spectrum.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResonancePoint {
    /// Resonance frequency (Hz)
    pub frequency: f64,
    /// Quality factor (sharpness of resonance)
    pub q_factor: f64,
    /// Amplitude at resonance
    pub amplitude: f64,
    /// Bandwidth (-3dB points)
    pub bandwidth: f64,
}

/// Spectral analyzer for network latency patterns.
#[derive(Debug)]
pub struct SpectralAnalyzer {
    config: SpectralConfig,
    sample_buffer: VecDeque<f64>,
    timestamp_buffer: VecDeque<f64>,
    averaged_spectrum: Vec<f64>,
    analysis_count: u64,
}

impl Default for SpectralAnalyzer {
    fn default() -> Self {
        Self::new(SpectralConfig::default())
    }
}

impl SpectralAnalyzer {
    /// Create a new spectral analyzer.
    pub fn new(config: SpectralConfig) -> Self {
        Self {
            sample_buffer: VecDeque::with_capacity(config.window_size * 2),
            timestamp_buffer: VecDeque::with_capacity(config.window_size * 2),
            averaged_spectrum: vec![0.0; config.window_size / 2],
            analysis_count: 0,
            config,
        }
    }

    /// Add a latency sample with timestamp.
    pub fn add_sample(&mut self, latency_ms: f64, timestamp: f64) {
        self.sample_buffer.push_back(latency_ms);
        self.timestamp_buffer.push_back(timestamp);

        // Keep buffer bounded
        while self.sample_buffer.len() > self.config.window_size * 2 {
            self.sample_buffer.pop_front();
            self.timestamp_buffer.pop_front();
        }
    }

    /// Check if enough samples for analysis.
    pub fn can_analyze(&self) -> bool {
        self.sample_buffer.len() >= self.config.window_size
    }

    /// Estimate sample rate from timestamps.
    fn estimate_sample_rate(&self) -> f64 {
        if self.timestamp_buffer.len() < 2 {
            return 10.0; // Default 10 Hz
        }

        let first = *self.timestamp_buffer.front().unwrap();
        let last = *self.timestamp_buffer.back().unwrap();
        let duration = last - first;

        if duration > 0.0 {
            (self.timestamp_buffer.len() - 1) as f64 / duration
        } else {
            10.0
        }
    }

    /// Perform spectral analysis on current buffer.
    pub fn analyze(&mut self) -> Option<SpectrumResult> {
        if !self.can_analyze() {
            return None;
        }

        let sample_rate = self.estimate_sample_rate();
        let samples: Vec<f64> = self.sample_buffer
            .iter()
            .take(self.config.window_size)
            .cloned()
            .collect();

        // Apply Hann window
        let windowed = self.apply_window(&samples);

        // Compute DFT (simplified for research purposes)
        let spectrum = self.compute_dft(&windowed);

        // Extract magnitude and phase
        let mut bins = Vec::new();
        let freq_resolution = sample_rate / self.config.window_size as f64;

        for (i, &(re, im)) in spectrum.iter().enumerate().take(self.config.window_size / 2) {
            let freq = i as f64 * freq_resolution;
            let magnitude = (re * re + im * im).sqrt();
            let phase = im.atan2(re);

            bins.push(FrequencyBin {
                frequency: freq,
                magnitude,
                phase,
                is_peak: false,
            });
        }

        // Update averaged spectrum with smoothing
        for (i, bin) in bins.iter().enumerate() {
            if i < self.averaged_spectrum.len() {
                self.averaged_spectrum[i] = self.config.smoothing * bin.magnitude
                    + (1.0 - self.config.smoothing) * self.averaged_spectrum[i];
            }
        }

        // Detect peaks
        self.detect_peaks(&mut bins);

        // Calculate spectral features
        let total_energy: f64 = bins.iter().map(|b| b.magnitude * b.magnitude).sum();

        let dominant_freq = bins
            .iter()
            .filter(|b| b.frequency >= self.config.min_freq_hz && b.frequency <= self.config.max_freq_hz)
            .max_by(|a, b| a.magnitude.partial_cmp(&b.magnitude).unwrap())
            .map(|b| b.frequency)
            .unwrap_or(0.0);

        let centroid = self.compute_centroid(&bins);
        let spread = self.compute_spread(&bins, centroid);

        // Detect resonance points
        let resonance_points = self.detect_resonance(&bins);

        self.analysis_count += 1;

        // Advance buffer by hop size
        let hop_size = ((1.0 - self.config.overlap) * self.config.window_size as f64) as usize;
        for _ in 0..hop_size.min(self.sample_buffer.len()) {
            self.sample_buffer.pop_front();
            self.timestamp_buffer.pop_front();
        }

        Some(SpectrumResult {
            bins,
            dominant_freq,
            total_energy,
            centroid,
            spread,
            resonance_points,
            sample_rate,
        })
    }

    /// Apply Hann window to samples.
    fn apply_window(&self, samples: &[f64]) -> Vec<f64> {
        samples
            .iter()
            .enumerate()
            .map(|(i, &s)| {
                let w = 0.5 * (1.0 - (2.0 * PI * i as f64 / (samples.len() - 1) as f64).cos());
                s * w
            })
            .collect()
    }

    /// Compute DFT (returns complex pairs).
    fn compute_dft(&self, samples: &[f64]) -> Vec<(f64, f64)> {
        let n = samples.len();
        let mut result = Vec::with_capacity(n);

        for k in 0..n {
            let mut re = 0.0;
            let mut im = 0.0;

            for (i, &sample) in samples.iter().enumerate() {
                let angle = -2.0 * PI * k as f64 * i as f64 / n as f64;
                re += sample * angle.cos();
                im += sample * angle.sin();
            }

            result.push((re / n as f64, im / n as f64));
        }

        result
    }

    /// Detect peaks in the spectrum.
    fn detect_peaks(&self, bins: &mut [FrequencyBin]) {
        if bins.len() < 3 {
            return;
        }

        let mean_mag: f64 = bins.iter().map(|b| b.magnitude).sum::<f64>() / bins.len() as f64;
        let threshold = mean_mag * self.config.peak_threshold;

        for i in 1..bins.len() - 1 {
            let is_local_max = bins[i].magnitude > bins[i - 1].magnitude
                && bins[i].magnitude > bins[i + 1].magnitude;
            let above_threshold = bins[i].magnitude > threshold;
            let in_range = bins[i].frequency >= self.config.min_freq_hz
                && bins[i].frequency <= self.config.max_freq_hz;

            bins[i].is_peak = is_local_max && above_threshold && in_range;
        }
    }

    /// Compute spectral centroid.
    fn compute_centroid(&self, bins: &[FrequencyBin]) -> f64 {
        let total_mag: f64 = bins.iter().map(|b| b.magnitude).sum();
        if total_mag == 0.0 {
            return 0.0;
        }

        bins.iter()
            .map(|b| b.frequency * b.magnitude)
            .sum::<f64>()
            / total_mag
    }

    /// Compute spectral spread.
    fn compute_spread(&self, bins: &[FrequencyBin], centroid: f64) -> f64 {
        let total_mag: f64 = bins.iter().map(|b| b.magnitude).sum();
        if total_mag == 0.0 {
            return 0.0;
        }

        let variance: f64 = bins
            .iter()
            .map(|b| (b.frequency - centroid).powi(2) * b.magnitude)
            .sum::<f64>()
            / total_mag;

        variance.sqrt()
    }

    /// Detect resonance points from peaks.
    fn detect_resonance(&self, bins: &[FrequencyBin]) -> Vec<ResonancePoint> {
        let peaks: Vec<&FrequencyBin> = bins.iter().filter(|b| b.is_peak).collect();
        let mut resonances = Vec::new();

        for peak in peaks {
            // Find -3dB bandwidth
            let half_power = peak.magnitude / 2.0_f64.sqrt();

            let mut lower_idx = bins
                .iter()
                .position(|b| b.frequency == peak.frequency)
                .unwrap_or(0);
            let mut upper_idx = lower_idx;

            // Find lower -3dB point
            while lower_idx > 0 && bins[lower_idx].magnitude > half_power {
                lower_idx -= 1;
            }

            // Find upper -3dB point
            while upper_idx < bins.len() - 1 && bins[upper_idx].magnitude > half_power {
                upper_idx += 1;
            }

            let lower_freq = bins[lower_idx].frequency;
            let upper_freq = bins[upper_idx].frequency;
            let bandwidth = upper_freq - lower_freq;

            let q_factor = if bandwidth > 0.0 {
                peak.frequency / bandwidth
            } else {
                0.0
            };

            resonances.push(ResonancePoint {
                frequency: peak.frequency,
                q_factor,
                amplitude: peak.magnitude,
                bandwidth,
            });
        }

        resonances
    }

    /// Get the averaged spectrum.
    pub fn averaged_spectrum(&self) -> &[f64] {
        &self.averaged_spectrum
    }

    /// Get analysis count.
    pub fn analysis_count(&self) -> u64 {
        self.analysis_count
    }

    /// Reset the analyzer.
    pub fn reset(&mut self) {
        self.sample_buffer.clear();
        self.timestamp_buffer.clear();
        self.averaged_spectrum.fill(0.0);
        self.analysis_count = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_spectral_config_default() {
        let config = SpectralConfig::default();
        assert_eq!(config.window_size, 256);
        assert!(config.overlap > 0.0 && config.overlap < 1.0);
    }

    #[test]
    fn test_analyzer_needs_samples() {
        let analyzer = SpectralAnalyzer::default();
        assert!(!analyzer.can_analyze());
    }

    #[test]
    fn test_analyzer_with_samples() {
        let mut analyzer = SpectralAnalyzer::new(SpectralConfig {
            window_size: 32,
            ..Default::default()
        });

        // Add synthetic samples with periodic pattern
        for i in 0..64 {
            let t = i as f64 * 0.1;
            let value = 10.0 + 5.0 * (2.0 * PI * 1.0 * t).sin(); // 1 Hz sine
            analyzer.add_sample(value, t);
        }

        assert!(analyzer.can_analyze());

        let result = analyzer.analyze().unwrap();
        assert!(!result.bins.is_empty());
        assert!(result.total_energy > 0.0);
    }

    #[test]
    fn test_window_function() {
        let analyzer = SpectralAnalyzer::default();
        let samples = vec![1.0; 8];
        let windowed = analyzer.apply_window(&samples);

        // Hann window should taper at edges
        assert!(windowed[0] < windowed[4]);
        assert!(windowed[7] < windowed[4]);
    }
}
