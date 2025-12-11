//! Tripolar resonance logic.
//!
//! The oscillator aggregates numeric signals and normalizes the result
//! into a bounded resonance score.

use serde::{Deserialize, Serialize};

/// Compute resonance values from numeric signals.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Oscillator {
    /// Last computed resonance state
    pub last_state: f64,
    /// History of computed values (bounded)
    history: Vec<f64>,
    /// Maximum history size
    max_history: usize,
}

impl Oscillator {
    /// Create a new oscillator with specified history capacity.
    pub fn new(max_history: usize) -> Self {
        Self {
            last_state: 0.0,
            history: Vec::with_capacity(max_history),
            max_history,
        }
    }

    /// Compute a resonance score between 0.0 and 1.0 from input signals.
    pub fn compute<I>(&mut self, signals: I) -> f64
    where
        I: IntoIterator<Item = f64>,
    {
        let values: Vec<f64> = signals.into_iter().collect();

        if values.is_empty() {
            self.last_state = 0.0;
            return 0.0;
        }

        let mean = values.iter().sum::<f64>() / values.len() as f64;
        let score = mean.clamp(0.0, 1.0);

        self.last_state = score;
        self.record(score);

        score
    }

    /// Compute resonance with weighted signals.
    pub fn compute_weighted<I>(&mut self, signals: I) -> f64
    where
        I: IntoIterator<Item = (f64, f64)>,
    {
        let pairs: Vec<(f64, f64)> = signals.into_iter().collect();

        if pairs.is_empty() {
            self.last_state = 0.0;
            return 0.0;
        }

        let total_weight: f64 = pairs.iter().map(|(_, w)| w).sum();
        if total_weight <= 0.0 {
            self.last_state = 0.0;
            return 0.0;
        }

        let weighted_sum: f64 = pairs.iter().map(|(v, w)| v * w).sum();
        let score = (weighted_sum / total_weight).clamp(0.0, 1.0);

        self.last_state = score;
        self.record(score);

        score
    }

    /// Record a value in history.
    fn record(&mut self, value: f64) {
        if self.history.len() >= self.max_history {
            self.history.remove(0);
        }
        self.history.push(value);
    }

    /// Get the moving average of recent values.
    pub fn moving_average(&self) -> f64 {
        if self.history.is_empty() {
            return 0.0;
        }
        self.history.iter().sum::<f64>() / self.history.len() as f64
    }

    /// Get variance of recent values.
    pub fn variance(&self) -> f64 {
        if self.history.len() < 2 {
            return 0.0;
        }

        let mean = self.moving_average();
        let sum_sq_diff: f64 = self.history.iter().map(|x| (x - mean).powi(2)).sum();
        sum_sq_diff / (self.history.len() - 1) as f64
    }

    /// Reset the oscillator state.
    pub fn reset(&mut self) {
        self.last_state = 0.0;
        self.history.clear();
    }

    /// Get history length.
    pub fn history_len(&self) -> usize {
        self.history.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_empty() {
        let mut osc = Oscillator::new(10);
        assert_eq!(osc.compute(std::iter::empty()), 0.0);
    }

    #[test]
    fn test_compute_single() {
        let mut osc = Oscillator::new(10);
        assert_eq!(osc.compute([0.5]), 0.5);
    }

    #[test]
    fn test_compute_multiple() {
        let mut osc = Oscillator::new(10);
        let result = osc.compute([0.2, 0.4, 0.6]);
        assert!((result - 0.4).abs() < 1e-9);
    }

    #[test]
    fn test_clamping() {
        let mut osc = Oscillator::new(10);
        assert_eq!(osc.compute([1.5, 2.0]), 1.0);
        assert_eq!(osc.compute([-0.5, -1.0]), 0.0);
    }
}
