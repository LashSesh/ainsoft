//! High-level kernel that orchestrates Web3 research workflows.

use nalgebra::DVector;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

use super::{
    ExportModule, MetaMemoryCore, MutationEngine, ReverbRing, ScorpioBridge, SeedClusterEngine,
    SeedDnaEngine, SupervisorInterface,
};

/// Configuration for Phosphoros kernel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KernelConfig {
    /// Heartbeat interval in seconds
    pub tick_interval: f64,
    /// Enable heartbeat bridge
    pub bridge_enabled: bool,
    /// Mutation rate
    pub mutation_rate: f64,
    /// Number of clusters
    pub n_clusters: usize,
    /// Maximum history size
    pub max_history: Option<usize>,
    /// Export directory
    pub export_path: Option<PathBuf>,
}

impl Default for KernelConfig {
    fn default() -> Self {
        Self {
            tick_interval: 0.017,
            bridge_enabled: true,
            mutation_rate: 0.1,
            n_clusters: 3,
            max_history: Some(1000),
            export_path: None,
        }
    }
}

/// High-level manager for Web3 research workflows.
pub struct PhosphorosKernel {
    /// Heartbeat bridge
    pub bridge: ScorpioBridge,
    /// DNA encoding engine
    pub dna_engine: SeedDnaEngine,
    /// Mutation engine
    pub mutation_engine: MutationEngine,
    /// Clustering engine
    pub cluster_engine: SeedClusterEngine,
    /// Supervisor interface
    pub supervisor: SupervisorInterface,
    /// Memory core
    pub meta_memory: MetaMemoryCore,
    /// Export module
    pub export: ExportModule,
    /// Activity ring
    pub reverb: ReverbRing,
    /// Stored seed geometries
    seeds: Vec<DVector<f64>>,
    /// Cluster labels
    clusters: Vec<usize>,
    /// Configuration
    config: KernelConfig,
}

impl std::fmt::Debug for PhosphorosKernel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PhosphorosKernel")
            .field("seed_count", &self.seeds.len())
            .field("cluster_count", &self.clusters.len())
            .field("config", &self.config)
            .finish()
    }
}

impl Default for PhosphorosKernel {
    fn default() -> Self {
        Self::with_config(KernelConfig::default())
    }
}

impl PhosphorosKernel {
    /// Create a kernel with custom configuration.
    pub fn with_config(config: KernelConfig) -> Self {
        let bridge =
            ScorpioBridge::new(std::time::Duration::from_secs_f64(config.tick_interval));
        let dna_engine = SeedDnaEngine::default();
        let mutation_engine = MutationEngine::with_rate(config.mutation_rate);
        let cluster_engine = SeedClusterEngine::new(config.n_clusters);
        let meta_memory = MetaMemoryCore::new(config.max_history);
        let export = match &config.export_path {
            Some(path) => ExportModule::new(path),
            None => ExportModule::default(),
        };

        Self {
            bridge,
            dna_engine,
            mutation_engine,
            cluster_engine,
            supervisor: SupervisorInterface::new(),
            meta_memory,
            export,
            reverb: ReverbRing::new(),
            seeds: Vec::new(),
            clusters: Vec::new(),
            config,
        }
    }

    /// Add a seed phrase and encode its geometry.
    pub fn add_seed_phrase(&mut self, phrase: &str, mutate: bool) -> DVector<f64> {
        let geometry = self.dna_engine.encode(phrase);
        self.seeds.push(geometry.clone());

        // Log activity
        let mut activity = HashMap::new();
        activity.insert("seed".to_string(), geometry.norm());
        activity.insert(
            "timestamp".to_string(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        );
        self.reverb.log(activity.clone());

        if mutate {
            let mutant = self.mutation_engine.generate_mutant(phrase);
            let mut mutant_activity = HashMap::new();
            mutant_activity.insert("mutant".to_string(), mutant.iter().sum());
            self.reverb.log(mutant_activity);
        }

        geometry
    }

    /// Cluster all seeds and cache labels.
    pub fn cluster(&mut self) -> Vec<usize> {
        if self.seeds.is_empty() {
            self.clusters = vec![];
            return vec![];
        }

        let labels = self.cluster_engine.cluster_seeds(&self.seeds);
        self.clusters = labels.clone();
        labels
    }

    /// Run a single tick (heartbeat callback).
    pub fn tick(&mut self) {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);

        let unique_clusters = if self.clusters.is_empty() {
            0
        } else {
            let mut seen = std::collections::HashSet::new();
            for &c in &self.clusters {
                seen.insert(c);
            }
            seen.len()
        };

        let mut activity = HashMap::new();
        activity.insert("tick_time".to_string(), timestamp);
        activity.insert("n_seeds".to_string(), self.seeds.len() as f64);
        activity.insert("n_clusters".to_string(), unique_clusters as f64);

        self.supervisor.update(activity.clone());
        self.meta_memory.store(activity.clone());
        self.reverb.log(activity);
    }

    /// Export current state to JSON.
    pub fn export_state(&self, filename: &str) -> std::io::Result<PathBuf> {
        let state = KernelState {
            seeds: self
                .seeds
                .iter()
                .map(|s| s.as_slice().to_vec())
                .collect(),
            clusters: self.clusters.clone(),
            history: self.meta_memory.get_history(),
            supervisor: self.supervisor.snapshot(),
        };

        self.export.export_as_json(&state, filename)
    }

    /// Get seed count.
    pub fn seed_count(&self) -> usize {
        self.seeds.len()
    }

    /// Get seeds.
    pub fn seeds(&self) -> &[DVector<f64>] {
        &self.seeds
    }

    /// Get cluster labels.
    pub fn cluster_labels(&self) -> &[usize] {
        &self.clusters
    }

    /// Clear all seeds and clusters.
    pub fn reset(&mut self) {
        self.seeds.clear();
        self.clusters.clear();
    }

    /// Get the silhouette score for current clustering.
    pub fn silhouette_score(&self) -> f64 {
        if self.seeds.is_empty() || self.clusters.is_empty() {
            return 0.0;
        }
        self.cluster_engine.silhouette_score(&self.seeds, &self.clusters)
    }
}

/// Serializable kernel state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KernelState {
    /// Seed geometries
    pub seeds: Vec<Vec<f64>>,
    /// Cluster labels
    pub clusters: Vec<usize>,
    /// Activity history
    pub history: Vec<super::memory::ActivityRecord>,
    /// Supervisor snapshot
    pub supervisor: HashMap<String, f64>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kernel_default() {
        let kernel = PhosphorosKernel::default();
        assert_eq!(kernel.seed_count(), 0);
    }

    #[test]
    fn test_add_seed() {
        let mut kernel = PhosphorosKernel::default();
        let geometry = kernel.add_seed_phrase("test phrase", false);
        assert_eq!(geometry.len(), 5);
        assert_eq!(kernel.seed_count(), 1);
    }

    #[test]
    fn test_clustering() {
        let mut kernel = PhosphorosKernel::default();

        // Add some seeds
        for i in 0..10 {
            kernel.add_seed_phrase(&format!("seed {i}"), false);
        }

        let labels = kernel.cluster();
        assert_eq!(labels.len(), 10);
    }

    #[test]
    fn test_tick() {
        let mut kernel = PhosphorosKernel::default();
        kernel.add_seed_phrase("test", false);
        kernel.tick();

        let snapshot = kernel.supervisor.snapshot();
        assert!(snapshot.contains_key("n_seeds"));
        assert_eq!(snapshot.get("n_seeds"), Some(&1.0));
    }
}
