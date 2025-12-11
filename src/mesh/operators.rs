//! Mesh operators for transformation and analysis.

use std::collections::HashMap;
use std::sync::Arc;

use nalgebra::DVector;

use super::MeshBuilder;

/// Type alias for operator functions.
pub type OperatorFn = Arc<dyn Fn(&mut MeshBuilder) + Send + Sync>;

/// Registry for mesh operators.
#[derive(Clone, Default)]
pub struct OperatorRegistry {
    operators: HashMap<String, OperatorFn>,
}

impl std::fmt::Debug for OperatorRegistry {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("OperatorRegistry")
            .field("registered", &self.operators.keys().collect::<Vec<_>>())
            .finish()
    }
}

impl OperatorRegistry {
    /// Create a new empty registry.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create a registry with default operators.
    pub fn with_defaults() -> Self {
        let mut registry = Self::new();
        registry.register("solve", Arc::new(|b| solve(b)));
        registry.register("gate", Arc::new(|b| gate(b, 0.5)));
        registry.register("coagula", Arc::new(|b| {
            coagula(b);
        }));
        registry
    }

    /// Register an operator.
    pub fn register(&mut self, name: impl Into<String>, op: OperatorFn) {
        self.operators.insert(name.into(), op);
    }

    /// Get an operator by name.
    pub fn get(&self, name: &str) -> Option<&OperatorFn> {
        self.operators.get(name)
    }

    /// Execute an operator by name.
    pub fn execute(&self, name: &str, builder: &mut MeshBuilder) -> bool {
        if let Some(op) = self.get(name) {
            op(builder);
            true
        } else {
            false
        }
    }

    /// List registered operators.
    pub fn list(&self) -> Vec<&String> {
        self.operators.keys().collect()
    }
}

/// Solve operator: removes edges with score below median.
pub fn solve(builder: &mut MeshBuilder) {
    if builder.edge_scores.is_empty() {
        return;
    }

    let mut scores: Vec<f64> = builder.edge_scores.values().copied().collect();
    scores.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let median = if scores.is_empty() {
        0.0
    } else if scores.len() % 2 == 0 {
        (scores[scores.len() / 2 - 1] + scores[scores.len() / 2]) / 2.0
    } else {
        scores[scores.len() / 2]
    };

    let to_remove: Vec<(usize, usize)> = builder
        .edge_scores
        .iter()
        .filter(|(_, &score)| score < median)
        .map(|(&edge, _)| edge)
        .collect();

    for edge in &to_remove {
        builder.remove_edge(*edge);
    }

    let mut info = HashMap::new();
    info.insert("removed".to_string(), serde_json::json!(to_remove.len()));
    info.insert("median".to_string(), serde_json::json!(median));
    builder.audit_log.push(super::builder::MeshAuditEvent::new("solve", info));
}

/// Gate operator: keeps only edges above threshold.
pub fn gate(builder: &mut MeshBuilder, threshold: f64) {
    let to_remove: Vec<(usize, usize)> = builder
        .edge_scores
        .iter()
        .filter(|(_, &score)| score < threshold)
        .map(|(&edge, _)| edge)
        .collect();

    for edge in &to_remove {
        builder.remove_edge(*edge);
    }

    let mut info = HashMap::new();
    info.insert("removed".to_string(), serde_json::json!(to_remove.len()));
    info.insert("threshold".to_string(), serde_json::json!(threshold));
    builder.audit_log.push(super::builder::MeshAuditEvent::new("gate", info));
}

/// Coagula operator: merges highly resonant nodes into clusters.
pub fn coagula(builder: &mut MeshBuilder) -> HashMap<usize, usize> {
    let n = builder.pointcloud.len();
    let mut labels: HashMap<usize, usize> = (0..n).map(|i| (i, i)).collect();

    // Merge nodes connected by high-score edges
    for &(i, j) in &builder.edges {
        let score = builder.edge_scores.get(&(i, j)).copied().unwrap_or(0.0);
        if score > 0.9 {
            let label = labels[&i].min(labels[&j]);
            labels.insert(i, label);
            labels.insert(j, label);
        }
    }

    // Propagate labels
    let mut changed = true;
    while changed {
        changed = false;
        for &(i, j) in &builder.edges {
            let li = labels[&i];
            let lj = labels[&j];
            if li != lj && builder.edge_scores.get(&(i, j)).copied().unwrap_or(0.0) > 0.9 {
                let new_label = li.min(lj);
                if labels[&i] != new_label || labels[&j] != new_label {
                    labels.insert(i, new_label);
                    labels.insert(j, new_label);
                    changed = true;
                }
            }
        }
    }

    let unique_labels: std::collections::HashSet<_> = labels.values().collect();
    let mut info = HashMap::new();
    info.insert("clusters".to_string(), serde_json::json!(unique_labels.len()));
    builder.audit_log.push(super::builder::MeshAuditEvent::new("coagula", info));

    labels
}

/// Expand operator: moves points along gradient.
pub fn expand<F>(builder: &mut MeshBuilder, grad_fn: F, step: f64)
where
    F: Fn(&[f64]) -> Vec<f64>,
{
    let n = builder.pointcloud.len();

    for i in 0..n {
        if let Some(point) = builder.pointcloud.get(i) {
            let gradient = grad_fn(point.as_slice());
            let mut new_point = point.as_slice().to_vec();

            for (j, (p, g)) in new_point.iter_mut().zip(gradient.iter()).enumerate() {
                *p += step * g;
            }

            if let Some(point_mut) = builder.pointcloud.get_mut(i) {
                *point_mut = DVector::from_vec(new_point);
            }
        }
    }

    let mut info = HashMap::new();
    info.insert("step".to_string(), serde_json::json!(step));
    builder.audit_log.push(super::builder::MeshAuditEvent::new("expand", info));
}

/// Gradient function pointing towards origin.
pub fn origin_gradient(point: &[f64]) -> Vec<f64> {
    let norm: f64 = point.iter().map(|x| x * x).sum::<f64>().sqrt() + 1e-9;
    point.iter().map(|x| -x / norm).collect()
}

/// Gradient function pointing away from origin.
pub fn expand_gradient(point: &[f64]) -> Vec<f64> {
    let norm: f64 = point.iter().map(|x| x * x).sum::<f64>().sqrt() + 1e-9;
    point.iter().map(|x| x / norm).collect()
}

/// Contract operator: moves all points towards centroid.
pub fn contract(builder: &mut MeshBuilder, factor: f64) {
    if let Some(centroid) = builder.pointcloud.centroid() {
        let n = builder.pointcloud.len();
        for i in 0..n {
            if let Some(point) = builder.pointcloud.get_mut(i) {
                let diff = &centroid - &*point;
                *point += &diff * factor;
            }
        }
    }

    let mut info = HashMap::new();
    info.insert("factor".to_string(), serde_json::json!(factor));
    builder.audit_log.push(super::builder::MeshAuditEvent::new("contract", info));
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mesh::{builder::distance_score, MeshMode, PointCloud};

    #[test]
    fn test_solve_operator() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
            vec![10.0, 0.0],
        ]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();
        builder.weight_edges(distance_score);

        let initial_edges = builder.edge_count();
        solve(&mut builder);

        // Should have removed some edges
        assert!(builder.edge_count() < initial_edges);
    }

    #[test]
    fn test_gate_operator() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
        ]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();
        builder.weight_edges(|_, _| 0.3); // Low scores

        gate(&mut builder, 0.5);
        assert_eq!(builder.edge_count(), 0); // All removed
    }

    #[test]
    fn test_coagula_operator() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![0.1, 0.0],
            vec![10.0, 0.0],
        ]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();
        builder.weight_edges(distance_score);

        let labels = coagula(&mut builder);
        assert_eq!(labels.len(), 3);
    }

    #[test]
    fn test_registry() {
        let registry = OperatorRegistry::with_defaults();
        assert!(registry.get("solve").is_some());
        assert!(registry.get("gate").is_some());
    }
}
