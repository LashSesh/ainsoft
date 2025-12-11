//! Probe packet generation for network research.

use rand::Rng;
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

/// Pattern for probe generation.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum ProbePattern {
    /// Sequential probing
    #[default]
    Sequential,
    /// Random probing
    Random,
    /// Burst pattern
    Burst,
    /// Exponential backoff
    Exponential,
}

/// A probe packet for network research.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProbePacket {
    /// Unique probe ID
    pub id: u64,
    /// Target identifier
    pub target: String,
    /// Probe payload (simulated)
    pub payload: Vec<u8>,
    /// Timestamp
    pub timestamp: f64,
    /// Sequence number
    pub sequence: u64,
    /// TTL (time to live)
    pub ttl: u8,
}

impl ProbePacket {
    /// Create a new probe packet.
    pub fn new(id: u64, target: impl Into<String>, sequence: u64) -> Self {
        Self {
            id,
            target: target.into(),
            payload: Vec::new(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
            sequence,
            ttl: 64,
        }
    }

    /// Set payload.
    pub fn with_payload(mut self, payload: Vec<u8>) -> Self {
        self.payload = payload;
        self
    }

    /// Set TTL.
    pub fn with_ttl(mut self, ttl: u8) -> Self {
        self.ttl = ttl;
        self
    }

    /// Generate a random payload.
    pub fn with_random_payload(mut self, size: usize) -> Self {
        let mut rng = rand::thread_rng();
        self.payload = (0..size).map(|_| rng.gen()).collect();
        self
    }
}

/// Probe emitter configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmitterConfig {
    /// Probe pattern
    pub pattern: ProbePattern,
    /// Interval between probes (seconds)
    pub interval: f64,
    /// Batch size for burst pattern
    pub batch_size: usize,
    /// Default payload size
    pub payload_size: usize,
    /// Default TTL
    pub ttl: u8,
}

impl Default for EmitterConfig {
    fn default() -> Self {
        Self {
            pattern: ProbePattern::Sequential,
            interval: 0.1,
            batch_size: 10,
            payload_size: 64,
            ttl: 64,
        }
    }
}

/// Generates probe packets for network research.
#[derive(Debug, Clone)]
pub struct ProbeEmitter {
    /// Configuration
    config: EmitterConfig,
    /// Targets to probe
    targets: Vec<String>,
    /// Current target index
    current_target: usize,
    /// Sequence counter
    sequence: u64,
    /// Total probes emitted
    pub total_emitted: u64,
    /// Last emission time
    last_emission: f64,
}

impl Default for ProbeEmitter {
    fn default() -> Self {
        Self::new(EmitterConfig::default())
    }
}

impl ProbeEmitter {
    /// Create a new emitter.
    pub fn new(config: EmitterConfig) -> Self {
        Self {
            config,
            targets: Vec::new(),
            current_target: 0,
            sequence: 0,
            total_emitted: 0,
            last_emission: 0.0,
        }
    }

    /// Add a target.
    pub fn add_target(&mut self, target: impl Into<String>) {
        self.targets.push(target.into());
    }

    /// Add multiple targets.
    pub fn add_targets<I, S>(&mut self, targets: I)
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        for target in targets {
            self.targets.push(target.into());
        }
    }

    /// Emit the next probe.
    pub fn emit(&mut self) -> Option<ProbePacket> {
        if self.targets.is_empty() {
            return None;
        }

        let target = match self.config.pattern {
            ProbePattern::Sequential => {
                let t = &self.targets[self.current_target];
                self.current_target = (self.current_target + 1) % self.targets.len();
                t.clone()
            }
            ProbePattern::Random => {
                let mut rng = rand::thread_rng();
                let idx = rng.gen_range(0..self.targets.len());
                self.targets[idx].clone()
            }
            ProbePattern::Burst | ProbePattern::Exponential => {
                self.targets[self.current_target].clone()
            }
        };

        self.sequence += 1;
        self.total_emitted += 1;
        self.last_emission = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);

        Some(
            ProbePacket::new(self.sequence, target, self.sequence)
                .with_random_payload(self.config.payload_size)
                .with_ttl(self.config.ttl),
        )
    }

    /// Emit a batch of probes.
    pub fn emit_batch(&mut self) -> Vec<ProbePacket> {
        let count = match self.config.pattern {
            ProbePattern::Burst => self.config.batch_size,
            _ => 1,
        };

        (0..count).filter_map(|_| self.emit()).collect()
    }

    /// Get the next emission delay based on pattern.
    pub fn next_delay(&self) -> f64 {
        match self.config.pattern {
            ProbePattern::Sequential | ProbePattern::Random => self.config.interval,
            ProbePattern::Burst => self.config.interval * self.config.batch_size as f64,
            ProbePattern::Exponential => {
                let backoff = 2.0_f64.powf((self.sequence % 10) as f64);
                self.config.interval * backoff.min(60.0)
            }
        }
    }

    /// Reset the emitter.
    pub fn reset(&mut self) {
        self.current_target = 0;
        self.sequence = 0;
        self.total_emitted = 0;
    }

    /// Get target count.
    pub fn target_count(&self) -> usize {
        self.targets.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_probe_packet() {
        let packet = ProbePacket::new(1, "localhost", 1)
            .with_random_payload(32)
            .with_ttl(128);

        assert_eq!(packet.id, 1);
        assert_eq!(packet.payload.len(), 32);
        assert_eq!(packet.ttl, 128);
    }

    #[test]
    fn test_emitter_sequential() {
        let mut emitter = ProbeEmitter::new(EmitterConfig {
            pattern: ProbePattern::Sequential,
            ..Default::default()
        });

        emitter.add_targets(["a", "b", "c"]);

        let p1 = emitter.emit().unwrap();
        let p2 = emitter.emit().unwrap();
        let p3 = emitter.emit().unwrap();
        let p4 = emitter.emit().unwrap();

        assert_eq!(p1.target, "a");
        assert_eq!(p2.target, "b");
        assert_eq!(p3.target, "c");
        assert_eq!(p4.target, "a"); // Wrap around
    }

    #[test]
    fn test_emitter_burst() {
        let mut emitter = ProbeEmitter::new(EmitterConfig {
            pattern: ProbePattern::Burst,
            batch_size: 5,
            ..Default::default()
        });

        emitter.add_target("target");
        let batch = emitter.emit_batch();

        assert_eq!(batch.len(), 5);
    }
}
