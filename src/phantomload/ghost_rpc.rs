//! GhostRPC engine for synthetic phantomload traffic simulation.

use rand::Rng;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use super::ProxyManager;

/// Represents a transient phantom RPC node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GhostRpcNode {
    /// Node identifier
    pub node_id: String,
    /// RPC endpoint URL
    pub endpoint: String,
    /// Associated seed phrase
    pub seed: String,
    /// Additional metadata
    pub metadata: HashMap<String, serde_json::Value>,
    /// Whether the node is active
    pub active: bool,
    /// Last recorded latency
    pub last_latency: f64,
    /// Total requests sent
    pub requests_sent: u64,
}

impl GhostRpcNode {
    /// Create a new ghost RPC node.
    pub fn new(
        node_id: impl Into<String>,
        endpoint: impl Into<String>,
        seed: impl Into<String>,
    ) -> Self {
        Self {
            node_id: node_id.into(),
            endpoint: endpoint.into(),
            seed: seed.into(),
            metadata: HashMap::new(),
            active: true,
            last_latency: 0.0,
            requests_sent: 0,
        }
    }

    /// Set metadata.
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }

    /// Get a snapshot of the node state.
    pub fn snapshot(&self) -> HashMap<String, serde_json::Value> {
        let mut data = self.metadata.clone();
        data.insert("id".to_string(), serde_json::json!(self.node_id));
        data.insert("endpoint".to_string(), serde_json::json!(self.endpoint));
        data.insert("seed".to_string(), serde_json::json!(self.seed));
        data.insert("active".to_string(), serde_json::json!(self.active));
        data.insert(
            "last_latency".to_string(),
            serde_json::json!(self.last_latency),
        );
        data.insert(
            "requests_sent".to_string(),
            serde_json::json!(self.requests_sent),
        );
        data
    }

    /// Simulate a request to the node.
    pub fn simulate_request(&mut self) -> f64 {
        if !self.active {
            return 0.0;
        }

        let mut rng = rand::thread_rng();
        let latency: f64 = rng.gen_range(0.01..0.3);
        let jitter: f64 = rng.gen_range(-0.005..0.005);
        self.last_latency = (latency + jitter).max(0.0);
        self.requests_sent += 1;
        self.last_latency
    }

    /// Deactivate the node.
    pub fn deactivate(&mut self) {
        self.active = false;
    }

    /// Activate the node.
    pub fn activate(&mut self) {
        self.active = true;
    }
}

/// Metrics for an RPC wave.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct WaveMetrics {
    /// Total requests made
    pub requests: u64,
    /// Total errors encountered
    pub errors: u64,
    /// Average latency
    pub avg_latency: f64,
    /// Min latency
    pub min_latency: f64,
    /// Max latency
    pub max_latency: f64,
}

impl WaveMetrics {
    /// Update metrics with new latency values.
    pub fn update(&mut self, latencies: &[f64]) {
        if latencies.is_empty() {
            return;
        }

        self.requests += latencies.len() as u64;
        let sum: f64 = latencies.iter().sum();
        self.avg_latency = sum / latencies.len() as f64;

        for &lat in latencies {
            if self.min_latency == 0.0 || lat < self.min_latency {
                self.min_latency = lat;
            }
            if lat > self.max_latency {
                self.max_latency = lat;
            }
        }
    }
}

/// Active phantomload wave description.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GhostRpcWave {
    /// Wave mode (e.g., "burst", "steady", "random")
    pub mode: String,
    /// Pattern identifier
    pub pattern: String,
    /// Nodes in the wave
    pub nodes: Vec<GhostRpcNode>,
    /// Target endpoint
    pub endpoint: String,
    /// Start timestamp
    pub started_at: f64,
    /// Current status
    pub status: String,
    /// Aggregate metrics
    pub metrics: WaveMetrics,
}

impl GhostRpcWave {
    /// Create a new wave.
    pub fn new(
        mode: impl Into<String>,
        pattern: impl Into<String>,
        nodes: Vec<GhostRpcNode>,
        endpoint: impl Into<String>,
    ) -> Self {
        Self {
            mode: mode.into(),
            pattern: pattern.into(),
            nodes,
            endpoint: endpoint.into(),
            started_at: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
            status: "running".to_string(),
            metrics: WaveMetrics::default(),
        }
    }

    /// Update metrics with new latencies.
    pub fn update_metrics(&mut self, latencies: &[f64]) {
        self.metrics.update(latencies);
    }

    /// Get a snapshot of the wave.
    pub fn snapshot(&self) -> HashMap<String, serde_json::Value> {
        let mut data = HashMap::new();
        data.insert("mode".to_string(), serde_json::json!(self.mode));
        data.insert("pattern".to_string(), serde_json::json!(self.pattern));
        data.insert("endpoint".to_string(), serde_json::json!(self.endpoint));
        data.insert("started_at".to_string(), serde_json::json!(self.started_at));
        data.insert("status".to_string(), serde_json::json!(self.status));
        data.insert("metrics".to_string(), serde_json::json!(self.metrics));
        data.insert(
            "nodes".to_string(),
            serde_json::json!(self.nodes.iter().map(|n| n.snapshot()).collect::<Vec<_>>()),
        );
        data
    }

    /// Stop the wave.
    pub fn stop(&mut self) {
        self.status = "stopped".to_string();
    }

    /// Check if the wave is running.
    pub fn is_running(&self) -> bool {
        self.status == "running"
    }
}

/// Coordinates phantom RPC waves and synthesized traffic.
#[derive(Debug, Clone)]
pub struct GhostRpcManager {
    /// Proxy manager for rotating proxies
    pub proxy_manager: ProxyManager,
    /// Current active wave
    wave: Option<GhostRpcWave>,
    /// Last tick timestamp
    last_tick: f64,
    /// Total waves executed
    total_waves: u64,
}

impl Default for GhostRpcManager {
    fn default() -> Self {
        Self::new(ProxyManager::default())
    }
}

impl GhostRpcManager {
    /// Create a new manager with a proxy manager.
    pub fn new(proxy_manager: ProxyManager) -> Self {
        Self {
            proxy_manager,
            wave: None,
            last_tick: 0.0,
            total_waves: 0,
        }
    }

    /// Start a new phantomload wave.
    pub fn start_wave(
        &mut self,
        mode: impl Into<String>,
        pattern: impl Into<String>,
        nodes: Vec<GhostRpcNode>,
        endpoint: impl Into<String>,
    ) -> &GhostRpcWave {
        let wave = GhostRpcWave::new(mode, pattern, nodes, endpoint);
        self.wave = Some(wave);
        self.total_waves += 1;
        self.last_tick = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);
        self.wave.as_ref().unwrap()
    }

    /// Stop the current wave.
    pub fn stop_wave(&mut self) {
        if let Some(ref mut wave) = self.wave {
            wave.stop();
        }
        self.wave = None;
    }

    /// Simulate a single tick of traffic.
    pub fn tick(&mut self) -> Option<HashMap<String, serde_json::Value>> {
        let wave = self.wave.as_mut()?;

        if !wave.is_running() {
            return None;
        }

        let mut latencies = Vec::new();
        for node in &mut wave.nodes {
            if node.active {
                let latency = node.simulate_request();
                latencies.push(latency);
            }
        }

        wave.update_metrics(&latencies);

        self.last_tick = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);

        let mut result = HashMap::new();
        result.insert("wave".to_string(), serde_json::json!(wave.snapshot()));
        result.insert(
            "proxy".to_string(),
            serde_json::json!(self.proxy_manager.snapshot()),
        );
        result.insert("timestamp".to_string(), serde_json::json!(self.last_tick));

        Some(result)
    }

    /// Get current status.
    pub fn status(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert("active".to_string(), serde_json::json!(self.wave.is_some()));
        result.insert(
            "wave".to_string(),
            self.wave
                .as_ref()
                .map(|w| serde_json::json!(w.snapshot()))
                .unwrap_or(serde_json::Value::Null),
        );
        result.insert(
            "proxy".to_string(),
            serde_json::json!(self.proxy_manager.snapshot()),
        );
        result.insert(
            "total_waves".to_string(),
            serde_json::json!(self.total_waves),
        );
        result
    }

    /// Get the active wave.
    pub fn active_wave(&self) -> Option<&GhostRpcWave> {
        self.wave.as_ref()
    }

    /// Get mutable reference to active wave.
    pub fn active_wave_mut(&mut self) -> Option<&mut GhostRpcWave> {
        self.wave.as_mut()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ghost_rpc_node() {
        let mut node = GhostRpcNode::new("node-1", "http://localhost:8545", "test seed");
        assert!(node.active);

        let latency = node.simulate_request();
        assert!(latency > 0.0);
        assert_eq!(node.requests_sent, 1);
    }

    #[test]
    fn test_wave_creation() {
        let nodes = vec![GhostRpcNode::new("n1", "http://localhost:8545", "seed1")];
        let wave = GhostRpcWave::new("burst", "pattern-1", nodes, "http://api.example.com");

        assert_eq!(wave.mode, "burst");
        assert!(wave.is_running());
    }

    #[test]
    fn test_manager_tick() {
        let mut manager = GhostRpcManager::default();

        let nodes = vec![
            GhostRpcNode::new("n1", "http://localhost:8545", "seed1"),
            GhostRpcNode::new("n2", "http://localhost:8546", "seed2"),
        ];

        manager.start_wave("steady", "default", nodes, "http://api.example.com");

        let result = manager.tick();
        assert!(result.is_some());

        let status = manager.status();
        assert_eq!(status.get("active"), Some(&serde_json::json!(true)));
    }
}
