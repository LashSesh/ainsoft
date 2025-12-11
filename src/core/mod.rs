//! Core resonance system components.
//!
//! This module provides the fundamental building blocks for resonance-based
//! signal processing and adaptive feedback systems.

mod feedback;
mod impulse;
mod network;
mod oscillator;
mod substrate;
mod threshold;

pub use feedback::{Feedback, FeedbackLoop, FeedbackSink};
pub use impulse::{Impulse, ImpulseGenerator};
pub use network::{create_socket_with_proxy, ProxyConfig};
pub use oscillator::Oscillator;
pub use substrate::{Substrate, SubstrateLayer};
pub use threshold::{AdaptiveThreshold, Threshold, ThresholdConfig};
