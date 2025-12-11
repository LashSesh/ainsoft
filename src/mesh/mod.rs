//! Mesh topology and triangulation workflows.
//!
//! This module provides tools for building and analyzing N-dimensional
//! point clouds and meshes for research visualization.

mod builder;
mod entropy;
mod layer;
mod operators;
mod point_cloud;
mod topology;

pub use builder::{MeshBuilder, MeshMode};
pub use entropy::EntropyControl;
pub use layer::{MeshLayer, MeshLayerConfig};
pub use operators::{coagula, expand, gate, solve, OperatorRegistry};
pub use point_cloud::PointCloud;
pub use topology::TopologyGuard;
