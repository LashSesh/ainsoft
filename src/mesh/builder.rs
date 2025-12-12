//! Mesh construction from point clouds.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

use super::PointCloud;

/// Mesh construction mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum MeshMode {
    /// k-Nearest Neighbors graph
    #[default]
    Knn,
    /// Delaunay-like triangulation (simplified)
    Delaunay,
    /// Radius-based connectivity
    Radius,
    /// Full connectivity (all pairs)
    Complete,
}

/// Audit event for mesh operations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshAuditEvent {
    /// Event name
    pub event: String,
    /// Event details
    pub info: HashMap<String, serde_json::Value>,
    /// Timestamp
    pub timestamp: f64,
}

impl MeshAuditEvent {
    /// Create a new audit event.
    pub fn new(event: impl Into<String>, info: HashMap<String, serde_json::Value>) -> Self {
        Self {
            event: event.into(),
            info,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        }
    }
}

/// Constructs meshes from point clouds.
#[derive(Debug, Clone)]
pub struct MeshBuilder {
    /// Source point cloud
    pub pointcloud: PointCloud,
    /// Construction mode
    pub mode: MeshMode,
    /// k parameter for kNN
    pub k: usize,
    /// Radius for radius-based mode
    pub radius: f64,
    /// Computed edges (index pairs)
    pub edges: Vec<(usize, usize)>,
    /// Edge scores/weights
    pub edge_scores: HashMap<(usize, usize), f64>,
    /// Audit log
    pub audit_log: Vec<MeshAuditEvent>,
}

impl MeshBuilder {
    /// Create a new mesh builder.
    pub fn new(pointcloud: PointCloud, mode: MeshMode) -> Self {
        Self {
            pointcloud,
            mode,
            k: 5,
            radius: 1.0,
            edges: Vec::new(),
            edge_scores: HashMap::new(),
            audit_log: Vec::new(),
        }
    }

    /// Set k parameter.
    pub fn with_k(mut self, k: usize) -> Self {
        self.k = k.max(1);
        self
    }

    /// Set radius parameter.
    pub fn with_radius(mut self, radius: f64) -> Self {
        self.radius = radius.max(0.0);
        self
    }

    /// Build the mesh.
    pub fn build(&mut self) {
        let n = self.pointcloud.len();
        if n <= 1 {
            self.edges.clear();
            self.audit(
                "build",
                serde_json::json!({"edges": 0, "reason": "insufficient_points"}),
            );
            return;
        }

        match self.mode {
            MeshMode::Knn => self.build_knn(),
            MeshMode::Delaunay => self.build_delaunay_approx(),
            MeshMode::Radius => self.build_radius(),
            MeshMode::Complete => self.build_complete(),
        }

        self.audit(
            "build",
            serde_json::json!({"edges": self.edges.len(), "mode": format!("{:?}", self.mode)}),
        );
    }

    /// Build kNN graph.
    fn build_knn(&mut self) {
        let mut edge_set: HashSet<(usize, usize)> = HashSet::new();
        let n = self.pointcloud.len();
        let k = self.k.min(n - 1);

        for i in 0..n {
            let neighbors = self.pointcloud.k_nearest(i, k);
            for (j, _) in neighbors {
                let edge = if i < j { (i, j) } else { (j, i) };
                edge_set.insert(edge);
            }
        }

        self.edges = edge_set.into_iter().collect();
        self.edges.sort();
    }

    /// Build approximate Delaunay triangulation using kNN with higher k.
    fn build_delaunay_approx(&mut self) {
        // Use higher k for denser connectivity (approximating Delaunay)
        let saved_k = self.k;
        self.k = (self.pointcloud.len() / 2).max(3).min(20);
        self.build_knn();
        self.k = saved_k;
    }

    /// Build radius-based connectivity.
    fn build_radius(&mut self) {
        let mut edge_set: HashSet<(usize, usize)> = HashSet::new();
        let n = self.pointcloud.len();

        for i in 0..n {
            for j in (i + 1)..n {
                if let Some(dist) = self.pointcloud.distance(i, j) {
                    if dist <= self.radius {
                        edge_set.insert((i, j));
                    }
                }
            }
        }

        self.edges = edge_set.into_iter().collect();
        self.edges.sort();
    }

    /// Build complete graph.
    fn build_complete(&mut self) {
        let n = self.pointcloud.len();
        self.edges.clear();

        for i in 0..n {
            for j in (i + 1)..n {
                self.edges.push((i, j));
            }
        }
    }

    /// Assign weights to edges using a scoring function.
    pub fn weight_edges<F>(&mut self, score_fn: F)
    where
        F: Fn(&[f64], &[f64]) -> f64,
    {
        self.edge_scores.clear();

        for &(i, j) in &self.edges {
            if let (Some(p1), Some(p2)) = (self.pointcloud.get(i), self.pointcloud.get(j)) {
                let score = score_fn(p1.as_slice(), p2.as_slice());
                self.edge_scores.insert((i, j), score);
            }
        }

        self.audit(
            "weight_edges",
            serde_json::json!({"edges_weighted": self.edge_scores.len()}),
        );
    }

    /// Get the audit trail.
    pub fn audit_trail(&self) -> &[MeshAuditEvent] {
        &self.audit_log
    }

    /// Record an audit event.
    fn audit(&mut self, event: &str, info: serde_json::Value) {
        let mut info_map = HashMap::new();
        if let serde_json::Value::Object(obj) = info {
            for (k, v) in obj {
                info_map.insert(k, v);
            }
        }
        self.audit_log.push(MeshAuditEvent::new(event, info_map));
    }

    /// Remove an edge.
    pub fn remove_edge(&mut self, edge: (usize, usize)) {
        self.edges.retain(|e| *e != edge);
        self.edge_scores.remove(&edge);
    }

    /// Get edge count.
    pub fn edge_count(&self) -> usize {
        self.edges.len()
    }

    /// Get edges.
    pub fn edges(&self) -> &[(usize, usize)] {
        &self.edges
    }

    /// Get edge score.
    pub fn edge_score(&self, edge: (usize, usize)) -> Option<f64> {
        self.edge_scores.get(&edge).copied()
    }
}

/// Distance-based score function (inverse distance).
pub fn distance_score(v1: &[f64], v2: &[f64]) -> f64 {
    let dist_sq: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| (a - b).powi(2)).sum();
    1.0 / (1.0 + dist_sq.sqrt())
}

/// Cosine similarity score.
pub fn cosine_score(v1: &[f64], v2: &[f64]) -> f64 {
    let dot: f64 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
    let norm1: f64 = v1.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm2: f64 = v2.iter().map(|x| x * x).sum::<f64>().sqrt();

    if norm1 < 1e-9 || norm2 < 1e-9 {
        return 0.0;
    }

    (dot / (norm1 * norm2)).clamp(-1.0, 1.0) * 0.5 + 0.5
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_knn_build() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
            vec![3.0, 0.0],
        ]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Knn).with_k(2);
        builder.build();

        assert!(builder.edge_count() > 0);
    }

    #[test]
    fn test_radius_build() {
        let cloud = PointCloud::from_points(vec![vec![0.0, 0.0], vec![0.5, 0.0], vec![10.0, 0.0]]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Radius).with_radius(1.0);
        builder.build();

        // Only first two points should be connected
        assert_eq!(builder.edge_count(), 1);
        assert!(builder.edges.contains(&(0, 1)));
    }

    #[test]
    fn test_weight_edges() {
        let cloud = PointCloud::from_points(vec![vec![0.0, 0.0], vec![1.0, 0.0]]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();
        builder.weight_edges(distance_score);

        assert!(builder.edge_score((0, 1)).is_some());
    }

    #[test]
    fn test_audit_trail() {
        let cloud = PointCloud::from_points(vec![vec![0.0], vec![1.0]]);
        let mut builder = MeshBuilder::new(cloud, MeshMode::Knn);
        builder.build();

        assert!(!builder.audit_trail().is_empty());
        assert_eq!(builder.audit_trail()[0].event, "build");
    }
}
