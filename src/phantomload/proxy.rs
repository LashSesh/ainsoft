//! Proxy rotation manager for RPC requests.

use rand::seq::SliceRandom;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A proxy endpoint.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proxy {
    /// Proxy host
    pub host: String,
    /// Proxy port
    pub port: u16,
    /// Protocol (socks5, http)
    pub protocol: String,
    /// Optional username
    pub username: Option<String>,
    /// Optional password
    pub password: Option<String>,
    /// Whether this proxy is active
    pub active: bool,
    /// Success count
    pub successes: u64,
    /// Failure count
    pub failures: u64,
}

impl Proxy {
    /// Create a new proxy.
    pub fn new(host: impl Into<String>, port: u16, protocol: impl Into<String>) -> Self {
        Self {
            host: host.into(),
            port,
            protocol: protocol.into(),
            username: None,
            password: None,
            active: true,
            successes: 0,
            failures: 0,
        }
    }

    /// Add authentication credentials.
    pub fn with_auth(mut self, username: impl Into<String>, password: impl Into<String>) -> Self {
        self.username = Some(username.into());
        self.password = Some(password.into());
        self
    }

    /// Get the proxy URL.
    pub fn url(&self) -> String {
        match (&self.username, &self.password) {
            (Some(u), Some(p)) => {
                format!("{}://{}:{}@{}:{}", self.protocol, u, p, self.host, self.port)
            }
            _ => format!("{}://{}:{}", self.protocol, self.host, self.port),
        }
    }

    /// Record a success.
    pub fn record_success(&mut self) {
        self.successes += 1;
    }

    /// Record a failure.
    pub fn record_failure(&mut self) {
        self.failures += 1;
        // Deactivate if too many failures
        if self.failures > 10 && self.success_rate() < 0.5 {
            self.active = false;
        }
    }

    /// Get success rate.
    pub fn success_rate(&self) -> f64 {
        let total = self.successes + self.failures;
        if total == 0 {
            return 1.0;
        }
        self.successes as f64 / total as f64
    }
}

/// Manages a pool of proxies with rotation.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProxyManager {
    /// Available proxies
    proxies: Vec<Proxy>,
    /// Current proxy index
    current_index: usize,
    /// Rotation strategy
    pub strategy: RotationStrategy,
}

/// Proxy rotation strategy.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum RotationStrategy {
    /// Round-robin through proxies
    #[default]
    RoundRobin,
    /// Random selection
    Random,
    /// Weighted by success rate
    Weighted,
    /// Use single proxy (no rotation)
    Sticky,
}

impl ProxyManager {
    /// Create a new proxy manager.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create with initial proxies.
    pub fn with_proxies(proxies: Vec<Proxy>) -> Self {
        Self {
            proxies,
            current_index: 0,
            strategy: RotationStrategy::RoundRobin,
        }
    }

    /// Add a proxy.
    pub fn add(&mut self, proxy: Proxy) {
        self.proxies.push(proxy);
    }

    /// Get the next proxy according to the rotation strategy.
    pub fn next(&mut self) -> Option<&Proxy> {
        let active: Vec<usize> = self
            .proxies
            .iter()
            .enumerate()
            .filter(|(_, p)| p.active)
            .map(|(i, _)| i)
            .collect();

        if active.is_empty() {
            return None;
        }

        let idx = match self.strategy {
            RotationStrategy::RoundRobin => {
                let idx = active
                    .iter()
                    .position(|&i| i >= self.current_index)
                    .unwrap_or(0);
                self.current_index = (active[idx] + 1) % self.proxies.len();
                active[idx]
            }
            RotationStrategy::Random => {
                let mut rng = rand::thread_rng();
                *active.choose(&mut rng).unwrap()
            }
            RotationStrategy::Weighted => {
                // Weight by success rate
                let weights: Vec<f64> = active
                    .iter()
                    .map(|&i| self.proxies[i].success_rate())
                    .collect();
                let total: f64 = weights.iter().sum();

                if total < 1e-9 {
                    active[0]
                } else {
                    let mut rng = rand::thread_rng();
                    let threshold: f64 = rand::Rng::gen(&mut rng);
                    let mut cumsum = 0.0;
                    let mut selected = active[0];

                    for (&i, &w) in active.iter().zip(weights.iter()) {
                        cumsum += w / total;
                        if cumsum >= threshold {
                            selected = i;
                            break;
                        }
                    }
                    selected
                }
            }
            RotationStrategy::Sticky => active[0],
        };

        self.proxies.get(idx)
    }

    /// Get a mutable reference to a proxy by index.
    pub fn get_mut(&mut self, index: usize) -> Option<&mut Proxy> {
        self.proxies.get_mut(index)
    }

    /// Get proxy count.
    pub fn count(&self) -> usize {
        self.proxies.len()
    }

    /// Get active proxy count.
    pub fn active_count(&self) -> usize {
        self.proxies.iter().filter(|p| p.active).count()
    }

    /// Get a snapshot of the manager state.
    pub fn snapshot(&self) -> HashMap<String, serde_json::Value> {
        let mut data = HashMap::new();
        data.insert("total".to_string(), serde_json::json!(self.count()));
        data.insert("active".to_string(), serde_json::json!(self.active_count()));
        data.insert("strategy".to_string(), serde_json::json!(format!("{:?}", self.strategy)));
        data.insert(
            "proxies".to_string(),
            serde_json::json!(
                self.proxies
                    .iter()
                    .map(|p| {
                        serde_json::json!({
                            "host": p.host,
                            "port": p.port,
                            "active": p.active,
                            "success_rate": p.success_rate()
                        })
                    })
                    .collect::<Vec<_>>()
            ),
        );
        data
    }

    /// Reset all proxy statistics.
    pub fn reset_stats(&mut self) {
        for proxy in &mut self.proxies {
            proxy.successes = 0;
            proxy.failures = 0;
            proxy.active = true;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_proxy_url() {
        let proxy = Proxy::new("localhost", 1080, "socks5");
        assert_eq!(proxy.url(), "socks5://localhost:1080");

        let proxy_auth = proxy.with_auth("user", "pass");
        assert_eq!(proxy_auth.url(), "socks5://user:pass@localhost:1080");
    }

    #[test]
    fn test_proxy_manager_rotation() {
        let mut manager = ProxyManager::new();
        manager.add(Proxy::new("proxy1", 1080, "socks5"));
        manager.add(Proxy::new("proxy2", 1081, "socks5"));

        let p1 = manager.next().map(|p| p.host.clone());
        let p2 = manager.next().map(|p| p.host.clone());
        let p3 = manager.next().map(|p| p.host.clone());

        // Round robin should cycle
        assert!(p1.is_some());
        assert!(p2.is_some());
        assert_eq!(p1, p3); // Back to first
    }

    #[test]
    fn test_proxy_success_rate() {
        let mut proxy = Proxy::new("test", 1080, "socks5");
        proxy.record_success();
        proxy.record_success();
        proxy.record_failure();

        assert!((proxy.success_rate() - 0.666).abs() < 0.01);
    }
}
