//! Entropy control for mesh complexity management.

use serde::{Deserialize, Serialize};

use super::MeshBuilder;

/// Tracks mesh complexity using entropy metrics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EntropyControl {
    /// Maximum allowed entropy
    pub max_entropy: f64,
    /// Entropy history
    history: Vec<f64>,
    /// Maximum history size
    max_history: usize,
}

impl Default for EntropyControl {
    fn default() -> Self {
        Self {
            max_entropy: 10.0,
            history: Vec::new(),
            max_history: 100,
        }
    }
}

impl EntropyControl {
    /// Create with custom max entropy.
    pub fn new(max_entropy: f64) -> Self {
        Self {
            max_entropy,
            ..Default::default()
        }
    }

    /// Calculate entropy for a mesh builder.
    pub fn entropy(&self, builder: &MeshBuilder) -> f64 {
        let num_points = builder.pointcloud.len();
        let num_edges = builder.edge_count();

        // Logarithmic complexity measure
        (1 + num_points).ilog2() as f64 + (1 + num_edges).ilog2() as f64
    }

    /// Check if the mesh is stable (below max entropy).
    pub fn is_stable(&self, builder: &MeshBuilder) -> bool {
        self.entropy(builder) < self.max_entropy
    }

    /// Record current entropy value.
    pub fn record(&mut self, entropy: f64) {
        if self.history.len() >= self.max_history {
            self.history.remove(0);
        }
        self.history.push(entropy);
    }

    /// Record entropy from a builder.
    pub fn record_from_builder(&mut self, builder: &MeshBuilder) {
        let e = self.entropy(builder);
        self.record(e);
    }

    /// Get entropy trend (positive = increasing, negative = decreasing).
    pub fn trend(&self) -> f64 {
        if self.history.len() < 2 {
            return 0.0;
        }

        let n = self.history.len();
        let recent = &self.history[n / 2..];
        let older = &self.history[..n / 2];

        let recent_avg: f64 = recent.iter().sum::<f64>() / recent.len() as f64;
        let older_avg: f64 = older.iter().sum::<f64>() / older.len() as f64;

        recent_avg - older_avg
    }

    /// Get the average entropy.
    pub fn average(&self) -> f64 {
        if self.history.is_empty() {
            return 0.0;
        }
        self.history.iter().sum::<f64>() / self.history.len() as f64
    }

    /// Get the current (latest) entropy.
    pub fn current(&self) -> Option<f64> {
        self.history.last().copied()
    }

    /// Get entropy variance.
    pub fn variance(&self) -> f64 {
        if self.history.len() < 2 {
            return 0.0;
        }

        let avg = self.average();
        let sum_sq: f64 = self.history.iter().map(|x| (x - avg).powi(2)).sum();
        sum_sq / (self.history.len() - 1) as f64
    }

    /// Clear history.
    pub fn clear_history(&mut self) {
        self.history.clear();
    }

    /// Get history length.
    pub fn history_len(&self) -> usize {
        self.history.len()
    }
}

/// Calculate edge distribution entropy.
pub fn edge_distribution_entropy(builder: &MeshBuilder) -> f64 {
    if builder.edge_scores.is_empty() {
        return 0.0;
    }

    let scores: Vec<f64> = builder.edge_scores.values().copied().collect();
    let total: f64 = scores.iter().sum();

    if total < 1e-9 {
        return 0.0;
    }

    // Shannon entropy
    let mut entropy = 0.0;
    for score in &scores {
        let p = score / total;
        if p > 1e-9 {
            entropy -= p * p.ln();
        }
    }

    entropy
}

/// Calculate spatial entropy based on point distribution.
pub fn spatial_entropy(builder: &MeshBuilder, bins: usize) -> f64 {
    let n = builder.pointcloud.len();
    if n == 0 || bins == 0 {
        return 0.0;
    }

    let dims = builder.pointcloud.dimensions;
    if dims == 0 {
        return 0.0;
    }

    // Use first dimension for binning
    let values: Vec<f64> = builder
        .pointcloud
        .points()
        .iter()
        .filter_map(|p| p.get(0).copied())
        .collect();

    if values.is_empty() {
        return 0.0;
    }

    let min = values.iter().fold(f64::INFINITY, |a, &b| a.min(b));
    let max = values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    let range = max - min;

    if range < 1e-9 {
        return 0.0;
    }

    // Count points in each bin
    let mut counts = vec![0usize; bins];
    for val in &values {
        let bin = (((val - min) / range) * (bins - 1) as f64).round() as usize;
        counts[bin.min(bins - 1)] += 1;
    }

    // Shannon entropy
    let mut entropy = 0.0;
    let total = values.len() as f64;
    for count in counts {
        if count > 0 {
            let p = count as f64 / total;
            entropy -= p * p.ln();
        }
    }

    entropy
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mesh::{MeshMode, PointCloud};

    #[test]
    fn test_entropy_control() {
        let cloud = PointCloud::from_points(vec![vec![0.0], vec![1.0], vec![2.0]]);
        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();

        let control = EntropyControl::new(20.0);
        let entropy = control.entropy(&builder);

        assert!(entropy > 0.0);
        assert!(control.is_stable(&builder));
    }

    #[test]
    fn test_entropy_history() {
        let mut control = EntropyControl::new(10.0);
        control.record(1.0);
        control.record(2.0);
        control.record(3.0);

        assert_eq!(control.history_len(), 3);
        assert!((control.average() - 2.0).abs() < 1e-9);
    }

    #[test]
    fn test_trend() {
        let mut control = EntropyControl::new(10.0);

        // Increasing trend
        for i in 0..10 {
            control.record(i as f64);
        }

        assert!(control.trend() > 0.0);
    }
}
