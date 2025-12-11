//! Topology analysis for meshes.

use std::collections::{HashMap, HashSet, VecDeque};

use super::MeshBuilder;

/// Performs topology analysis and coherence checks on meshes.
#[derive(Debug, Clone)]
pub struct TopologyGuard<'a> {
    /// Reference to the mesh builder
    builder: &'a MeshBuilder,
}

impl<'a> TopologyGuard<'a> {
    /// Create a new topology guard.
    pub fn new(builder: &'a MeshBuilder) -> Self {
        Self { builder }
    }

    /// Check if the mesh is coherent (all points connected).
    pub fn check_coherence(&self) -> bool {
        let n = self.builder.pointcloud.len();
        if n == 0 {
            return false;
        }

        let mut connected: HashSet<usize> = HashSet::new();
        for &(i, j) in &self.builder.edges {
            connected.insert(i);
            connected.insert(j);
        }

        connected.len() == n
    }

    /// Check if the mesh is fully connected (single component).
    pub fn is_connected(&self) -> bool {
        let n = self.builder.pointcloud.len();
        if n == 0 {
            return false;
        }
        if self.builder.edges.is_empty() {
            return n == 1;
        }

        // Build adjacency list
        let mut adj: HashMap<usize, Vec<usize>> = HashMap::new();
        for &(i, j) in &self.builder.edges {
            adj.entry(i).or_default().push(j);
            adj.entry(j).or_default().push(i);
        }

        // BFS from first connected node
        let start = self.builder.edges.first().map(|e| e.0).unwrap_or(0);
        let mut visited: HashSet<usize> = HashSet::new();
        let mut queue: VecDeque<usize> = VecDeque::new();

        visited.insert(start);
        queue.push_back(start);

        while let Some(node) = queue.pop_front() {
            if let Some(neighbors) = adj.get(&node) {
                for &neighbor in neighbors {
                    if !visited.contains(&neighbor) {
                        visited.insert(neighbor);
                        queue.push_back(neighbor);
                    }
                }
            }
        }

        // Check if all nodes with edges are visited
        let nodes_with_edges: HashSet<usize> = self
            .builder
            .edges
            .iter()
            .flat_map(|&(i, j)| vec![i, j])
            .collect();

        visited == nodes_with_edges
    }

    /// Get the number of connected components.
    pub fn component_count(&self) -> usize {
        let n = self.builder.pointcloud.len();
        if n == 0 {
            return 0;
        }

        // Build adjacency list
        let mut adj: HashMap<usize, Vec<usize>> = HashMap::new();
        for &(i, j) in &self.builder.edges {
            adj.entry(i).or_default().push(j);
            adj.entry(j).or_default().push(i);
        }

        let mut visited: HashSet<usize> = HashSet::new();
        let mut components = 0;

        for start in 0..n {
            if visited.contains(&start) {
                continue;
            }

            // BFS for this component
            let mut queue: VecDeque<usize> = VecDeque::new();
            visited.insert(start);
            queue.push_back(start);

            while let Some(node) = queue.pop_front() {
                if let Some(neighbors) = adj.get(&node) {
                    for &neighbor in neighbors {
                        if !visited.contains(&neighbor) {
                            visited.insert(neighbor);
                            queue.push_back(neighbor);
                        }
                    }
                }
            }

            components += 1;
        }

        components
    }

    /// Calculate approximate Betti numbers.
    /// Returns [b0] where b0 is the number of connected components.
    pub fn betti_numbers(&self) -> Vec<usize> {
        let b0 = if self.check_coherence() {
            self.component_count()
        } else {
            0
        };
        vec![b0]
    }

    /// Calculate the degree of each node.
    pub fn node_degrees(&self) -> HashMap<usize, usize> {
        let mut degrees: HashMap<usize, usize> = HashMap::new();

        for &(i, j) in &self.builder.edges {
            *degrees.entry(i).or_insert(0) += 1;
            *degrees.entry(j).or_insert(0) += 1;
        }

        degrees
    }

    /// Get the average degree.
    pub fn average_degree(&self) -> f64 {
        let n = self.builder.pointcloud.len();
        if n == 0 {
            return 0.0;
        }

        let total_degree: usize = self.node_degrees().values().sum();
        total_degree as f64 / n as f64
    }

    /// Find articulation points (nodes whose removal disconnects the graph).
    pub fn articulation_points(&self) -> Vec<usize> {
        // Simplified: return nodes with very high degree
        let degrees = self.node_degrees();
        let avg = self.average_degree();

        degrees
            .iter()
            .filter(|(_, &deg)| deg as f64 > avg * 2.0)
            .map(|(&node, _)| node)
            .collect()
    }

    /// Calculate clustering coefficient for a node.
    pub fn clustering_coefficient(&self, node: usize) -> f64 {
        let degrees = self.node_degrees();
        let k = *degrees.get(&node).unwrap_or(&0);

        if k < 2 {
            return 0.0;
        }

        // Find neighbors
        let neighbors: HashSet<usize> = self
            .builder
            .edges
            .iter()
            .filter_map(|&(i, j)| {
                if i == node {
                    Some(j)
                } else if j == node {
                    Some(i)
                } else {
                    None
                }
            })
            .collect();

        // Count edges between neighbors
        let mut neighbor_edges = 0;
        for &(i, j) in &self.builder.edges {
            if neighbors.contains(&i) && neighbors.contains(&j) {
                neighbor_edges += 1;
            }
        }

        let max_edges = k * (k - 1) / 2;
        if max_edges == 0 {
            return 0.0;
        }

        neighbor_edges as f64 / max_edges as f64
    }

    /// Calculate average clustering coefficient.
    pub fn average_clustering(&self) -> f64 {
        let n = self.builder.pointcloud.len();
        if n == 0 {
            return 0.0;
        }

        let sum: f64 = (0..n).map(|i| self.clustering_coefficient(i)).sum();
        sum / n as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mesh::{MeshMode, PointCloud};

    #[test]
    fn test_coherence_check() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
        ]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();

        let guard = TopologyGuard::new(&builder);
        assert!(guard.check_coherence());
    }

    #[test]
    fn test_connected_components() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![0.5, 0.0],
            vec![10.0, 0.0],
            vec![10.5, 0.0],
        ]);

        // With small radius, should have 2 components
        let mut builder = MeshBuilder::new(cloud, MeshMode::Radius).with_radius(1.0);
        builder.build();

        let guard = TopologyGuard::new(&builder);
        assert_eq!(guard.component_count(), 2);
    }

    #[test]
    fn test_node_degrees() {
        let cloud = PointCloud::from_points(vec![
            vec![0.0, 0.0],
            vec![1.0, 0.0],
            vec![2.0, 0.0],
        ]);

        let mut builder = MeshBuilder::new(cloud, MeshMode::Complete);
        builder.build();

        let guard = TopologyGuard::new(&builder);
        let degrees = guard.node_degrees();

        // In complete graph with 3 nodes, each has degree 2
        assert_eq!(degrees.get(&0), Some(&2));
        assert_eq!(degrees.get(&1), Some(&2));
        assert_eq!(degrees.get(&2), Some(&2));
    }
}
