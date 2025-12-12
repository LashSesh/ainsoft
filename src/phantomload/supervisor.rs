//! Supervisor for phantomload activities.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

/// Event type for supervisor logging.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EventType {
    /// Wave started
    WaveStart,
    /// Wave stopped
    WaveStop,
    /// Cell spawned
    CellSpawn,
    /// Cell removed
    CellRemove,
    /// Error occurred
    Error,
    /// General activity
    Activity,
}

/// A supervisor event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupervisorEvent {
    /// Event type
    pub event_type: EventType,
    /// Event message
    pub message: String,
    /// Associated data
    pub data: HashMap<String, serde_json::Value>,
    /// Timestamp
    pub timestamp: f64,
}

impl SupervisorEvent {
    /// Create a new event.
    pub fn new(event_type: EventType, message: impl Into<String>) -> Self {
        Self {
            event_type,
            message: message.into(),
            data: HashMap::new(),
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
        }
    }

    /// Add data to the event.
    pub fn with_data(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.data.insert(key.into(), value);
        self
    }
}

/// Supervisor for monitoring phantomload activities.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PhantomSupervisor {
    /// Event log
    events: Vec<SupervisorEvent>,
    /// Maximum log size
    max_events: usize,
    /// Current metrics
    metrics: HashMap<String, f64>,
}

impl PhantomSupervisor {
    /// Create a new supervisor.
    pub fn new(max_events: usize) -> Self {
        Self {
            events: Vec::new(),
            max_events,
            metrics: HashMap::new(),
        }
    }

    /// Log an event.
    pub fn log(&mut self, event: SupervisorEvent) {
        if self.events.len() >= self.max_events {
            self.events.remove(0);
        }
        self.events.push(event);
    }

    /// Log a wave start.
    pub fn log_wave_start(&mut self, wave_id: &str, node_count: usize) {
        let event = SupervisorEvent::new(EventType::WaveStart, format!("Wave {wave_id} started"))
            .with_data("wave_id", serde_json::json!(wave_id))
            .with_data("node_count", serde_json::json!(node_count));
        self.log(event);
    }

    /// Log a wave stop.
    pub fn log_wave_stop(&mut self, wave_id: &str, total_requests: u64) {
        let event = SupervisorEvent::new(EventType::WaveStop, format!("Wave {wave_id} stopped"))
            .with_data("wave_id", serde_json::json!(wave_id))
            .with_data("total_requests", serde_json::json!(total_requests));
        self.log(event);
    }

    /// Log cell spawn.
    pub fn log_cell_spawn(&mut self, cell_id: &str) {
        let event = SupervisorEvent::new(EventType::CellSpawn, format!("Cell {cell_id} spawned"))
            .with_data("cell_id", serde_json::json!(cell_id));
        self.log(event);
    }

    /// Log an error.
    pub fn log_error(&mut self, message: impl Into<String>) {
        let event = SupervisorEvent::new(EventType::Error, message);
        self.log(event);
    }

    /// Update a metric.
    pub fn update_metric(&mut self, key: impl Into<String>, value: f64) {
        self.metrics.insert(key.into(), value);
    }

    /// Increment a metric.
    pub fn increment_metric(&mut self, key: impl Into<String>, delta: f64) {
        let key = key.into();
        let current = self.metrics.get(&key).copied().unwrap_or(0.0);
        self.metrics.insert(key, current + delta);
    }

    /// Get a metric value.
    pub fn get_metric(&self, key: &str) -> Option<f64> {
        self.metrics.get(key).copied()
    }

    /// Get all metrics.
    pub fn metrics(&self) -> &HashMap<String, f64> {
        &self.metrics
    }

    /// Get recent events.
    pub fn recent_events(&self, count: usize) -> &[SupervisorEvent] {
        let start = self.events.len().saturating_sub(count);
        &self.events[start..]
    }

    /// Get all events.
    pub fn events(&self) -> &[SupervisorEvent] {
        &self.events
    }

    /// Get event count.
    pub fn event_count(&self) -> usize {
        self.events.len()
    }

    /// Clear all events.
    pub fn clear_events(&mut self) {
        self.events.clear();
    }

    /// Get a summary snapshot.
    pub fn snapshot(&self) -> HashMap<String, serde_json::Value> {
        let mut data = HashMap::new();
        data.insert(
            "event_count".to_string(),
            serde_json::json!(self.events.len()),
        );
        data.insert("metrics".to_string(), serde_json::json!(self.metrics));
        data.insert(
            "recent_events".to_string(),
            serde_json::json!(self.recent_events(10)),
        );
        data
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_supervisor_logging() {
        let mut supervisor = PhantomSupervisor::new(100);
        supervisor.log_wave_start("wave-1", 5);
        supervisor.log_wave_stop("wave-1", 100);

        assert_eq!(supervisor.event_count(), 2);
    }

    #[test]
    fn test_metrics() {
        let mut supervisor = PhantomSupervisor::new(100);
        supervisor.update_metric("requests", 10.0);
        supervisor.increment_metric("requests", 5.0);

        assert_eq!(supervisor.get_metric("requests"), Some(15.0));
    }

    #[test]
    fn test_max_events() {
        let mut supervisor = PhantomSupervisor::new(3);

        for i in 0..5 {
            supervisor.log_wave_start(&format!("wave-{i}"), 1);
        }

        assert_eq!(supervisor.event_count(), 3);
        // Oldest events should be removed
    }
}
