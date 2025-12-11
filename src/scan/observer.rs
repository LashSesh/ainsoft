//! Response observation and collection.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

use super::ProbePacket;

/// A recorded response to a probe.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResponseRecord {
    /// Original probe ID
    pub probe_id: u64,
    /// Target that responded
    pub target: String,
    /// Response latency (seconds)
    pub latency: f64,
    /// Response size (bytes)
    pub size: usize,
    /// Response status
    pub status: ResponseStatus,
    /// Additional data
    pub data: HashMap<String, serde_json::Value>,
    /// Timestamp
    pub timestamp: f64,
}

/// Response status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ResponseStatus {
    /// Successful response
    Success,
    /// Timeout
    Timeout,
    /// Error
    Error,
    /// Filtered/dropped
    Filtered,
    /// Unknown
    Unknown,
}

impl ResponseRecord {
    /// Create a success record.
    pub fn success(probe_id: u64, target: impl Into<String>, latency: f64, size: usize) -> Self {
        Self {
            probe_id,
            target: target.into(),
            latency,
            size,
            status: ResponseStatus::Success,
            data: HashMap::new(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        }
    }

    /// Create a timeout record.
    pub fn timeout(probe_id: u64, target: impl Into<String>) -> Self {
        Self {
            probe_id,
            target: target.into(),
            latency: 0.0,
            size: 0,
            status: ResponseStatus::Timeout,
            data: HashMap::new(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        }
    }

    /// Create an error record.
    pub fn error(probe_id: u64, target: impl Into<String>, message: impl Into<String>) -> Self {
        let mut data = HashMap::new();
        data.insert("error".to_string(), serde_json::json!(message.into()));

        Self {
            probe_id,
            target: target.into(),
            latency: 0.0,
            size: 0,
            status: ResponseStatus::Error,
            data,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        }
    }

    /// Add metadata.
    pub fn with_data(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.data.insert(key.into(), value);
        self
    }

    /// Check if successful.
    pub fn is_success(&self) -> bool {
        self.status == ResponseStatus::Success
    }
}

/// Observer for collecting and managing responses.
#[derive(Debug, Clone, Default)]
pub struct ResponseObserver {
    /// Response records
    records: VecDeque<ResponseRecord>,
    /// Maximum records to keep
    max_records: usize,
    /// Per-target statistics
    target_stats: HashMap<String, TargetStats>,
    /// Pending probes (waiting for response)
    pending: HashMap<u64, PendingProbe>,
    /// Timeout threshold (seconds)
    pub timeout: f64,
}

/// Statistics for a target.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TargetStats {
    /// Total probes sent
    pub total_probes: u64,
    /// Successful responses
    pub successes: u64,
    /// Timeouts
    pub timeouts: u64,
    /// Errors
    pub errors: u64,
    /// Average latency
    pub avg_latency: f64,
    /// Min latency
    pub min_latency: f64,
    /// Max latency
    pub max_latency: f64,
}

impl TargetStats {
    /// Update with a new response.
    pub fn update(&mut self, response: &ResponseRecord) {
        self.total_probes += 1;

        match response.status {
            ResponseStatus::Success => {
                self.successes += 1;
                let n = self.successes;
                self.avg_latency =
                    self.avg_latency * ((n - 1) as f64 / n as f64) + response.latency / n as f64;
                if self.min_latency == 0.0 || response.latency < self.min_latency {
                    self.min_latency = response.latency;
                }
                if response.latency > self.max_latency {
                    self.max_latency = response.latency;
                }
            }
            ResponseStatus::Timeout => self.timeouts += 1,
            ResponseStatus::Error | ResponseStatus::Filtered => self.errors += 1,
            ResponseStatus::Unknown => {}
        }
    }

    /// Get success rate.
    pub fn success_rate(&self) -> f64 {
        if self.total_probes == 0 {
            return 0.0;
        }
        self.successes as f64 / self.total_probes as f64
    }
}

/// A pending probe waiting for response.
#[derive(Debug, Clone)]
struct PendingProbe {
    target: String,
    sent_at: f64,
}

impl ResponseObserver {
    /// Create a new observer.
    pub fn new(max_records: usize, timeout: f64) -> Self {
        Self {
            records: VecDeque::with_capacity(max_records),
            max_records,
            target_stats: HashMap::new(),
            pending: HashMap::new(),
            timeout,
        }
    }

    /// Register a sent probe.
    pub fn register_probe(&mut self, probe: &ProbePacket) {
        self.pending.insert(
            probe.id,
            PendingProbe {
                target: probe.target.clone(),
                sent_at: probe.timestamp,
            },
        );
    }

    /// Record a response.
    pub fn record(&mut self, response: ResponseRecord) {
        // Update target stats
        let stats = self
            .target_stats
            .entry(response.target.clone())
            .or_default();
        stats.update(&response);

        // Remove from pending
        self.pending.remove(&response.probe_id);

        // Add to records
        if self.records.len() >= self.max_records {
            self.records.pop_front();
        }
        self.records.push_back(response);
    }

    /// Check for timed out probes.
    pub fn check_timeouts(&mut self) -> Vec<ResponseRecord> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs_f64())
            .unwrap_or(0.0);

        let timed_out: Vec<_> = self
            .pending
            .iter()
            .filter(|(_, p)| now - p.sent_at > self.timeout)
            .map(|(&id, p)| (id, p.target.clone()))
            .collect();

        let mut records = Vec::new();
        for (id, target) in timed_out {
            let response = ResponseRecord::timeout(id, &target);
            records.push(response.clone());
            self.record(response);
        }

        records
    }

    /// Get recent records.
    pub fn recent(&self, count: usize) -> Vec<&ResponseRecord> {
        self.records.iter().rev().take(count).collect()
    }

    /// Get all records.
    pub fn all_records(&self) -> &VecDeque<ResponseRecord> {
        &self.records
    }

    /// Get statistics for a target.
    pub fn stats_for(&self, target: &str) -> Option<&TargetStats> {
        self.target_stats.get(target)
    }

    /// Get all target statistics.
    pub fn all_stats(&self) -> &HashMap<String, TargetStats> {
        &self.target_stats
    }

    /// Get total record count.
    pub fn record_count(&self) -> usize {
        self.records.len()
    }

    /// Get pending probe count.
    pub fn pending_count(&self) -> usize {
        self.pending.len()
    }

    /// Clear all records.
    pub fn clear(&mut self) {
        self.records.clear();
        self.target_stats.clear();
        self.pending.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_response_record() {
        let record = ResponseRecord::success(1, "localhost", 0.05, 64);
        assert!(record.is_success());
        assert_eq!(record.latency, 0.05);
    }

    #[test]
    fn test_observer_recording() {
        let mut observer = ResponseObserver::new(100, 5.0);

        observer.record(ResponseRecord::success(1, "target1", 0.01, 64));
        observer.record(ResponseRecord::success(2, "target1", 0.02, 64));
        observer.record(ResponseRecord::timeout(3, "target1"));

        let stats = observer.stats_for("target1").unwrap();
        assert_eq!(stats.total_probes, 3);
        assert_eq!(stats.successes, 2);
        assert_eq!(stats.timeouts, 1);
    }

    #[test]
    fn test_target_stats_update() {
        let mut stats = TargetStats::default();

        stats.update(&ResponseRecord::success(1, "t", 0.1, 64));
        stats.update(&ResponseRecord::success(2, "t", 0.2, 64));

        assert_eq!(stats.successes, 2);
        assert!((stats.avg_latency - 0.15).abs() < 0.01);
        assert_eq!(stats.min_latency, 0.1);
        assert_eq!(stats.max_latency, 0.2);
    }
}
