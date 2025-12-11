//! Phantom RPC simulation for Web3 research.
//!
//! This module provides tools for simulating phantom wallet and RPC node
//! behavior for blockchain research purposes.

mod cell;
mod ghost_rpc;
mod heatmap;
mod proxy;
mod supervisor;

pub mod kernel;

pub use cell::{PhantomCell, PhantomCellManager};
pub use ghost_rpc::{GhostRpcManager, GhostRpcNode, GhostRpcWave};
pub use heatmap::PhantomHeatmap;
pub use kernel::{PhantomloadConfig, PhantomloadKernel};
pub use proxy::ProxyManager;
pub use supervisor::PhantomSupervisor;
