//! Signal analysis with adaptive thresholds.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

use super::{ResponseObserver, ResponseStatus};
use crate::core::AdaptiveThreshold;

/// Metrics from signal analysis.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SignalMetrics {
    /// Number of samples analyzed
    pub samples: usize,
    /// Mean value
    pub mean: f64,
    /// Standard deviation
    pub std_dev: f64,
    /// Minimum value
    pub min: f64,
    /// Maximum value
    pub max: f64,
    /// Current threshold
    pub threshold: f64,
    /// Pass rate (above threshold)
    pub pass_rate: f64,
    /// Anomaly count
    pub anomalies: usize,
}

/// Signal analyzer with adaptive threshold.
#[derive(Debug, Clone)]
pub struct SignalAnalyzer {
    /// Adaptive threshold
    threshold: AdaptiveThreshold,
    /// Recent signal values
    values: VecDeque<f64>,
    /// Maximum history size
    max_history: usize,
    /// Anomaly threshold (std devs from mean)
    anomaly_threshold: f64,
    /// Detected anomalies
    anomalies: Vec<AnomalyRecord>,
    /// Maximum anomaly records
    max_anomalies: usize,
}

/// Record of a detected anomaly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnomalyRecord {
    /// Anomalous value
    pub value: f64,
    /// Expected range (mean - std, mean + std)
    pub expected_range: (f64, f64),
    /// Z-score (deviation from mean)
    pub z_score: f64,
    /// Timestamp
    pub timestamp: f64,
}

impl Default for SignalAnalyzer {
    fn default() -> Self {
        Self::new(1000, 2.0)
    }
}

impl SignalAnalyzer {
    /// Create a new analyzer.
    pub fn new(max_history: usize, anomaly_threshold: f64) -> Self {
        Self {
            threshold: AdaptiveThreshold::default(),
            values: VecDeque::with_capacity(max_history),
            max_history,
            anomaly_threshold,
            anomalies: Vec::new(),
            max_anomalies: 100,
        }
    }

    /// Process a signal value.
    pub fn process(&mut self, value: f64) -> bool {
        // Record value
        if self.values.len() >= self.max_history {
            self.values.pop_front();
        }
        self.values.push_back(value);

        // Check against threshold
        let passed = self.threshold.check(value);

        // Check for anomaly
        if let Some(anomaly) = self.detect_anomaly(value) {
            if self.anomalies.len() >= self.max_anomalies {
                self.anomalies.remove(0);
            }
            self.anomalies.push(anomaly);
        }

        passed
    }

    /// Detect if a value is anomalous.
    fn detect_anomaly(&self, value: f64) -> Option<AnomalyRecord> {
        if self.values.len() < 10 {
            return None;
        }

        let mean = self.mean();
        let std_dev = self.std_dev();

        if std_dev < 1e-9 {
            return None;
        }

        let z_score = (value - mean) / std_dev;

        if z_score.abs() > self.anomaly_threshold {
            Some(AnomalyRecord {
                value,
                expected_range: (mean - std_dev, mean + std_dev),
                z_score,
                timestamp: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs_f64())
                    .unwrap_or(0.0),
            })
        } else {
            None
        }
    }

    /// Analyze responses from an observer.
    pub fn analyze_responses(&mut self, observer: &ResponseObserver) -> SignalMetrics {
        let latencies: Vec<f64> = observer
            .all_records()
            .iter()
            .filter(|r| r.status == ResponseStatus::Success)
            .map(|r| r.latency)
            .collect();

        for &lat in &latencies {
            self.process(lat);
        }

        self.metrics()
    }

    /// Get current metrics.
    pub fn metrics(&self) -> SignalMetrics {
        SignalMetrics {
            samples: self.values.len(),
            mean: self.mean(),
            std_dev: self.std_dev(),
            min: self.min(),
            max: self.max(),
            threshold: self.threshold.value,
            pass_rate: self.threshold.pass_rate(),
            anomalies: self.anomalies.len(),
        }
    }

    /// Calculate mean.
    pub fn mean(&self) -> f64 {
        if self.values.is_empty() {
            return 0.0;
        }
        self.values.iter().sum::<f64>() / self.values.len() as f64
    }

    /// Calculate standard deviation.
    pub fn std_dev(&self) -> f64 {
        if self.values.len() < 2 {
            return 0.0;
        }

        let mean = self.mean();
        let variance: f64 = self
            .values
            .iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>()
            / (self.values.len() - 1) as f64;

        variance.sqrt()
    }

    /// Get minimum value.
    pub fn min(&self) -> f64 {
        self.values
            .iter()
            .fold(f64::INFINITY, |a, &b| a.min(b))
    }

    /// Get maximum value.
    pub fn max(&self) -> f64 {
        self.values
            .iter()
            .fold(f64::NEG_INFINITY, |a, &b| a.max(b))
    }

    /// Get recent anomalies.
    pub fn recent_anomalies(&self, count: usize) -> &[AnomalyRecord] {
        let start = self.anomalies.len().saturating_sub(count);
        &self.anomalies[start..]
    }

    /// Get all anomalies.
    pub fn anomalies(&self) -> &[AnomalyRecord] {
        &self.anomalies
    }

    /// Reset the analyzer.
    pub fn reset(&mut self) {
        self.values.clear();
        self.anomalies.clear();
        self.threshold.reset();
    }

    /// Get current threshold value.
    pub fn threshold_value(&self) -> f64 {
        self.threshold.value
    }

    /// Set threshold manually.
    pub fn set_threshold(&mut self, value: f64) {
        self.threshold.set(value);
    }
}

/// Compute moving average.
pub fn moving_average(values: &[f64], window: usize) -> Vec<f64> {
    if values.is_empty() || window == 0 {
        return vec![];
    }

    let window = window.min(values.len());
    let mut result = Vec::with_capacity(values.len() - window + 1);

    for i in 0..=(values.len() - window) {
        let sum: f64 = values[i..i + window].iter().sum();
        result.push(sum / window as f64);
    }

    result
}

/// Detect trend in values.
pub fn detect_trend(values: &[f64]) -> f64 {
    if values.len() < 2 {
        return 0.0;
    }

    let n = values.len() as f64;
    let sum_x: f64 = (0..values.len()).map(|i| i as f64).sum();
    let sum_y: f64 = values.iter().sum();
    let sum_xy: f64 = values.iter().enumerate().map(|(i, y)| i as f64 * y).sum();
    let sum_xx: f64 = (0..values.len()).map(|i| (i * i) as f64).sum();

    let slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x);
    slope
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_signal_analyzer() {
        let mut analyzer = SignalAnalyzer::new(100, 2.0);

        for i in 0..50 {
            analyzer.process(i as f64 * 0.01);
        }

        let metrics = analyzer.metrics();
        assert_eq!(metrics.samples, 50);
        assert!(metrics.mean > 0.0);
    }

    #[test]
    fn test_anomaly_detection() {
        let mut analyzer = SignalAnalyzer::new(100, 2.0);

        // Normal values
        for _ in 0..50 {
            analyzer.process(0.1);
        }

        // Anomaly
        analyzer.process(10.0);

        assert!(!analyzer.anomalies().is_empty());
    }

    #[test]
    fn test_moving_average() {
        let values = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let ma = moving_average(&values, 3);

        assert_eq!(ma.len(), 3);
        assert!((ma[0] - 2.0).abs() < 1e-9);
        assert!((ma[1] - 3.0).abs() < 1e-9);
        assert!((ma[2] - 4.0).abs() < 1e-9);
    }

    #[test]
    fn test_trend_detection() {
        // Increasing trend
        let increasing = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let trend = detect_trend(&increasing);
        assert!(trend > 0.0);

        // Decreasing trend
        let decreasing = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        let trend = detect_trend(&decreasing);
        assert!(trend < 0.0);
    }
}
