//! Substrate layer for resonance propagation.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A substrate cell that can hold and propagate resonance values.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Substrate {
    /// Cell identifier
    pub id: String,
    /// Current resonance value
    pub value: f64,
    /// Propagation coefficient (how much signal passes through)
    pub conductance: f64,
    /// Decay rate per step
    pub decay: f64,
    /// Connected neighbor IDs with connection strengths
    pub neighbors: HashMap<String, f64>,
}

impl Substrate {
    /// Create a new substrate cell.
    pub fn new(id: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            value: 0.0,
            conductance: 0.8,
            decay: 0.95,
            neighbors: HashMap::new(),
        }
    }

    /// Set the conductance value.
    pub fn with_conductance(mut self, conductance: f64) -> Self {
        self.conductance = conductance.clamp(0.0, 1.0);
        self
    }

    /// Set the decay rate.
    pub fn with_decay(mut self, decay: f64) -> Self {
        self.decay = decay.clamp(0.0, 1.0);
        self
    }

    /// Add a neighbor connection.
    pub fn connect(&mut self, neighbor_id: impl Into<String>, strength: f64) {
        self.neighbors
            .insert(neighbor_id.into(), strength.clamp(0.0, 1.0));
    }

    /// Inject a signal into the substrate.
    pub fn inject(&mut self, signal: f64) {
        self.value += signal * self.conductance;
    }

    /// Step the substrate forward, applying decay.
    pub fn step(&mut self) -> f64 {
        self.value *= self.decay;
        self.value
    }

    /// Calculate the signal to propagate to neighbors.
    pub fn propagate(&self) -> HashMap<String, f64> {
        let mut signals = HashMap::new();
        for (neighbor, strength) in &self.neighbors {
            let signal = self.value * strength * self.conductance;
            signals.insert(neighbor.clone(), signal);
        }
        signals
    }

    /// Reset the substrate to zero.
    pub fn reset(&mut self) {
        self.value = 0.0;
    }
}

/// A layer of interconnected substrate cells.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SubstrateLayer {
    /// All cells in the layer
    cells: HashMap<String, Substrate>,
    /// Global dampening factor
    pub dampening: f64,
}

impl SubstrateLayer {
    /// Create a new substrate layer.
    pub fn new() -> Self {
        Self {
            cells: HashMap::new(),
            dampening: 0.9,
        }
    }

    /// Add a cell to the layer.
    pub fn add_cell(&mut self, cell: Substrate) {
        self.cells.insert(cell.id.clone(), cell);
    }

    /// Get a cell by ID.
    pub fn get(&self, id: &str) -> Option<&Substrate> {
        self.cells.get(id)
    }

    /// Get a mutable reference to a cell.
    pub fn get_mut(&mut self, id: &str) -> Option<&mut Substrate> {
        self.cells.get_mut(id)
    }

    /// Inject a signal into a specific cell.
    pub fn inject(&mut self, cell_id: &str, signal: f64) {
        if let Some(cell) = self.cells.get_mut(cell_id) {
            cell.inject(signal);
        }
    }

    /// Step all cells and propagate signals.
    pub fn step(&mut self) {
        // Collect all propagation signals
        let mut all_signals: HashMap<String, f64> = HashMap::new();
        for cell in self.cells.values() {
            for (target, signal) in cell.propagate() {
                *all_signals.entry(target).or_insert(0.0) += signal;
            }
        }

        // Apply decay to all cells
        for cell in self.cells.values_mut() {
            cell.step();
        }

        // Apply propagated signals
        for (target, signal) in all_signals {
            if let Some(cell) = self.cells.get_mut(&target) {
                cell.inject(signal * self.dampening);
            }
        }
    }

    /// Get the total energy in the layer.
    pub fn total_energy(&self) -> f64 {
        self.cells.values().map(|c| c.value.abs()).sum()
    }

    /// Get the number of cells.
    pub fn cell_count(&self) -> usize {
        self.cells.len()
    }

    /// Reset all cells.
    pub fn reset(&mut self) {
        for cell in self.cells.values_mut() {
            cell.reset();
        }
    }

    /// Create a ring topology with n cells.
    pub fn create_ring(n: usize, conductance: f64, decay: f64) -> Self {
        let mut layer = Self::new();

        for i in 0..n {
            let mut cell = Substrate::new(format!("cell-{i}"))
                .with_conductance(conductance)
                .with_decay(decay);

            // Connect to neighbors in ring
            let prev = format!("cell-{}", (i + n - 1) % n);
            let next = format!("cell-{}", (i + 1) % n);
            cell.connect(prev, 0.5);
            cell.connect(next, 0.5);

            layer.add_cell(cell);
        }

        layer
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_substrate_inject() {
        let mut sub = Substrate::new("test").with_conductance(0.5);
        sub.inject(1.0);
        assert!((sub.value - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_substrate_decay() {
        let mut sub = Substrate::new("test").with_decay(0.5);
        sub.value = 1.0;
        sub.step();
        assert!((sub.value - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_layer_ring() {
        let layer = SubstrateLayer::create_ring(4, 0.8, 0.9);
        assert_eq!(layer.cell_count(), 4);
    }
}
