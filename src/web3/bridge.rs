//! Heartbeat-driven scheduler for research callbacks.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time;

/// Callback function type for bridge ticks.
pub type TickCallback = Box<dyn Fn() + Send + Sync + 'static>;

/// Heartbeat-driven scheduler for executing callbacks.
///
/// Executes registered callbacks at a fixed interval using async runtime.
pub struct ScorpioBridge {
    /// Tick interval
    tick_interval: Duration,
    /// Running state
    running: Arc<AtomicBool>,
    /// Callback functions
    callbacks: Vec<Arc<TickCallback>>,
    /// Shutdown signal sender
    shutdown_tx: Option<mpsc::Sender<()>>,
}

impl std::fmt::Debug for ScorpioBridge {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ScorpioBridge")
            .field("tick_interval", &self.tick_interval)
            .field("running", &self.running.load(Ordering::SeqCst))
            .field("callback_count", &self.callbacks.len())
            .finish()
    }
}

impl Default for ScorpioBridge {
    fn default() -> Self {
        Self::new(Duration::from_secs_f64(0.017)) // ~60 Hz
    }
}

impl ScorpioBridge {
    /// Create a new bridge with specified tick interval.
    pub fn new(tick_interval: Duration) -> Self {
        Self {
            tick_interval,
            running: Arc::new(AtomicBool::new(false)),
            callbacks: Vec::new(),
            shutdown_tx: None,
        }
    }

    /// Create with tick interval in seconds.
    pub fn with_interval_secs(secs: f64) -> Self {
        Self::new(Duration::from_secs_f64(secs))
    }

    /// Register a callback function.
    pub fn register_callback<F>(&mut self, callback: F)
    where
        F: Fn() + Send + Sync + 'static,
    {
        self.callbacks.push(Arc::new(Box::new(callback)));
    }

    /// Check if the bridge is running.
    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }

    /// Start the heartbeat loop (async).
    pub async fn start(&mut self) {
        if self.running.load(Ordering::SeqCst) {
            return;
        }

        self.running.store(true, Ordering::SeqCst);

        let (shutdown_tx, mut shutdown_rx) = mpsc::channel::<()>(1);
        self.shutdown_tx = Some(shutdown_tx);

        let running = self.running.clone();
        let tick_interval = self.tick_interval;
        let callbacks = self.callbacks.clone();

        tokio::spawn(async move {
            let mut interval = time::interval(tick_interval);

            loop {
                tokio::select! {
                    _ = interval.tick() => {
                        if !running.load(Ordering::SeqCst) {
                            break;
                        }
                        for callback in &callbacks {
                            callback();
                        }
                    }
                    _ = shutdown_rx.recv() => {
                        break;
                    }
                }
            }
        });
    }

    /// Stop the heartbeat loop.
    pub async fn stop(&mut self) {
        self.running.store(false, Ordering::SeqCst);
        if let Some(tx) = self.shutdown_tx.take() {
            let _ = tx.send(()).await;
        }
    }

    /// Get the number of registered callbacks.
    pub fn callback_count(&self) -> usize {
        self.callbacks.len()
    }

    /// Clear all callbacks.
    pub fn clear_callbacks(&mut self) {
        self.callbacks.clear();
    }
}

/// Synchronous wrapper for running bridge callbacks once.
pub fn run_callbacks_once(callbacks: &[Arc<TickCallback>]) {
    for callback in callbacks {
        callback();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;

    #[test]
    fn test_bridge_creation() {
        let bridge = ScorpioBridge::default();
        assert!(!bridge.is_running());
        assert_eq!(bridge.callback_count(), 0);
    }

    #[test]
    fn test_callback_registration() {
        let mut bridge = ScorpioBridge::default();
        bridge.register_callback(|| {});
        bridge.register_callback(|| {});
        assert_eq!(bridge.callback_count(), 2);
    }

    #[tokio::test]
    async fn test_bridge_start_stop() {
        let counter = Arc::new(AtomicUsize::new(0));
        let counter_clone = counter.clone();

        let mut bridge = ScorpioBridge::with_interval_secs(0.01);
        bridge.register_callback(move || {
            counter_clone.fetch_add(1, Ordering::SeqCst);
        });

        bridge.start().await;
        assert!(bridge.is_running());

        tokio::time::sleep(Duration::from_millis(50)).await;

        bridge.stop().await;
        assert!(!bridge.is_running());

        // Counter should have been incremented multiple times
        assert!(counter.load(Ordering::SeqCst) > 0);
    }
}
