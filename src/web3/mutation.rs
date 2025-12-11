//! Mutation engine for generating seed variants.

use nalgebra::DVector;
use rand::Rng;
use serde::{Deserialize, Serialize};

use super::SeedDnaEngine;

/// Configuration for mutation behavior.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MutationConfig {
    /// Base mutation rate (perturbation magnitude)
    pub rate: f64,
    /// Whether to use Gaussian distribution for mutations
    pub gaussian: bool,
    /// Standard deviation for Gaussian mutations
    pub std_dev: f64,
}

impl Default for MutationConfig {
    fn default() -> Self {
        Self {
            rate: 0.1,
            gaussian: false,
            std_dev: 0.05,
        }
    }
}

/// Engine for generating mutated seed variants.
#[derive(Debug, Clone)]
pub struct MutationEngine {
    /// Configuration
    config: MutationConfig,
}

impl Default for MutationEngine {
    fn default() -> Self {
        Self {
            config: MutationConfig::default(),
        }
    }
}

impl MutationEngine {
    /// Create a new mutation engine with custom configuration.
    pub fn new(config: MutationConfig) -> Self {
        Self { config }
    }

    /// Create with a specific mutation rate.
    pub fn with_rate(rate: f64) -> Self {
        Self {
            config: MutationConfig {
                rate,
                ..Default::default()
            },
        }
    }

    /// Mutate a seed sequence with bounded random perturbation.
    pub fn mutate_seed(&self, seed: &[u16]) -> Vec<f64> {
        let mut rng = rand::thread_rng();
        seed.iter()
            .map(|&x| {
                let perturbation = if self.config.gaussian {
                    // Gaussian perturbation
                    let u1: f64 = rng.gen();
                    let u2: f64 = rng.gen();
                    let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
                    z * self.config.std_dev
                } else {
                    // Uniform perturbation
                    (rng.gen::<f64>() - 0.5) * 2.0 * self.config.rate
                };
                x as f64 + perturbation * x as f64
            })
            .collect()
    }

    /// Generate a mutated seed from a phrase.
    pub fn generate_mutant(&self, phrase: &str) -> Vec<f64> {
        let base_seed = SeedDnaEngine::phrase_to_seed(phrase);
        self.mutate_seed(&base_seed)
    }

    /// Generate a mutated geometry vector from a phrase.
    pub fn generate_geometry(&self, phrase: &str) -> DVector<f64> {
        let mutated = self.generate_mutant(phrase);
        // Take first 5 dimensions
        let values: Vec<f64> = mutated.into_iter().take(5).collect();
        DVector::from_vec(values)
    }

    /// Generate multiple mutants from a single phrase.
    pub fn generate_population(&self, phrase: &str, count: usize) -> Vec<DVector<f64>> {
        (0..count)
            .map(|i| {
                // Use index as additional entropy
                let variant_phrase = format!("{phrase}-{i}");
                self.generate_geometry(&variant_phrase)
            })
            .collect()
    }

    /// Crossover two geometry vectors to create offspring.
    pub fn crossover(&self, a: &DVector<f64>, b: &DVector<f64>) -> DVector<f64> {
        let mut rng = rand::thread_rng();
        let crossover_point = rng.gen_range(0..a.len());

        let mut values: Vec<f64> = Vec::with_capacity(a.len());
        for i in 0..a.len() {
            if i < crossover_point {
                values.push(a[i]);
            } else {
                values.push(b[i]);
            }
        }

        DVector::from_vec(values)
    }

    /// Apply point mutation to a geometry vector.
    pub fn point_mutate(&self, geometry: &DVector<f64>) -> DVector<f64> {
        let mut rng = rand::thread_rng();
        let mut values = geometry.as_slice().to_vec();

        // Mutate each dimension with some probability
        for value in &mut values {
            if rng.gen::<f64>() < 0.3 {
                let perturbation = if self.config.gaussian {
                    let u1: f64 = rng.gen();
                    let u2: f64 = rng.gen();
                    let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
                    z * self.config.std_dev * *value
                } else {
                    (rng.gen::<f64>() - 0.5) * 2.0 * self.config.rate * *value
                };
                *value += perturbation;
            }
        }

        DVector::from_vec(values)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mutate_seed() {
        let engine = MutationEngine::with_rate(0.1);
        let seed = vec![1000, 2000, 3000];
        let mutated = engine.mutate_seed(&seed);
        assert_eq!(mutated.len(), seed.len());

        // Values should be different but close
        for (orig, mut_val) in seed.iter().zip(mutated.iter()) {
            let diff = (*orig as f64 - *mut_val).abs();
            assert!(diff < *orig as f64 * 0.5); // Within 50%
        }
    }

    #[test]
    fn test_generate_population() {
        let engine = MutationEngine::default();
        let population = engine.generate_population("test", 10);
        assert_eq!(population.len(), 10);

        // All should be different
        for i in 0..population.len() {
            for j in (i + 1)..population.len() {
                assert_ne!(population[i], population[j]);
            }
        }
    }

    #[test]
    fn test_crossover() {
        let engine = MutationEngine::default();
        let a = DVector::from_vec(vec![1.0, 1.0, 1.0, 1.0, 1.0]);
        let b = DVector::from_vec(vec![2.0, 2.0, 2.0, 2.0, 2.0]);
        let offspring = engine.crossover(&a, &b);

        assert_eq!(offspring.len(), 5);
        // Offspring should have mix of 1.0 and 2.0 values
    }
}
