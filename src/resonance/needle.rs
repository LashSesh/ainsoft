//! Precision needle probes for network resonance research.
//!
//! Needles are minimal, precisely-timed network probes designed to gather
//! maximum information with minimum footprint - like acupuncture for networks.

use rand::Rng;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

/// Type of needle probe for different resonance measurements.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum NeedleType {
    /// Single-byte timing probe - measures pure latency
    #[default]
    Whisper,
    /// Minimal HTTP HEAD request
    Touch,
    /// TCP SYN timing measurement
    Pulse,
    /// DNS resolution timing
    Echo,
    /// TLS handshake timing
    Cipher,
    /// Custom payload probe
    Custom,
}

impl NeedleType {
    /// Get the typical payload size for this needle type.
    pub fn payload_size(&self) -> usize {
        match self {
            NeedleType::Whisper => 1,
            NeedleType::Touch => 0,  // HEAD request, no body
            NeedleType::Pulse => 0,  // SYN packet
            NeedleType::Echo => 32,  // DNS query
            NeedleType::Cipher => 0, // TLS handshake
            NeedleType::Custom => 64,
        }
    }

    /// Get the expected response time range (min, max) in milliseconds.
    pub fn expected_latency_range(&self) -> (f64, f64) {
        match self {
            NeedleType::Whisper => (0.5, 50.0),
            NeedleType::Touch => (1.0, 100.0),
            NeedleType::Pulse => (0.1, 30.0),
            NeedleType::Echo => (1.0, 200.0),
            NeedleType::Cipher => (5.0, 500.0),
            NeedleType::Custom => (1.0, 1000.0),
        }
    }
}

/// A precision needle probe.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Needle {
    /// Unique needle identifier
    pub id: u64,
    /// Needle type
    pub needle_type: NeedleType,
    /// Target endpoint
    pub target: String,
    /// Emission timestamp (high precision)
    pub emitted_at: f64,
    /// Response timestamp (filled on return)
    pub returned_at: Option<f64>,
    /// Payload fingerprint (for correlation)
    pub fingerprint: u32,
    /// Sequence in the harmonic pattern
    pub harmonic_seq: u32,
    /// Phase offset (0.0 - 1.0) within timing window
    pub phase: f64,
    /// Optional metadata
    pub metadata: HashMap<String, String>,
}

impl Needle {
    /// Create a new needle.
    pub fn new(id: u64, needle_type: NeedleType, target: impl Into<String>) -> Self {
        let mut rng = rand::thread_rng();
        Self {
            id,
            needle_type,
            target: target.into(),
            emitted_at: Self::now(),
            returned_at: None,
            fingerprint: rng.gen(),
            harmonic_seq: 0,
            phase: 0.0,
            metadata: HashMap::new(),
        }
    }

    /// Set harmonic sequence and phase.
    pub fn with_harmonic(mut self, seq: u32, phase: f64) -> Self {
        self.harmonic_seq = seq;
        self.phase = phase.clamp(0.0, 1.0);
        self
    }

    /// Add metadata.
    pub fn with_metadata(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metadata.insert(key.into(), value.into());
        self
    }

    /// Mark the needle as returned.
    pub fn mark_returned(&mut self) {
        self.returned_at = Some(Self::now());
    }

    /// Get round-trip time in milliseconds.
    pub fn rtt_ms(&self) -> Option<f64> {
        self.returned_at.map(|r| (r - self.emitted_at) * 1000.0)
    }

    /// Check if RTT is within expected range for this needle type.
    pub fn is_normal(&self) -> Option<bool> {
        let rtt = self.rtt_ms()?;
        let (min, max) = self.needle_type.expected_latency_range();
        Some(rtt >= min && rtt <= max)
    }

    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0)
    }
}

/// Configuration for needle emission.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeedleConfig {
    /// Default needle type
    pub needle_type: NeedleType,
    /// Minimum interval between needles (microseconds)
    pub min_interval_us: u64,
    /// Maximum jitter to add (microseconds)
    pub jitter_us: u64,
    /// Enable fingerprint correlation
    pub correlate: bool,
    /// Maximum needles in flight
    pub max_in_flight: usize,
    /// Timeout for needle return (milliseconds)
    pub timeout_ms: u64,
}

impl Default for NeedleConfig {
    fn default() -> Self {
        Self {
            needle_type: NeedleType::Whisper,
            min_interval_us: 10_000, // 10ms minimum
            jitter_us: 5_000,        // 5ms jitter
            correlate: true,
            max_in_flight: 16,
            timeout_ms: 5000,
        }
    }
}

/// Precision needle emitter for network resonance research.
#[derive(Debug)]
pub struct NeedleEmitter {
    config: NeedleConfig,
    targets: Vec<String>,
    sequence: u64,
    in_flight: HashMap<u64, Needle>,
    completed: Vec<Needle>,
    last_emission: Option<Instant>,
    total_emitted: u64,
    total_returned: u64,
    total_lost: u64,
}

impl Default for NeedleEmitter {
    fn default() -> Self {
        Self::new(NeedleConfig::default())
    }
}

impl NeedleEmitter {
    /// Create a new needle emitter.
    pub fn new(config: NeedleConfig) -> Self {
        Self {
            config,
            targets: Vec::new(),
            sequence: 0,
            in_flight: HashMap::new(),
            completed: Vec::new(),
            last_emission: None,
            total_emitted: 0,
            total_returned: 0,
            total_lost: 0,
        }
    }

    /// Add a target endpoint.
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

    /// Check if we can emit a needle (respecting timing constraints).
    pub fn can_emit(&self) -> bool {
        if self.targets.is_empty() {
            return false;
        }
        if self.in_flight.len() >= self.config.max_in_flight {
            return false;
        }
        if let Some(last) = self.last_emission {
            let elapsed_us = last.elapsed().as_micros() as u64;
            if elapsed_us < self.config.min_interval_us {
                return false;
            }
        }
        true
    }

    /// Get the delay until next emission is allowed (microseconds).
    pub fn delay_until_next_us(&self) -> u64 {
        if let Some(last) = self.last_emission {
            let elapsed_us = last.elapsed().as_micros() as u64;
            if elapsed_us < self.config.min_interval_us {
                return self.config.min_interval_us - elapsed_us;
            }
        }
        0
    }

    /// Emit a needle to a specific target with harmonic timing.
    pub fn emit_to(&mut self, target: &str, harmonic_seq: u32, phase: f64) -> Option<Needle> {
        if !self.can_emit() {
            return None;
        }

        self.sequence += 1;
        let needle = Needle::new(self.sequence, self.config.needle_type, target)
            .with_harmonic(harmonic_seq, phase);

        self.in_flight.insert(needle.id, needle.clone());
        self.last_emission = Some(Instant::now());
        self.total_emitted += 1;

        Some(needle)
    }

    /// Emit a needle to the next target in sequence.
    pub fn emit_next(&mut self, harmonic_seq: u32, phase: f64) -> Option<Needle> {
        if self.targets.is_empty() {
            return None;
        }
        let idx = (self.sequence as usize) % self.targets.len();
        let target = self.targets[idx].clone();
        self.emit_to(&target, harmonic_seq, phase)
    }

    /// Record a needle return by ID.
    pub fn record_return(&mut self, id: u64) -> Option<Needle> {
        if let Some(mut needle) = self.in_flight.remove(&id) {
            needle.mark_returned();
            self.total_returned += 1;
            self.completed.push(needle.clone());
            Some(needle)
        } else {
            None
        }
    }

    /// Record a needle return by fingerprint.
    pub fn record_return_by_fingerprint(&mut self, fingerprint: u32) -> Option<Needle> {
        let id = self.in_flight
            .iter()
            .find(|(_, n)| n.fingerprint == fingerprint)
            .map(|(id, _)| *id)?;
        self.record_return(id)
    }

    /// Check for timed-out needles.
    pub fn collect_timeouts(&mut self) -> Vec<Needle> {
        let now = Needle::now();
        let timeout_secs = self.config.timeout_ms as f64 / 1000.0;

        let timed_out: Vec<u64> = self.in_flight
            .iter()
            .filter(|(_, n)| now - n.emitted_at > timeout_secs)
            .map(|(id, _)| *id)
            .collect();

        let mut result = Vec::new();
        for id in timed_out {
            if let Some(needle) = self.in_flight.remove(&id) {
                self.total_lost += 1;
                result.push(needle);
            }
        }
        result
    }

    /// Get statistics.
    pub fn stats(&self) -> NeedleStats {
        let rtts: Vec<f64> = self.completed
            .iter()
            .filter_map(|n| n.rtt_ms())
            .collect();

        let mean_rtt = if rtts.is_empty() {
            0.0
        } else {
            rtts.iter().sum::<f64>() / rtts.len() as f64
        };

        let std_dev = if rtts.len() < 2 {
            0.0
        } else {
            let variance = rtts.iter()
                .map(|r| (r - mean_rtt).powi(2))
                .sum::<f64>() / (rtts.len() - 1) as f64;
            variance.sqrt()
        };

        let min_rtt = rtts.iter().cloned().fold(f64::INFINITY, f64::min);
        let max_rtt = rtts.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        NeedleStats {
            total_emitted: self.total_emitted,
            total_returned: self.total_returned,
            total_lost: self.total_lost,
            in_flight: self.in_flight.len() as u64,
            mean_rtt_ms: mean_rtt,
            std_dev_ms: std_dev,
            min_rtt_ms: if min_rtt.is_finite() { min_rtt } else { 0.0 },
            max_rtt_ms: if max_rtt.is_finite() { max_rtt } else { 0.0 },
            return_rate: if self.total_emitted > 0 {
                self.total_returned as f64 / self.total_emitted as f64
            } else {
                0.0
            },
        }
    }

    /// Get completed needles.
    pub fn completed(&self) -> &[Needle] {
        &self.completed
    }

    /// Clear completed needles.
    pub fn clear_completed(&mut self) {
        self.completed.clear();
    }

    /// Reset the emitter.
    pub fn reset(&mut self) {
        self.sequence = 0;
        self.in_flight.clear();
        self.completed.clear();
        self.last_emission = None;
        self.total_emitted = 0;
        self.total_returned = 0;
        self.total_lost = 0;
    }
}

/// Statistics from needle emissions.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NeedleStats {
    pub total_emitted: u64,
    pub total_returned: u64,
    pub total_lost: u64,
    pub in_flight: u64,
    pub mean_rtt_ms: f64,
    pub std_dev_ms: f64,
    pub min_rtt_ms: f64,
    pub max_rtt_ms: f64,
    pub return_rate: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_needle_creation() {
        let needle = Needle::new(1, NeedleType::Whisper, "localhost")
            .with_harmonic(5, 0.25);

        assert_eq!(needle.id, 1);
        assert_eq!(needle.harmonic_seq, 5);
        assert!((needle.phase - 0.25).abs() < 0.001);
        assert!(needle.returned_at.is_none());
    }

    #[test]
    fn test_needle_rtt() {
        let mut needle = Needle::new(1, NeedleType::Whisper, "localhost");
        assert!(needle.rtt_ms().is_none());

        needle.mark_returned();
        let rtt = needle.rtt_ms().unwrap();
        assert!(rtt >= 0.0);
    }

    #[test]
    fn test_emitter_basic() {
        let mut emitter = NeedleEmitter::default();
        emitter.add_target("target1");
        emitter.add_target("target2");

        assert!(emitter.can_emit());

        let needle = emitter.emit_next(0, 0.0);
        assert!(needle.is_some());

        let stats = emitter.stats();
        assert_eq!(stats.total_emitted, 1);
    }

    #[test]
    fn test_needle_types() {
        assert_eq!(NeedleType::Whisper.payload_size(), 1);
        assert_eq!(NeedleType::Touch.payload_size(), 0);

        let (min, max) = NeedleType::Pulse.expected_latency_range();
        assert!(min < max);
    }
}
