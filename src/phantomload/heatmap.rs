//! Heatmap visualization for phantomload traffic.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A single heatmap cell.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeatmapCell {
    /// Cell coordinates
    pub x: usize,
    pub y: usize,
    /// Intensity value (0.0 to 1.0)
    pub intensity: f64,
    /// Number of samples in this cell
    pub samples: u64,
}

/// Heatmap for visualizing phantomload activity.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhantomHeatmap {
    /// Width of the heatmap grid
    pub width: usize,
    /// Height of the heatmap grid
    pub height: usize,
    /// Grid cells
    cells: Vec<Vec<HeatmapCell>>,
    /// Decay rate per update
    pub decay: f64,
}

impl Default for PhantomHeatmap {
    fn default() -> Self {
        Self::new(100, 100, 0.95)
    }
}

impl PhantomHeatmap {
    /// Create a new heatmap.
    pub fn new(width: usize, height: usize, decay: f64) -> Self {
        let cells = (0..height)
            .map(|y| {
                (0..width)
                    .map(|x| HeatmapCell {
                        x,
                        y,
                        intensity: 0.0,
                        samples: 0,
                    })
                    .collect()
            })
            .collect();

        Self {
            width,
            height,
            cells,
            decay,
        }
    }

    /// Add activity at normalized coordinates (0.0 to 1.0).
    pub fn add_activity(&mut self, norm_x: f64, norm_y: f64, intensity: f64) {
        let x = ((norm_x.clamp(0.0, 1.0) * (self.width - 1) as f64).round() as usize)
            .min(self.width - 1);
        let y = ((norm_y.clamp(0.0, 1.0) * (self.height - 1) as f64).round() as usize)
            .min(self.height - 1);

        self.cells[y][x].intensity = (self.cells[y][x].intensity + intensity).min(1.0);
        self.cells[y][x].samples += 1;
    }

    /// Add activity from a 3D position (uses first 2 dimensions).
    pub fn add_from_position(&mut self, position: &[f64], intensity: f64, scale: f64) {
        if position.len() >= 2 {
            // Normalize position to 0-1 range using scale
            let norm_x = (position[0] / scale).clamp(0.0, 1.0);
            let norm_y = (position[1] / scale).clamp(0.0, 1.0);
            self.add_activity(norm_x, norm_y, intensity);
        }
    }

    /// Apply decay to all cells.
    pub fn apply_decay(&mut self) {
        for row in &mut self.cells {
            for cell in row {
                cell.intensity *= self.decay;
            }
        }
    }

    /// Step the heatmap (apply decay and prepare for next frame).
    pub fn step(&mut self) {
        self.apply_decay();
    }

    /// Get cell at coordinates.
    pub fn get(&self, x: usize, y: usize) -> Option<&HeatmapCell> {
        self.cells.get(y).and_then(|row| row.get(x))
    }

    /// Get total intensity.
    pub fn total_intensity(&self) -> f64 {
        self.cells
            .iter()
            .flat_map(|row| row.iter())
            .map(|cell| cell.intensity)
            .sum()
    }

    /// Get average intensity.
    pub fn average_intensity(&self) -> f64 {
        let total = self.width * self.height;
        if total == 0 {
            return 0.0;
        }
        self.total_intensity() / total as f64
    }

    /// Get cells above a threshold.
    pub fn hot_spots(&self, threshold: f64) -> Vec<&HeatmapCell> {
        self.cells
            .iter()
            .flat_map(|row| row.iter())
            .filter(|cell| cell.intensity >= threshold)
            .collect()
    }

    /// Export as a 2D array of intensities.
    pub fn to_array(&self) -> Vec<Vec<f64>> {
        self.cells
            .iter()
            .map(|row| row.iter().map(|cell| cell.intensity).collect())
            .collect()
    }

    /// Export as a flat list of hot spots.
    pub fn to_hot_spot_list(&self, threshold: f64) -> Vec<HashMap<String, serde_json::Value>> {
        self.hot_spots(threshold)
            .iter()
            .map(|cell| {
                let mut data = HashMap::new();
                data.insert("x".to_string(), serde_json::json!(cell.x));
                data.insert("y".to_string(), serde_json::json!(cell.y));
                data.insert("intensity".to_string(), serde_json::json!(cell.intensity));
                data.insert("samples".to_string(), serde_json::json!(cell.samples));
                data
            })
            .collect()
    }

    /// Reset the heatmap.
    pub fn reset(&mut self) {
        for row in &mut self.cells {
            for cell in row {
                cell.intensity = 0.0;
                cell.samples = 0;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_heatmap_creation() {
        let heatmap = PhantomHeatmap::new(10, 10, 0.9);
        assert_eq!(heatmap.width, 10);
        assert_eq!(heatmap.height, 10);
        assert_eq!(heatmap.total_intensity(), 0.0);
    }

    #[test]
    fn test_add_activity() {
        let mut heatmap = PhantomHeatmap::new(10, 10, 0.9);
        heatmap.add_activity(0.5, 0.5, 1.0);

        let cell = heatmap.get(5, 5).unwrap();
        assert_eq!(cell.intensity, 1.0);
        assert_eq!(cell.samples, 1);
    }

    #[test]
    fn test_decay() {
        let mut heatmap = PhantomHeatmap::new(10, 10, 0.5);
        heatmap.add_activity(0.5, 0.5, 1.0);
        heatmap.apply_decay();

        let cell = heatmap.get(5, 5).unwrap();
        assert!((cell.intensity - 0.5).abs() < 1e-9);
    }

    #[test]
    fn test_hot_spots() {
        let mut heatmap = PhantomHeatmap::new(10, 10, 0.9);
        heatmap.add_activity(0.1, 0.1, 0.8);
        heatmap.add_activity(0.9, 0.9, 0.3);

        let hot_spots = heatmap.hot_spots(0.5);
        assert_eq!(hot_spots.len(), 1);
    }
}
