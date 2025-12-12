//! Memory and state management for Web3 research.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, VecDeque};

/// Activity record for supervisor interface.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityRecord {
    /// Record data
    pub data: HashMap<String, f64>,
    /// Timestamp
    pub timestamp: f64,
}

impl ActivityRecord {
    /// Create a new activity record.
    pub fn new(data: HashMap<String, f64>) -> Self {
        Self {
            data,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        }
    }

    /// Get a value from the record.
    pub fn get(&self, key: &str) -> Option<f64> {
        self.data.get(key).copied()
    }
}

/// Stores aggregated activity data for visualization or dashboards.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SupervisorInterface {
    /// Current state
    state: HashMap<String, f64>,
}

impl SupervisorInterface {
    /// Create a new supervisor interface.
    pub fn new() -> Self {
        Self::default()
    }

    /// Update the state with new activity data.
    pub fn update(&mut self, activity: HashMap<String, f64>) {
        self.state.extend(activity);
    }

    /// Update a single value.
    pub fn set(&mut self, key: impl Into<String>, value: f64) {
        self.state.insert(key.into(), value);
    }

    /// Get a snapshot of the current state.
    pub fn snapshot(&self) -> HashMap<String, f64> {
        self.state.clone()
    }

    /// Get a specific value.
    pub fn get(&self, key: &str) -> Option<f64> {
        self.state.get(key).copied()
    }

    /// Clear all state.
    pub fn clear(&mut self) {
        self.state.clear();
    }
}

/// Keeps a bounded history of activity snapshots.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct MetaMemoryCore {
    /// Maximum history size
    max_history: Option<usize>,
    /// History of records
    history: VecDeque<ActivityRecord>,
}

impl MetaMemoryCore {
    /// Create a new memory core with optional maximum history.
    pub fn new(max_history: Option<usize>) -> Self {
        Self {
            max_history,
            history: VecDeque::new(),
        }
    }

    /// Create with a maximum history size.
    pub fn with_max_history(max: usize) -> Self {
        Self::new(Some(max))
    }

    /// Store a new record.
    pub fn store(&mut self, record: HashMap<String, f64>) {
        if let Some(max) = self.max_history {
            while self.history.len() >= max {
                self.history.pop_front();
            }
        }
        self.history.push_back(ActivityRecord::new(record));
    }

    /// Get the full history.
    pub fn get_history(&self) -> Vec<ActivityRecord> {
        self.history.iter().cloned().collect()
    }

    /// Get the latest record.
    pub fn latest(&self) -> Option<&ActivityRecord> {
        self.history.back()
    }

    /// Get history length.
    pub fn len(&self) -> usize {
        self.history.len()
    }

    /// Check if history is empty.
    pub fn is_empty(&self) -> bool {
        self.history.is_empty()
    }

    /// Clear all history.
    pub fn clear(&mut self) {
        self.history.clear();
    }

    /// Get aggregated statistics over history.
    pub fn aggregate(&self, key: &str) -> Option<AggregateStats> {
        let values: Vec<f64> = self.history.iter().filter_map(|r| r.get(key)).collect();

        if values.is_empty() {
            return None;
        }

        let sum: f64 = values.iter().sum();
        let mean = sum / values.len() as f64;
        let min = values.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        let max = values.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
        let variance = if values.len() > 1 {
            values.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / (values.len() - 1) as f64
        } else {
            0.0
        };

        Some(AggregateStats {
            count: values.len(),
            sum,
            mean,
            min,
            max,
            std_dev: variance.sqrt(),
        })
    }
}

/// Aggregate statistics for a key.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggregateStats {
    pub count: usize,
    pub sum: f64,
    pub mean: f64,
    pub min: f64,
    pub max: f64,
    pub std_dev: f64,
}

/// Lightweight activity log for building heatmaps.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ReverbRing {
    /// Activity log entries
    activity_log: Vec<ActivityRecord>,
    /// Maximum log size
    max_size: Option<usize>,
}

impl ReverbRing {
    /// Create a new reverb ring.
    pub fn new() -> Self {
        Self::default()
    }

    /// Create with a maximum size.
    pub fn with_max_size(max: usize) -> Self {
        Self {
            activity_log: Vec::new(),
            max_size: Some(max),
        }
    }

    /// Log an activity.
    pub fn log(&mut self, activity: HashMap<String, f64>) {
        if let Some(max) = self.max_size {
            if self.activity_log.len() >= max {
                self.activity_log.remove(0);
            }
        }
        self.activity_log.push(ActivityRecord::new(activity));
    }

    /// Get the heatmap data.
    pub fn get_heatmap(&self) -> Vec<HashMap<String, f64>> {
        self.activity_log.iter().map(|r| r.data.clone()).collect()
    }

    /// Get log length.
    pub fn len(&self) -> usize {
        self.activity_log.len()
    }

    /// Check if log is empty.
    pub fn is_empty(&self) -> bool {
        self.activity_log.is_empty()
    }

    /// Clear the log.
    pub fn clear(&mut self) {
        self.activity_log.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_supervisor_interface() {
        let mut sup = SupervisorInterface::new();
        sup.set("key1", 1.0);
        sup.set("key2", 2.0);

        assert_eq!(sup.get("key1"), Some(1.0));
        assert_eq!(sup.get("key2"), Some(2.0));
        assert_eq!(sup.get("key3"), None);
    }

    #[test]
    fn test_meta_memory_bounded() {
        let mut mem = MetaMemoryCore::with_max_history(3);

        for i in 0..5 {
            let mut data = HashMap::new();
            data.insert("value".to_string(), i as f64);
            mem.store(data);
        }

        assert_eq!(mem.len(), 3);
        // Should contain only last 3 values
        let history = mem.get_history();
        assert_eq!(history[0].get("value"), Some(2.0));
        assert_eq!(history[2].get("value"), Some(4.0));
    }

    #[test]
    fn test_aggregate_stats() {
        let mut mem = MetaMemoryCore::new(None);

        for i in 1..=5 {
            let mut data = HashMap::new();
            data.insert("x".to_string(), i as f64);
            mem.store(data);
        }

        let stats = mem.aggregate("x").unwrap();
        assert_eq!(stats.count, 5);
        assert_eq!(stats.sum, 15.0);
        assert_eq!(stats.mean, 3.0);
        assert_eq!(stats.min, 1.0);
        assert_eq!(stats.max, 5.0);
    }

    #[test]
    fn test_reverb_ring() {
        let mut ring = ReverbRing::with_max_size(2);

        let mut data1 = HashMap::new();
        data1.insert("a".to_string(), 1.0);
        ring.log(data1);

        let mut data2 = HashMap::new();
        data2.insert("a".to_string(), 2.0);
        ring.log(data2);

        let mut data3 = HashMap::new();
        data3.insert("a".to_string(), 3.0);
        ring.log(data3);

        assert_eq!(ring.len(), 2);
        let heatmap = ring.get_heatmap();
        assert_eq!(heatmap[0].get("a"), Some(&2.0));
        assert_eq!(heatmap[1].get("a"), Some(&3.0));
    }
}
