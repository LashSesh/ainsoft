//! # AinSOFT Research Framework
//!
//! A universal research framework for Web3 resonance networks and mesh topology analysis.
//!
//! This crate provides tools for:
//! - **Core resonance systems**: Oscillators, feedback loops, and adaptive thresholds
//! - **Web3 integration**: Phantom wallet simulation, seed phrase geometry encoding
//! - **Mesh topology**: N-dimensional point clouds, Delaunay triangulation, kNN graphs
//! - **Network probing**: Signal analysis and response observation
//!
//! ## Example
//!
//! ```rust,no_run
//! use ainsoft::web3::SeedDnaEngine;
//! use ainsoft::mesh::MeshLayer;
//!
//! // Encode seed phrases to 5D geometry
//! let engine = SeedDnaEngine::default();
//! let geometry = engine.encode("example seed phrase");
//! let geometry = geometry.as_slice().to_vec();
//!
//! // Build mesh from points
//! let points = vec![geometry];
//! let mesh = MeshLayer::new(points, Default::default());
//! ```

pub mod config;
pub mod core;
pub mod mesh;
pub mod phantomload;
pub mod pipeline;
pub mod scan;
pub mod web3;

// Re-export commonly used types
pub use config::Config;
pub use core::{Feedback, Oscillator, Threshold};
pub use mesh::{MeshBuilder, MeshLayer, PointCloud};
pub use phantomload::{GhostRpcManager, PhantomCell, PhantomCellManager};
pub use pipeline::{
    fixpunkt_from_config, orchestrator_from_config, FixpunktAttraktorEngine, FixpunktCandidate,
    PipelineDocument, PipelineOrchestrator, PipelineRegistry,
};
pub use web3::{MutationEngine, PhosphorosKernel, SeedClusterEngine, SeedDnaEngine};

/// Framework version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default tick interval in seconds
pub const DEFAULT_TICK_INTERVAL: f64 = 0.017;

/// Number of dimensions for geometry vectors
pub const GEOMETRY_DIMENSIONS: usize = 5;
