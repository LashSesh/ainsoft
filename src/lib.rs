//! # AinSOFT Research Framework
//!
//! A universal research framework for Web3 resonance networks and mesh topology analysis.
//!
//! This crate provides tools for:
//! - **Core resonance systems**: Oscillators, feedback loops, and adaptive thresholds
//! - **Web3 integration**: Phantom wallet simulation, seed phrase geometry encoding
//! - **Mesh topology**: N-dimensional point clouds, Delaunay triangulation, kNN graphs
//! - **Network probing**: Signal analysis and response observation
//! - **Network resonance**: Spectral calibration with precision timing (Shaolin needle method)
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
//!
//! // Build mesh from points (convert geometry to Vec<f64>)
//! let points: Vec<Vec<f64>> = vec![geometry.as_slice().to_vec()];
//! let mesh = MeshLayer::new(points, Default::default());
//! ```

pub mod config;
pub mod core;
pub mod mesh;
pub mod phantomload;
pub mod resonance;
pub mod scan;
pub mod web3;

// Re-export commonly used types
pub use config::Config;
pub use core::{Feedback, Oscillator, Threshold};
pub use mesh::{MeshBuilder, MeshLayer, PointCloud};
pub use phantomload::{GhostRpcManager, PhantomCell, PhantomCellManager};
pub use resonance::{
    HarmonicScheduler, NeedleEmitter, ResonanceCalibrator, SpectralAnalyzer,
};
pub use web3::{MutationEngine, PhosphorosKernel, SeedClusterEngine, SeedDnaEngine};

/// Framework version
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// Default tick interval in seconds
pub const DEFAULT_TICK_INTERVAL: f64 = 0.017;

/// Number of dimensions for geometry vectors
pub const GEOMETRY_DIMENSIONS: usize = 5;
