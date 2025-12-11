//! Feedback mechanisms for resonance systems.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

/// A feedback entry containing a signal value and metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Feedback {
    /// The feedback value
    pub value: f64,
    /// Source identifier
    pub source: String,
    /// Timestamp (epoch seconds)
    pub timestamp: f64,
    /// Optional metadata
    #[serde(default)]
    pub metadata: std::collections::HashMap<String, serde_json::Value>,
}

impl Feedback {
    /// Create a new feedback entry.
    pub fn new(value: f64, source: impl Into<String>) -> Self {
        Self {
            value,
            source: source.into(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs_f64())
                .unwrap_or(0.0),
            metadata: Default::default(),
        }
    }

    /// Add metadata to the feedback.
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

/// Thread-safe feedback sink for collecting feedback entries.
#[derive(Debug, Clone, Default)]
pub struct FeedbackSink {
    buffer: Arc<Mutex<VecDeque<Feedback>>>,
    max_size: usize,
}

impl FeedbackSink {
    /// Create a new feedback sink with specified capacity.
    pub fn new(max_size: usize) -> Self {
        Self {
            buffer: Arc::new(Mutex::new(VecDeque::with_capacity(max_size))),
            max_size,
        }
    }

    /// Push a feedback entry to the sink.
    pub fn push(&self, feedback: Feedback) {
        let mut buffer = self.buffer.lock().unwrap();
        if buffer.len() >= self.max_size {
            buffer.pop_front();
        }
        buffer.push_back(feedback);
    }

    /// Collect all feedback entries, clearing the buffer.
    pub fn collect(&self) -> Vec<Feedback> {
        let mut buffer = self.buffer.lock().unwrap();
        buffer.drain(..).collect()
    }

    /// Peek at the latest feedback without removing it.
    pub fn peek_latest(&self) -> Option<Feedback> {
        let buffer = self.buffer.lock().unwrap();
        buffer.back().cloned()
    }

    /// Get the number of pending feedback entries.
    pub fn len(&self) -> usize {
        self.buffer.lock().unwrap().len()
    }

    /// Check if the sink is empty.
    pub fn is_empty(&self) -> bool {
        self.buffer.lock().unwrap().is_empty()
    }
}

/// Feedback loop with dampening and smoothing.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeedbackLoop {
    /// Dampening factor (0.0 to 1.0)
    pub dampen: f64,
    /// Current accumulated value
    pub current: f64,
    /// Target value
    pub target: f64,
    /// Smoothing factor for exponential moving average
    pub smoothing: f64,
}

impl Default for FeedbackLoop {
    fn default() -> Self {
        Self {
            dampen: 0.95,
            current: 0.0,
            target: 0.0,
            smoothing: 0.1,
        }
    }
}

impl FeedbackLoop {
    /// Create a new feedback loop with custom parameters.
    pub fn new(dampen: f64, smoothing: f64) -> Self {
        Self {
            dampen: dampen.clamp(0.0, 1.0),
            current: 0.0,
            target: 0.0,
            smoothing: smoothing.clamp(0.0, 1.0),
        }
    }

    /// Set a new target value.
    pub fn set_target(&mut self, target: f64) {
        self.target = target;
    }

    /// Step the feedback loop forward.
    pub fn step(&mut self) -> f64 {
        // Exponential smoothing towards target
        self.current = self.current * (1.0 - self.smoothing) + self.target * self.smoothing;
        // Apply dampening
        self.current *= self.dampen;
        self.current
    }

    /// Step with an external signal injection.
    pub fn step_with_signal(&mut self, signal: f64) -> f64 {
        self.target = signal;
        self.step()
    }

    /// Reset the feedback loop.
    pub fn reset(&mut self) {
        self.current = 0.0;
        self.target = 0.0;
    }

    /// Check if the loop has converged (current ≈ target).
    pub fn has_converged(&self, epsilon: f64) -> bool {
        (self.current - self.target).abs() < epsilon
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_feedback_sink() {
        let sink = FeedbackSink::new(3);
        sink.push(Feedback::new(0.1, "a"));
        sink.push(Feedback::new(0.2, "b"));
        sink.push(Feedback::new(0.3, "c"));
        sink.push(Feedback::new(0.4, "d")); // Should evict first

        let collected = sink.collect();
        assert_eq!(collected.len(), 3);
        assert_eq!(collected[0].source, "b");
    }

    #[test]
    fn test_feedback_loop_convergence() {
        let mut fbl = FeedbackLoop::new(1.0, 0.5);
        fbl.set_target(1.0);

        for _ in 0..20 {
            fbl.step();
        }

        assert!(fbl.has_converged(0.01));
    }
}
