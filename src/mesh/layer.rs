//! High-level mesh layer orchestrator.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

use super::{
    builder::distance_score, coagula, expand, gate, solve, EntropyControl, MeshBuilder, MeshMode,
    OperatorRegistry, PointCloud, TopologyGuard,
};
use crate::web3::ExportModule;

/// Configuration for mesh layer.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshLayerConfig {
    /// Mesh construction mode
    pub mode: MeshMode,
    /// k parameter for kNN
    pub k: usize,
    /// Radius for radius-based mode
    pub radius: f64,
    /// Maximum entropy threshold
    pub max_entropy: f64,
}

impl Default for MeshLayerConfig {
    fn default() -> Self {
        Self {
            mode: MeshMode::Knn,
            k: 5,
            radius: 1.0,
            max_entropy: 10.0,
        }
    }
}

/// High-level orchestrator for mesh pipelines.
pub struct MeshLayer {
    /// Mesh builder
    pub builder: MeshBuilder,
    /// Entropy control
    pub entropy: EntropyControl,
    /// Operator registry
    pub operators: OperatorRegistry,
    /// Export module
    pub export: ExportModule,
    /// Additional state
    state: HashMap<String, serde_json::Value>,
}

impl std::fmt::Debug for MeshLayer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MeshLayer")
            .field("point_count", &self.builder.pointcloud.len())
            .field("edge_count", &self.builder.edge_count())
            .finish()
    }
}

impl MeshLayer {
    /// Create a new mesh layer from points.
    pub fn new(points: Vec<Vec<f64>>, config: MeshLayerConfig) -> Self {
        let pointcloud = PointCloud::from_points(points);
        let builder = MeshBuilder::new(pointcloud, config.mode)
            .with_k(config.k)
            .with_radius(config.radius);

        Self {
            builder,
            entropy: EntropyControl::new(config.max_entropy),
            operators: OperatorRegistry::with_defaults(),
            export: ExportModule::default(),
            state: HashMap::new(),
        }
    }

    /// Create from an existing point cloud.
    pub fn from_pointcloud(pointcloud: PointCloud, config: MeshLayerConfig) -> Self {
        let builder = MeshBuilder::new(pointcloud, config.mode)
            .with_k(config.k)
            .with_radius(config.radius);

        Self {
            builder,
            entropy: EntropyControl::new(config.max_entropy),
            operators: OperatorRegistry::with_defaults(),
            export: ExportModule::default(),
            state: HashMap::new(),
        }
    }

    /// Build the mesh.
    pub fn build_mesh(&mut self) {
        self.builder.build();
        self.entropy.record_from_builder(&self.builder);
    }

    /// Weight edges with a custom score function.
    pub fn weight_edges<F>(&mut self, score_fn: F)
    where
        F: Fn(&[f64], &[f64]) -> f64,
    {
        self.builder.weight_edges(score_fn);
    }

    /// Weight edges with default distance score.
    pub fn weight_edges_default(&mut self) {
        self.builder.weight_edges(distance_score);
    }

    /// Apply solve operator.
    pub fn solve(&mut self) {
        solve(&mut self.builder);
        self.entropy.record_from_builder(&self.builder);
    }

    /// Apply gate operator.
    pub fn gate(&mut self, threshold: f64) {
        gate(&mut self.builder, threshold);
        self.entropy.record_from_builder(&self.builder);
    }

    /// Apply coagula operator.
    pub fn coagula(&mut self) -> HashMap<usize, usize> {
        let labels = coagula(&mut self.builder);
        self.entropy.record_from_builder(&self.builder);
        labels
    }

    /// Apply expand operator.
    pub fn expand<F>(&mut self, grad_fn: F, step: f64)
    where
        F: Fn(&[f64]) -> Vec<f64>,
    {
        expand(&mut self.builder, grad_fn, step);
        self.entropy.record_from_builder(&self.builder);
    }

    /// Check topology.
    pub fn check_topology(&self) -> (bool, Vec<usize>) {
        let guard = TopologyGuard::new(&self.builder);
        (guard.check_coherence(), guard.betti_numbers())
    }

    /// Check entropy stability.
    pub fn check_entropy(&self) -> (bool, f64) {
        let e = self.entropy.entropy(&self.builder);
        (self.entropy.is_stable(&self.builder), e)
    }

    /// Get audit trail.
    pub fn audit(&self) -> Vec<super::builder::MeshAuditEvent> {
        self.builder.audit_trail().to_vec()
    }

    /// Export mesh to JSON.
    pub fn export_json(&self, filename: &str) -> std::io::Result<PathBuf> {
        let mesh_data = MeshExportData {
            points: self.builder.pointcloud.to_array(),
            edges: self.builder.edges().to_vec(),
            edge_scores: self
                .builder
                .edge_scores
                .iter()
                .map(|((i, j), s)| (format!("{i}-{j}"), *s))
                .collect(),
            metadata: self.state.clone(),
        };
        self.export.export_as_json(&mesh_data, filename)
    }

    /// Get point count.
    pub fn point_count(&self) -> usize {
        self.builder.pointcloud.len()
    }

    /// Get edge count.
    pub fn edge_count(&self) -> usize {
        self.builder.edge_count()
    }

    /// Set state value.
    pub fn set_state(&mut self, key: impl Into<String>, value: serde_json::Value) {
        self.state.insert(key.into(), value);
    }

    /// Get state value.
    pub fn get_state(&self, key: &str) -> Option<&serde_json::Value> {
        self.state.get(key)
    }

    /// Print statistics.
    pub fn print_stats(&self) {
        println!("Points: {}", self.point_count());
        println!("Edges: {}", self.edge_count());
        let (stable, entropy) = self.check_entropy();
        println!("Entropy: {:.2} (stable: {})", entropy, stable);
        let (coherent, betti) = self.check_topology();
        println!("Topology: coherent={}, betti={:?}", coherent, betti);
    }
}

/// Mesh export data structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshExportData {
    /// Point coordinates
    pub points: Vec<Vec<f64>>,
    /// Edge indices
    pub edges: Vec<(usize, usize)>,
    /// Edge scores
    pub edge_scores: HashMap<String, f64>,
    /// Metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mesh_layer_creation() {
        let points = vec![vec![0.0, 0.0], vec![1.0, 0.0], vec![2.0, 0.0]];
        let layer = MeshLayer::new(points, Default::default());

        assert_eq!(layer.point_count(), 3);
        assert_eq!(layer.edge_count(), 0); // Not built yet
    }

    #[test]
    fn test_mesh_layer_pipeline() {
        let points = vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
            vec![3.0, 0.0],
        ];
        let mut layer = MeshLayer::new(points, Default::default());

        layer.build_mesh();
        assert!(layer.edge_count() > 0);

        layer.weight_edges_default();
        layer.solve();

        let (coherent, _) = layer.check_topology();
        assert!(coherent);
    }

    #[test]
    fn test_entropy_tracking() {
        let points = vec![vec![0.0], vec![1.0], vec![2.0]];
        let mut layer = MeshLayer::new(points, Default::default());

        layer.build_mesh();
        let (stable, entropy) = layer.check_entropy();

        assert!(entropy > 0.0);
        assert!(stable);
    }
}
