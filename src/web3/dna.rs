//! Seed phrase to geometry encoding engine.
//!
//! Derives 5D geometry vectors from seed phrases using cryptographic hashing.

use nalgebra::DVector;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::GEOMETRY_DIMENSIONS;

/// Transform function type for post-processing geometry vectors.
pub type TransformFn = Box<dyn Fn(DVector<f64>) -> DVector<f64> + Send + Sync>;

/// Engine for encoding seed phrases into 5D geometry vectors.
#[derive(Default)]
pub struct SeedDnaEngine {
    /// Optional transformation function
    transform: Option<TransformFn>,
}

impl std::fmt::Debug for SeedDnaEngine {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SeedDnaEngine")
            .field("has_transform", &self.transform.is_some())
            .finish()
    }
}

/// A seed representation with geometry data.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Seed {
    /// Original phrase
    pub phrase: String,
    /// Raw seed values (16-bit chunks)
    pub values: Vec<u16>,
    /// 5D geometry vector
    pub geometry: Vec<f64>,
}

impl SeedDnaEngine {
    /// Create a new engine with a transformation function.
    pub fn with_transform<F>(transform: F) -> Self
    where
        F: Fn(DVector<f64>) -> DVector<f64> + Send + Sync + 'static,
    {
        Self {
            transform: Some(Box::new(transform)),
        }
    }

    /// Convert a phrase into deterministic 16-bit chunks using SHA-256.
    pub fn phrase_to_seed(phrase: &str) -> Vec<u16> {
        let mut hasher = Sha256::new();
        hasher.update(phrase.as_bytes());
        let digest = hasher.finalize();
        let hex = hex::encode(digest);

        // Extract 8 x 16-bit values from 64 hex chars (32 bytes)
        (0..8)
            .map(|i| {
                let chunk = &hex[i * 4..(i + 1) * 4];
                u16::from_str_radix(chunk, 16).unwrap_or(0)
            })
            .collect()
    }

    /// Create a 5D vector from seed values.
    pub fn seed_to_geometry(seed: &[u16]) -> DVector<f64> {
        let mut values: Vec<f64> = seed
            .iter()
            .take(GEOMETRY_DIMENSIONS)
            .map(|&v| v as f64)
            .collect();

        // Pad with zeros if needed
        while values.len() < GEOMETRY_DIMENSIONS {
            values.push(0.0);
        }

        DVector::from_vec(values)
    }

    /// Encode a phrase to a geometry vector with optional transformation.
    pub fn encode(&self, phrase: &str) -> DVector<f64> {
        let seed = Self::phrase_to_seed(phrase);
        let geometry = Self::seed_to_geometry(&seed);

        match &self.transform {
            Some(f) => f(geometry),
            None => geometry,
        }
    }

    /// Encode a phrase and return full seed data.
    pub fn encode_full(&self, phrase: &str) -> Seed {
        let values = Self::phrase_to_seed(phrase);
        let geometry = self.encode(phrase);

        Seed {
            phrase: phrase.to_string(),
            values,
            geometry: geometry.as_slice().to_vec(),
        }
    }

    /// Normalize a geometry vector to unit length.
    pub fn normalize(geometry: &DVector<f64>) -> DVector<f64> {
        let norm = geometry.norm();
        if norm > 1e-9 {
            geometry / norm
        } else {
            geometry.clone()
        }
    }

    /// Calculate distance between two geometry vectors.
    pub fn distance(a: &DVector<f64>, b: &DVector<f64>) -> f64 {
        (a - b).norm()
    }

    /// Calculate cosine similarity between two geometry vectors.
    pub fn cosine_similarity(a: &DVector<f64>, b: &DVector<f64>) -> f64 {
        let norm_a = a.norm();
        let norm_b = b.norm();

        if norm_a < 1e-9 || norm_b < 1e-9 {
            return 0.0;
        }

        a.dot(b) / (norm_a * norm_b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_phrase_to_seed() {
        let seed = SeedDnaEngine::phrase_to_seed("test phrase");
        assert_eq!(seed.len(), 8);
        // Should be deterministic
        assert_eq!(seed, SeedDnaEngine::phrase_to_seed("test phrase"));
    }

    #[test]
    fn test_seed_to_geometry() {
        let seed = vec![1000, 2000, 3000, 4000, 5000];
        let geometry = SeedDnaEngine::seed_to_geometry(&seed);
        assert_eq!(geometry.len(), GEOMETRY_DIMENSIONS);
        assert_eq!(geometry[0], 1000.0);
    }

    #[test]
    fn test_encode() {
        let engine = SeedDnaEngine::default();
        let geometry = engine.encode("test");
        assert_eq!(geometry.len(), GEOMETRY_DIMENSIONS);
    }

    #[test]
    fn test_with_transform() {
        let engine = SeedDnaEngine::with_transform(|v| v * 2.0);
        let geometry = engine.encode("test");
        let default_engine = SeedDnaEngine::default();
        let default_geometry = default_engine.encode("test");

        // Transformed should be 2x the default
        assert!((geometry[0] - default_geometry[0] * 2.0).abs() < 1e-9);
    }

    #[test]
    fn test_cosine_similarity() {
        let a = DVector::from_vec(vec![1.0, 0.0, 0.0, 0.0, 0.0]);
        let b = DVector::from_vec(vec![1.0, 0.0, 0.0, 0.0, 0.0]);
        assert!((SeedDnaEngine::cosine_similarity(&a, &b) - 1.0).abs() < 1e-9);

        let c = DVector::from_vec(vec![0.0, 1.0, 0.0, 0.0, 0.0]);
        assert!(SeedDnaEngine::cosine_similarity(&a, &c).abs() < 1e-9);
    }
}
