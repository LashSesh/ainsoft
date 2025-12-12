//! N-dimensional point cloud representation.

use nalgebra::DVector;
use serde::{Deserialize, Serialize};

/// An N-dimensional point cloud.
#[derive(Debug, Clone)]
pub struct PointCloud {
    /// Points in the cloud
    points: Vec<DVector<f64>>,
    /// Number of dimensions
    pub dimensions: usize,
}

impl Default for PointCloud {
    fn default() -> Self {
        Self::new(5) // Default to 5D
    }
}

impl PointCloud {
    /// Create a new empty point cloud.
    pub fn new(dimensions: usize) -> Self {
        Self {
            points: Vec::new(),
            dimensions,
        }
    }

    /// Create from existing points.
    pub fn from_points(points: Vec<Vec<f64>>) -> Self {
        let dimensions = points.first().map(|p| p.len()).unwrap_or(5);
        let converted: Vec<DVector<f64>> = points.into_iter().map(DVector::from_vec).collect();

        Self {
            points: converted,
            dimensions,
        }
    }

    /// Create from DVector points.
    pub fn from_dvectors(points: Vec<DVector<f64>>) -> Self {
        let dimensions = points.first().map(|p| p.len()).unwrap_or(5);
        Self { points, dimensions }
    }

    /// Add a point to the cloud.
    pub fn add(&mut self, point: impl Into<Vec<f64>>) {
        let vec: Vec<f64> = point.into();
        self.points.push(DVector::from_vec(vec));
    }

    /// Add a DVector point.
    pub fn add_dvector(&mut self, point: DVector<f64>) {
        self.points.push(point);
    }

    /// Get the number of points.
    pub fn len(&self) -> usize {
        self.points.len()
    }

    /// Check if the cloud is empty.
    pub fn is_empty(&self) -> bool {
        self.points.is_empty()
    }

    /// Get a point by index.
    pub fn get(&self, index: usize) -> Option<&DVector<f64>> {
        self.points.get(index)
    }

    /// Get a mutable reference to a point.
    pub fn get_mut(&mut self, index: usize) -> Option<&mut DVector<f64>> {
        self.points.get_mut(index)
    }

    /// Get all points as slice.
    pub fn points(&self) -> &[DVector<f64>] {
        &self.points
    }

    /// Get all points as mutable slice.
    pub fn points_mut(&mut self) -> &mut [DVector<f64>] {
        &mut self.points
    }

    /// Convert to 2D array representation.
    pub fn to_array(&self) -> Vec<Vec<f64>> {
        self.points.iter().map(|p| p.as_slice().to_vec()).collect()
    }

    /// Calculate centroid of all points.
    pub fn centroid(&self) -> Option<DVector<f64>> {
        if self.is_empty() {
            return None;
        }

        let mut sum = DVector::zeros(self.dimensions);
        for point in &self.points {
            sum += point;
        }
        Some(sum / self.len() as f64)
    }

    /// Calculate bounding box (min, max for each dimension).
    pub fn bounding_box(&self) -> Option<(DVector<f64>, DVector<f64>)> {
        if self.is_empty() {
            return None;
        }

        let mut min = self.points[0].clone();
        let mut max = self.points[0].clone();

        for point in &self.points[1..] {
            for i in 0..self.dimensions.min(point.len()) {
                if point[i] < min[i] {
                    min[i] = point[i];
                }
                if point[i] > max[i] {
                    max[i] = point[i];
                }
            }
        }

        Some((min, max))
    }

    /// Normalize all points to [0, 1] range.
    pub fn normalize(&mut self) {
        if let Some((min, max)) = self.bounding_box() {
            let range = &max - &min;
            for point in &mut self.points {
                for i in 0..self.dimensions.min(point.len()) {
                    if range[i] > 1e-9 {
                        point[i] = (point[i] - min[i]) / range[i];
                    } else {
                        point[i] = 0.5;
                    }
                }
            }
        }
    }

    /// Calculate distance between two points.
    pub fn distance(&self, i: usize, j: usize) -> Option<f64> {
        let p1 = self.get(i)?;
        let p2 = self.get(j)?;
        Some((p1 - p2).norm())
    }

    /// Find k nearest neighbors for a point.
    pub fn k_nearest(&self, point_idx: usize, k: usize) -> Vec<(usize, f64)> {
        if point_idx >= self.len() {
            return vec![];
        }

        let point = &self.points[point_idx];
        let mut distances: Vec<(usize, f64)> = self
            .points
            .iter()
            .enumerate()
            .filter(|(i, _)| *i != point_idx)
            .map(|(i, p)| (i, (point - p).norm()))
            .collect();

        distances.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
        distances.truncate(k);
        distances
    }

    /// Clear all points.
    pub fn clear(&mut self) {
        self.points.clear();
    }

    /// Iterate over points.
    pub fn iter(&self) -> impl Iterator<Item = &DVector<f64>> {
        self.points.iter()
    }
}

impl IntoIterator for PointCloud {
    type Item = DVector<f64>;
    type IntoIter = std::vec::IntoIter<Self::Item>;

    fn into_iter(self) -> Self::IntoIter {
        self.points.into_iter()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_point_cloud_creation() {
        let mut cloud = PointCloud::new(3);
        cloud.add(vec![1.0, 2.0, 3.0]);
        cloud.add(vec![4.0, 5.0, 6.0]);

        assert_eq!(cloud.len(), 2);
        assert_eq!(cloud.dimensions, 3);
    }

    #[test]
    fn test_centroid() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![2.0, 0.0],
            vec![0.0, 2.0],
            vec![2.0, 2.0],
        ]);

        let centroid = cloud.centroid().unwrap();
        assert!((centroid[0] - 1.0).abs() < 1e-9);
        assert!((centroid[1] - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_k_nearest() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
            vec![10.0, 0.0],
        ]);

        let nearest = cloud.k_nearest(0, 2);
        assert_eq!(nearest.len(), 2);
        assert_eq!(nearest[0].0, 1); // Closest is point 1
        assert_eq!(nearest[1].0, 2); // Second closest is point 2
    }

    #[test]
    fn test_bounding_box() {
        let cloud = PointCloud::from_points(vec![vec![1.0, 2.0], vec![3.0, 4.0], vec![0.0, 5.0]]);

        let (min, max) = cloud.bounding_box().unwrap();
        assert_eq!(min[0], 0.0);
        assert_eq!(min[1], 2.0);
        assert_eq!(max[0], 3.0);
        assert_eq!(max[1], 5.0);
    }
}
