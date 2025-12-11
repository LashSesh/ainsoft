//! Network scanning and signal analysis for research.
//!
//! This module provides tools for network probing and response analysis
//! in a research context.

mod analyzer;
mod emitter;
mod observer;

pub use analyzer::{SignalAnalyzer, SignalMetrics};
pub use emitter::{ProbeEmitter, ProbePacket, ProbePattern};
pub use observer::{ResponseObserver, ResponseRecord, ResponseStatus};
