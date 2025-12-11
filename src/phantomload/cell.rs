//! Phantom cell management for phantomload simulations.

use nalgebra::DVector;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

use crate::web3::{MutationEngine, SeedClusterEngine, SeedDnaEngine};

/// Represents a phantomload cell tied to a seed geometry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhantomCell {
    /// Cell identifier
    pub cell_id: String,
    /// 5D geometry vector
    #[serde(with = "dvector_serde")]
    pub geometry: DVector<f64>,
    /// Associated seed phrase
    pub seed_phrase: String,
    /// Cluster assignment
    pub cluster: Option<usize>,
    /// Creation timestamp
    pub created_at: f64,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
}

mod dvector_serde {
    use nalgebra::DVector;
    use serde::{Deserialize, Deserializer, Serialize, Serializer};

    pub fn serialize<S>(v: &DVector<f64>, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        v.as_slice().serialize(serializer)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<DVector<f64>, D::Error>
    where
        D: Deserializer<'de>,
    {
        let vec = Vec::<f64>::deserialize(deserializer)?;
        Ok(DVector::from_vec(vec))
    }
}

impl PhantomCell {
    /// Create a new phantom cell.
    pub fn new(cell_id: impl Into<String>, geometry: DVector<f64>, seed_phrase: impl Into<String>) -> Self {
        Self {
            cell_id: cell_id.into(),
            geometry,
            seed_phrase: seed_phrase.into(),
            cluster: None,
            created_at: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
            metadata: HashMap::new(),
        }
    }

    /// Get a 3D position from the 5D geometry.
    pub fn position(&self) -> [f64; 3] {
        let g = &self.geometry;
        let len = g.len();
        [
            if len > 0 { g[0] } else { 0.0 },
            if len > 1 { g[1] } else { 0.0 },
            if len > 2 { g[2] } else { 0.0 },
        ]
    }

    /// Get a score based on geometry magnitude.
    pub fn score(&self) -> f64 {
        self.geometry.norm()
    }

    /// Get a serializable snapshot.
    pub fn snapshot(&self) -> HashMap<String, serde_json::Value> {
        let pos = self.position();
        let mut data = HashMap::new();
        data.insert("id".to_string(), serde_json::json!(self.cell_id));
        data.insert("position".to_string(), serde_json::json!(pos));
        data.insert("score".to_string(), serde_json::json!(self.score()));
        data.insert("cluster".to_string(), serde_json::json!(self.cluster));
        data.insert("created_at".to_string(), serde_json::json!(self.created_at));
        data.insert("seed".to_string(), serde_json::json!(self.seed_phrase));
        data.insert("metadata".to_string(), serde_json::json!(self.metadata));
        data
    }

    /// Set metadata.
    pub fn set_metadata(&mut self, key: impl Into<String>, value: serde_json::Value) {
        self.metadata.insert(key.into(), value);
    }
}

/// Manager for phantom cells.
pub struct PhantomCellManager {
    /// DNA encoding engine
    dna_engine: SeedDnaEngine,
    /// Mutation engine
    mutation_engine: MutationEngine,
    /// Clustering engine
    cluster_engine: SeedClusterEngine,
    /// Registered cells
    cells: HashMap<String, PhantomCell>,
}

impl std::fmt::Debug for PhantomCellManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PhantomCellManager")
            .field("cell_count", &self.cells.len())
            .finish()
    }
}

impl Default for PhantomCellManager {
    fn default() -> Self {
        Self::new(
            SeedDnaEngine::default(),
            MutationEngine::default(),
            SeedClusterEngine::default(),
        )
    }
}

impl PhantomCellManager {
    /// Create a new cell manager.
    pub fn new(
        dna_engine: SeedDnaEngine,
        mutation_engine: MutationEngine,
        cluster_engine: SeedClusterEngine,
    ) -> Self {
        Self {
            dna_engine,
            mutation_engine,
            cluster_engine,
            cells: HashMap::new(),
        }
    }

    /// Spawn multiple cells from a base phrase.
    pub fn spawn_cells(&mut self, count: usize, base_phrase: &str, mutate: bool) -> Vec<String> {
        let mut created = Vec::with_capacity(count);

        for index in 0..count {
            let phrase = format!("{base_phrase}-{index}");
            let geometry = if mutate {
                let mutated = self.mutation_engine.generate_mutant(&phrase);
                DVector::from_vec(mutated.into_iter().take(5).collect())
            } else {
                self.dna_engine.encode(&phrase)
            };

            let cell_id = Uuid::new_v4().to_string();
            let cell = PhantomCell::new(&cell_id, geometry, &phrase);
            self.cells.insert(cell_id.clone(), cell);
            created.push(cell_id);
        }

        self.assign_clusters();
        created
    }

    /// Assign cluster labels to all cells.
    pub fn assign_clusters(&mut self) {
        if self.cells.is_empty() {
            return;
        }

        let seeds: Vec<DVector<f64>> = self.cells.values().map(|c| c.geometry.clone()).collect();
        let labels = self.cluster_engine.cluster_seeds(&seeds);

        for (cell, label) in self.cells.values_mut().zip(labels.iter()) {
            cell.cluster = Some(*label);
        }
    }

    /// Generate a mesh representation for visualization.
    pub fn to_mesh(&self, view: &str) -> MeshData {
        let nodes: Vec<_> = self.cells.values().map(|c| c.snapshot()).collect();

        // Create edges between consecutive cells (simple ring topology)
        let cell_ids: Vec<_> = self.cells.keys().cloned().collect();
        let mut edges = Vec::new();

        for i in 0..cell_ids.len() {
            let src = &cell_ids[i];
            let dst = &cell_ids[(i + 1) % cell_ids.len()];

            if src == dst {
                continue;
            }

            if let (Some(c1), Some(c2)) = (self.cells.get(src), self.cells.get(dst)) {
                let distance = (&c1.geometry - &c2.geometry).norm();
                edges.push(EdgeData {
                    source: src.clone(),
                    target: dst.clone(),
                    weight: distance,
                });
            }
        }

        MeshData {
            view: view.to_string(),
            nodes,
            edges,
        }
    }

    /// Get cell count.
    pub fn cell_count(&self) -> usize {
        self.cells.len()
    }

    /// Get a cell by ID.
    pub fn get(&self, cell_id: &str) -> Option<&PhantomCell> {
        self.cells.get(cell_id)
    }

    /// Get mutable reference to a cell.
    pub fn get_mut(&mut self, cell_id: &str) -> Option<&mut PhantomCell> {
        self.cells.get_mut(cell_id)
    }

    /// Remove a cell.
    pub fn remove(&mut self, cell_id: &str) -> Option<PhantomCell> {
        self.cells.remove(cell_id)
    }

    /// Reset (remove all cells).
    pub fn reset(&mut self) {
        self.cells.clear();
    }

    /// Iterate over cells.
    pub fn iter(&self) -> impl Iterator<Item = &PhantomCell> {
        self.cells.values()
    }
}

/// Mesh representation for visualization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshData {
    /// View name
    pub view: String,
    /// Node data
    pub nodes: Vec<HashMap<String, serde_json::Value>>,
    /// Edge data
    pub edges: Vec<EdgeData>,
}

/// Edge in a mesh.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeData {
    /// Source node ID
    pub source: String,
    /// Target node ID
    pub target: String,
    /// Edge weight/distance
    pub weight: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_phantom_cell() {
        let geometry = DVector::from_vec(vec![1.0, 2.0, 3.0, 4.0, 5.0]);
        let cell = PhantomCell::new("cell-1", geometry, "test seed");

        assert_eq!(cell.position(), [1.0, 2.0, 3.0]);
        assert!(cell.score() > 0.0);
    }

    #[test]
    fn test_spawn_cells() {
        let mut manager = PhantomCellManager::default();
        let ids = manager.spawn_cells(5, "base", true);

        assert_eq!(ids.len(), 5);
        assert_eq!(manager.cell_count(), 5);

        // All cells should have cluster assignments
        for cell in manager.iter() {
            assert!(cell.cluster.is_some());
        }
    }

    #[test]
    fn test_to_mesh() {
        let mut manager = PhantomCellManager::default();
        manager.spawn_cells(4, "test", false);

        let mesh = manager.to_mesh("traffic");
        assert_eq!(mesh.nodes.len(), 4);
        assert_eq!(mesh.edges.len(), 4); // Ring topology
    }
}
