//! High-level kernel for phantomload operations.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

use super::{
    GhostRpcManager, GhostRpcNode, PhantomCellManager, PhantomHeatmap, PhantomSupervisor,
    ProxyManager,
};
use crate::web3::ExportModule;

/// Configuration for phantomload kernel.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhantomloadConfig {
    /// Heatmap width
    pub heatmap_width: usize,
    /// Heatmap height
    pub heatmap_height: usize,
    /// Heatmap decay rate
    pub heatmap_decay: f64,
    /// Maximum supervisor events
    pub max_events: usize,
    /// Scale factor for position normalization
    pub position_scale: f64,
    /// Export directory
    pub export_path: Option<PathBuf>,
}

impl Default for PhantomloadConfig {
    fn default() -> Self {
        Self {
            heatmap_width: 100,
            heatmap_height: 100,
            heatmap_decay: 0.95,
            max_events: 1000,
            position_scale: 65535.0, // 16-bit max
            export_path: None,
        }
    }
}

/// High-level kernel orchestrating phantomload operations.
pub struct PhantomloadKernel {
    /// RPC manager
    pub rpc_manager: GhostRpcManager,
    /// Cell manager
    pub cell_manager: PhantomCellManager,
    /// Activity heatmap
    pub heatmap: PhantomHeatmap,
    /// Supervisor
    pub supervisor: PhantomSupervisor,
    /// Export module
    pub export: ExportModule,
    /// Configuration
    config: PhantomloadConfig,
    /// Tick counter
    tick_count: u64,
}

impl std::fmt::Debug for PhantomloadKernel {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PhantomloadKernel")
            .field("tick_count", &self.tick_count)
            .field("cell_count", &self.cell_manager.cell_count())
            .field("config", &self.config)
            .finish()
    }
}

impl Default for PhantomloadKernel {
    fn default() -> Self {
        Self::with_config(PhantomloadConfig::default())
    }
}

impl PhantomloadKernel {
    /// Create a kernel with custom configuration.
    pub fn with_config(config: PhantomloadConfig) -> Self {
        let heatmap =
            PhantomHeatmap::new(config.heatmap_width, config.heatmap_height, config.heatmap_decay);
        let supervisor = PhantomSupervisor::new(config.max_events);
        let export = match &config.export_path {
            Some(path) => ExportModule::new(path),
            None => ExportModule::default(),
        };

        Self {
            rpc_manager: GhostRpcManager::default(),
            cell_manager: PhantomCellManager::default(),
            heatmap,
            supervisor,
            export,
            config,
            tick_count: 0,
        }
    }

    /// Add proxies to the RPC manager.
    pub fn add_proxies(&mut self, proxies: Vec<(String, u16, String)>) {
        for (host, port, protocol) in proxies {
            self.rpc_manager.proxy_manager.add(
                super::proxy::Proxy::new(host, port, protocol)
            );
        }
    }

    /// Spawn phantom cells.
    pub fn spawn_cells(&mut self, count: usize, base_phrase: &str, mutate: bool) -> Vec<String> {
        let ids = self.cell_manager.spawn_cells(count, base_phrase, mutate);
        for id in &ids {
            self.supervisor.log_cell_spawn(id);
        }
        self.supervisor.update_metric("cell_count", self.cell_manager.cell_count() as f64);
        ids
    }

    /// Start an RPC wave.
    pub fn start_wave(
        &mut self,
        mode: &str,
        pattern: &str,
        endpoint: &str,
    ) {
        // Create nodes from cells
        let nodes: Vec<GhostRpcNode> = self
            .cell_manager
            .iter()
            .map(|cell| {
                GhostRpcNode::new(
                    cell.cell_id.clone(),
                    endpoint,
                    cell.seed_phrase.clone(),
                )
            })
            .collect();

        let node_count = nodes.len();
        self.rpc_manager.start_wave(mode, pattern, nodes, endpoint);
        self.supervisor.log_wave_start(pattern, node_count);
    }

    /// Stop the current wave.
    pub fn stop_wave(&mut self) {
        if let Some(wave) = self.rpc_manager.active_wave() {
            let total_requests = wave.metrics.requests;
            self.supervisor.log_wave_stop(&wave.pattern, total_requests);
        }
        self.rpc_manager.stop_wave();
    }

    /// Run a single tick.
    pub fn tick(&mut self) -> Option<HashMap<String, serde_json::Value>> {
        self.tick_count += 1;

        // Tick RPC manager
        let rpc_result = self.rpc_manager.tick();

        // Update heatmap from cell positions
        for cell in self.cell_manager.iter() {
            let position = cell.position();
            let intensity = 0.1; // Base activity
            self.heatmap.add_from_position(&position, intensity, self.config.position_scale);
        }

        // Apply heatmap decay
        self.heatmap.step();

        // Update metrics
        self.supervisor.update_metric("tick_count", self.tick_count as f64);
        self.supervisor.update_metric(
            "heatmap_intensity",
            self.heatmap.total_intensity(),
        );

        rpc_result
    }

    /// Get current status.
    pub fn status(&self) -> HashMap<String, serde_json::Value> {
        let mut data = HashMap::new();
        data.insert("tick_count".to_string(), serde_json::json!(self.tick_count));
        data.insert("cell_count".to_string(), serde_json::json!(self.cell_manager.cell_count()));
        data.insert("rpc_status".to_string(), serde_json::json!(self.rpc_manager.status()));
        data.insert("supervisor".to_string(), serde_json::json!(self.supervisor.snapshot()));
        data.insert(
            "heatmap_intensity".to_string(),
            serde_json::json!(self.heatmap.total_intensity()),
        );
        data
    }

    /// Export current state.
    pub fn export_state(&self, filename: &str) -> std::io::Result<PathBuf> {
        let state = KernelExport {
            tick_count: self.tick_count,
            cell_count: self.cell_manager.cell_count(),
            mesh: self.cell_manager.to_mesh("export"),
            heatmap: self.heatmap.to_hot_spot_list(0.1),
            metrics: self.supervisor.metrics().clone(),
        };
        self.export.export_as_json(&state, filename)
    }

    /// Reset the kernel.
    pub fn reset(&mut self) {
        self.cell_manager.reset();
        self.heatmap.reset();
        self.supervisor.clear_events();
        self.tick_count = 0;
    }

    /// Get tick count.
    pub fn tick_count(&self) -> u64 {
        self.tick_count
    }
}

/// Serializable kernel state for export.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct KernelExport {
    tick_count: u64,
    cell_count: usize,
    mesh: super::cell::MeshData,
    heatmap: Vec<HashMap<String, serde_json::Value>>,
    metrics: HashMap<String, f64>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_kernel_default() {
        let kernel = PhantomloadKernel::default();
        assert_eq!(kernel.tick_count(), 0);
        assert_eq!(kernel.cell_manager.cell_count(), 0);
    }

    #[test]
    fn test_spawn_and_wave() {
        let mut kernel = PhantomloadKernel::default();

        // Spawn cells
        let ids = kernel.spawn_cells(5, "test", false);
        assert_eq!(ids.len(), 5);

        // Start wave
        kernel.start_wave("burst", "test-wave", "http://localhost:8545");

        // Tick
        let result = kernel.tick();
        assert!(result.is_some());
    }

    #[test]
    fn test_tick_updates() {
        let mut kernel = PhantomloadKernel::default();
        kernel.spawn_cells(3, "seed", true);

        for _ in 0..10 {
            kernel.tick();
        }

        assert_eq!(kernel.tick_count(), 10);
        assert!(kernel.heatmap.total_intensity() > 0.0);
    }
}
