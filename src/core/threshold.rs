//! Adaptive threshold systems for signal gating.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

/// Configuration for threshold behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThresholdConfig {
    /// Initial threshold value
    pub initial: f64,
    /// Minimum allowed threshold
    pub min: f64,
    /// Maximum allowed threshold
    pub max: f64,
    /// Adaptation rate (how quickly threshold adjusts)
    pub adaptation_rate: f64,
    /// Window size for moving statistics
    pub window_size: usize,
}

impl Default for ThresholdConfig {
    fn default() -> Self {
        Self {
            initial: 0.5,
            min: 0.1,
            max: 0.9,
            adaptation_rate: 0.1,
            window_size: 100,
        }
    }
}

/// Basic threshold gate.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Threshold {
    /// Current threshold value
    pub value: f64,
    /// Number of signals that passed
    pub passed: u64,
    /// Number of signals that were blocked
    pub blocked: u64,
}

impl Default for Threshold {
    fn default() -> Self {
        Self {
            value: 0.5,
            passed: 0,
            blocked: 0,
        }
    }
}

impl Threshold {
    /// Create a new threshold with specified value.
    pub fn new(value: f64) -> Self {
        Self {
            value: value.clamp(0.0, 1.0),
            passed: 0,
            blocked: 0,
        }
    }

    /// Check if a signal passes the threshold.
    pub fn check(&mut self, signal: f64) -> bool {
        if signal >= self.value {
            self.passed += 1;
            true
        } else {
            self.blocked += 1;
            false
        }
    }

    /// Get the pass rate.
    pub fn pass_rate(&self) -> f64 {
        let total = self.passed + self.blocked;
        if total == 0 {
            return 0.0;
        }
        self.passed as f64 / total as f64
    }

    /// Reset statistics.
    pub fn reset_stats(&mut self) {
        self.passed = 0;
        self.blocked = 0;
    }

    /// Set a new threshold value.
    pub fn set(&mut self, value: f64) {
        self.value = value.clamp(0.0, 1.0);
    }
}

/// Adaptive threshold that adjusts based on signal history.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdaptiveThreshold {
    /// Current threshold value
    pub value: f64,
    /// Configuration
    config: ThresholdConfig,
    /// Recent signal history
    history: VecDeque<f64>,
    /// Statistics
    pub passed: u64,
    pub blocked: u64,
}

impl Default for AdaptiveThreshold {
    fn default() -> Self {
        Self::with_config(ThresholdConfig::default())
    }
}

impl AdaptiveThreshold {
    /// Create with custom configuration.
    pub fn with_config(config: ThresholdConfig) -> Self {
        Self {
            value: config.initial,
            history: VecDeque::with_capacity(config.window_size),
            passed: 0,
            blocked: 0,
            config,
        }
    }

    /// Check a signal and adapt the threshold.
    pub fn check(&mut self, signal: f64) -> bool {
        // Record signal in history
        if self.history.len() >= self.config.window_size {
            self.history.pop_front();
        }
        self.history.push_back(signal);

        // Check against current threshold
        let passed = signal >= self.value;
        if passed {
            self.passed += 1;
        } else {
            self.blocked += 1;
        }

        // Adapt threshold
        self.adapt();

        passed
    }

    /// Adapt the threshold based on recent history.
    fn adapt(&mut self) {
        if self.history.is_empty() {
            return;
        }

        // Calculate statistics from history
        let mean = self.history.iter().sum::<f64>() / self.history.len() as f64;
        let variance = if self.history.len() > 1 {
            self.history
                .iter()
                .map(|x| (x - mean).powi(2))
                .sum::<f64>()
                / (self.history.len() - 1) as f64
        } else {
            0.0
        };
        let std_dev = variance.sqrt();

        // New threshold = mean + k * std_dev (adjustable sensitivity)
        let target = mean + 0.5 * std_dev;

        // Smooth adaptation towards target
        self.value = self.value * (1.0 - self.config.adaptation_rate)
            + target * self.config.adaptation_rate;

        // Clamp to bounds
        self.value = self.value.clamp(self.config.min, self.config.max);
    }

    /// Get the current pass rate.
    pub fn pass_rate(&self) -> f64 {
        let total = self.passed + self.blocked;
        if total == 0 {
            return 0.0;
        }
        self.passed as f64 / total as f64
    }

    /// Get the mean of recent signals.
    pub fn mean(&self) -> f64 {
        if self.history.is_empty() {
            return 0.0;
        }
        self.history.iter().sum::<f64>() / self.history.len() as f64
    }

    /// Get the standard deviation of recent signals.
    pub fn std_dev(&self) -> f64 {
        if self.history.len() < 2 {
            return 0.0;
        }
        let mean = self.mean();
        let variance = self
            .history
            .iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>()
            / (self.history.len() - 1) as f64;
        variance.sqrt()
    }

    /// Reset the adaptive threshold.
    pub fn reset(&mut self) {
        self.value = self.config.initial;
        self.history.clear();
        self.passed = 0;
        self.blocked = 0;
    }

    /// Force set the threshold value.
    pub fn set(&mut self, value: f64) {
        self.value = value.clamp(self.config.min, self.config.max);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_threshold_check() {
        let mut th = Threshold::new(0.5);
        assert!(th.check(0.6));
        assert!(!th.check(0.4));
        assert_eq!(th.passed, 1);
        assert_eq!(th.blocked, 1);
    }

    #[test]
    fn test_adaptive_threshold() {
        let mut ath = AdaptiveThreshold::default();

        // Feed high signals
        for _ in 0..50 {
            ath.check(0.8);
        }

        // Threshold should adapt upward
        assert!(ath.value > 0.5);
    }

    #[test]
    fn test_adaptive_bounds() {
        let config = ThresholdConfig {
            min: 0.3,
            max: 0.7,
            ..Default::default()
        };
        let mut ath = AdaptiveThreshold::with_config(config);

        // Feed very high signals
        for _ in 0..100 {
            ath.check(1.0);
        }

        // Should be clamped to max
        assert!(ath.value <= 0.7);
    }
}
