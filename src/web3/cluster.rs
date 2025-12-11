//! Seed clustering using simple k-means or fallback heuristics.

use nalgebra::DVector;
use rand::seq::SliceRandom;
use rand::Rng;
use serde::{Deserialize, Serialize};

/// Configuration for clustering.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterConfig {
    /// Number of clusters
    pub n_clusters: usize,
    /// Maximum iterations for k-means
    pub max_iterations: usize,
    /// Convergence tolerance
    pub tolerance: f64,
}

impl Default for ClusterConfig {
    fn default() -> Self {
        Self {
            n_clusters: 3,
            max_iterations: 100,
            tolerance: 1e-6,
        }
    }
}

/// Result of a clustering operation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClusterResult {
    /// Cluster labels for each input point
    pub labels: Vec<usize>,
    /// Cluster centroids
    pub centroids: Vec<Vec<f64>>,
    /// Inertia (sum of squared distances to centroids)
    pub inertia: f64,
    /// Number of iterations performed
    pub iterations: usize,
}

/// Engine for clustering seed geometries.
#[derive(Debug, Clone)]
pub struct SeedClusterEngine {
    config: ClusterConfig,
}

impl Default for SeedClusterEngine {
    fn default() -> Self {
        Self {
            config: ClusterConfig::default(),
        }
    }
}

impl SeedClusterEngine {
    /// Create with custom configuration.
    pub fn new(n_clusters: usize) -> Self {
        Self {
            config: ClusterConfig {
                n_clusters: n_clusters.max(1),
                ..Default::default()
            },
        }
    }

    /// Create with full configuration.
    pub fn with_config(config: ClusterConfig) -> Self {
        Self { config }
    }

    /// Cluster seeds and return labels.
    pub fn cluster_seeds(&self, seeds: &[DVector<f64>]) -> Vec<usize> {
        if seeds.is_empty() {
            return vec![];
        }

        if seeds.len() < self.config.n_clusters {
            // Fallback: assign by modulo
            return (0..seeds.len())
                .map(|i| i % self.config.n_clusters)
                .collect();
        }

        self.kmeans(seeds).labels
    }

    /// Run k-means clustering and return full result.
    pub fn kmeans(&self, data: &[DVector<f64>]) -> ClusterResult {
        if data.is_empty() {
            return ClusterResult {
                labels: vec![],
                centroids: vec![],
                inertia: 0.0,
                iterations: 0,
            };
        }

        let n = data.len();
        let k = self.config.n_clusters.min(n);
        let dim = data[0].len();

        // Initialize centroids using k-means++
        let mut centroids = self.initialize_centroids(data, k);
        let mut labels = vec![0usize; n];
        let mut prev_inertia = f64::INFINITY;
        let mut iterations = 0;

        for iter in 0..self.config.max_iterations {
            iterations = iter + 1;

            // Assignment step: assign each point to nearest centroid
            let mut inertia = 0.0;
            for (i, point) in data.iter().enumerate() {
                let (nearest, dist_sq) = self.find_nearest_centroid(point, &centroids);
                labels[i] = nearest;
                inertia += dist_sq;
            }

            // Update step: recalculate centroids
            let new_centroids = self.update_centroids(data, &labels, k, dim);
            centroids = new_centroids;

            // Check convergence
            if (prev_inertia - inertia).abs() < self.config.tolerance {
                break;
            }
            prev_inertia = inertia;
        }

        // Calculate final inertia
        let inertia: f64 = data
            .iter()
            .zip(labels.iter())
            .map(|(point, &label)| {
                let centroid = DVector::from_vec(centroids[label].clone());
                (point - centroid).norm_squared()
            })
            .sum();

        ClusterResult {
            labels,
            centroids,
            inertia,
            iterations,
        }
    }

    /// Initialize centroids using k-means++.
    fn initialize_centroids(&self, data: &[DVector<f64>], k: usize) -> Vec<Vec<f64>> {
        let mut rng = rand::thread_rng();
        let mut centroids = Vec::with_capacity(k);

        // First centroid: random point
        let first_idx = rng.gen_range(0..data.len());
        centroids.push(data[first_idx].as_slice().to_vec());

        // Remaining centroids: weighted by distance squared
        for _ in 1..k {
            let weights: Vec<f64> = data
                .iter()
                .map(|point| {
                    centroids
                        .iter()
                        .map(|c| {
                            let c_vec = DVector::from_vec(c.clone());
                            (point - c_vec).norm_squared()
                        })
                        .fold(f64::INFINITY, f64::min)
                })
                .collect();

            let total: f64 = weights.iter().sum();
            if total < 1e-9 {
                // All points are centroids, pick randomly
                let idx = rng.gen_range(0..data.len());
                centroids.push(data[idx].as_slice().to_vec());
            } else {
                // Weighted random selection
                let threshold = rng.gen::<f64>() * total;
                let mut cumsum = 0.0;
                for (i, &w) in weights.iter().enumerate() {
                    cumsum += w;
                    if cumsum >= threshold {
                        centroids.push(data[i].as_slice().to_vec());
                        break;
                    }
                }
            }
        }

        centroids
    }

    /// Find the nearest centroid to a point.
    fn find_nearest_centroid(&self, point: &DVector<f64>, centroids: &[Vec<f64>]) -> (usize, f64) {
        let mut best_idx = 0;
        let mut best_dist = f64::INFINITY;

        for (i, centroid) in centroids.iter().enumerate() {
            let c_vec = DVector::from_vec(centroid.clone());
            let dist_sq = (point - c_vec).norm_squared();
            if dist_sq < best_dist {
                best_dist = dist_sq;
                best_idx = i;
            }
        }

        (best_idx, best_dist)
    }

    /// Update centroids based on current assignments.
    fn update_centroids(
        &self,
        data: &[DVector<f64>],
        labels: &[usize],
        k: usize,
        dim: usize,
    ) -> Vec<Vec<f64>> {
        let mut sums: Vec<Vec<f64>> = vec![vec![0.0; dim]; k];
        let mut counts: Vec<usize> = vec![0; k];

        for (point, &label) in data.iter().zip(labels.iter()) {
            for (j, val) in point.iter().enumerate() {
                sums[label][j] += val;
            }
            counts[label] += 1;
        }

        sums.iter()
            .zip(counts.iter())
            .map(|(sum, &count)| {
                if count == 0 {
                    sum.clone()
                } else {
                    sum.iter().map(|v| v / count as f64).collect()
                }
            })
            .collect()
    }

    /// Calculate silhouette score for clustering quality.
    pub fn silhouette_score(&self, data: &[DVector<f64>], labels: &[usize]) -> f64 {
        if data.len() < 2 {
            return 0.0;
        }

        let n_clusters = *labels.iter().max().unwrap_or(&0) + 1;
        let mut silhouettes = Vec::with_capacity(data.len());

        for (i, point) in data.iter().enumerate() {
            let my_label = labels[i];

            // a(i): mean distance to same cluster
            let same_cluster: Vec<_> = data
                .iter()
                .enumerate()
                .filter(|(j, _)| *j != i && labels[*j] == my_label)
                .map(|(_, p)| (point - p).norm())
                .collect();

            let a = if same_cluster.is_empty() {
                0.0
            } else {
                same_cluster.iter().sum::<f64>() / same_cluster.len() as f64
            };

            // b(i): min mean distance to other clusters
            let mut b = f64::INFINITY;
            for c in 0..n_clusters {
                if c == my_label {
                    continue;
                }
                let other_cluster: Vec<_> = data
                    .iter()
                    .enumerate()
                    .filter(|(j, _)| labels[*j] == c)
                    .map(|(_, p)| (point - p).norm())
                    .collect();

                if !other_cluster.is_empty() {
                    let mean_dist = other_cluster.iter().sum::<f64>() / other_cluster.len() as f64;
                    b = b.min(mean_dist);
                }
            }

            if b == f64::INFINITY {
                b = 0.0;
            }

            let s = if a.max(b) < 1e-9 {
                0.0
            } else {
                (b - a) / a.max(b)
            };
            silhouettes.push(s);
        }

        silhouettes.iter().sum::<f64>() / silhouettes.len() as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cluster_empty() {
        let engine = SeedClusterEngine::new(3);
        let labels = engine.cluster_seeds(&[]);
        assert!(labels.is_empty());
    }

    #[test]
    fn test_cluster_single() {
        let engine = SeedClusterEngine::new(3);
        let seeds = vec![DVector::from_vec(vec![1.0, 2.0, 3.0, 4.0, 5.0])];
        let labels = engine.cluster_seeds(&seeds);
        assert_eq!(labels.len(), 1);
    }

    #[test]
    fn test_cluster_multiple() {
        let engine = SeedClusterEngine::new(2);
        let seeds = vec![
            DVector::from_vec(vec![0.0, 0.0, 0.0, 0.0, 0.0]),
            DVector::from_vec(vec![0.1, 0.1, 0.1, 0.1, 0.1]),
            DVector::from_vec(vec![10.0, 10.0, 10.0, 10.0, 10.0]),
            DVector::from_vec(vec![10.1, 10.1, 10.1, 10.1, 10.1]),
        ];
        let labels = engine.cluster_seeds(&seeds);
        assert_eq!(labels.len(), 4);

        // Points 0,1 should be in same cluster, 2,3 in same cluster
        assert_eq!(labels[0], labels[1]);
        assert_eq!(labels[2], labels[3]);
        assert_ne!(labels[0], labels[2]);
    }
}
