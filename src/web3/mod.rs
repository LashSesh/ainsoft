//! Web3 research utilities for AinSOFT.
//!
//! This module provides tools for Web3/blockchain research including:
//! - Seed phrase geometry encoding
//! - Mutation and variant generation
//! - Cluster analysis
//! - Phantom wallet simulation support

mod bridge;
mod cluster;
mod dna;
mod export;
mod memory;
mod mutation;

pub mod kernel;

pub use bridge::ScorpioBridge;
pub use cluster::SeedClusterEngine;
pub use dna::SeedDnaEngine;
pub use export::ExportModule;
pub use kernel::{KernelConfig, PhosphorosKernel};
pub use memory::{MetaMemoryCore, ReverbRing, SupervisorInterface};
pub use mutation::MutationEngine;
