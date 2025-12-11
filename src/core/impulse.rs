//! Impulse generation for resonance systems.

use rand::Rng;
use serde::{Deserialize, Serialize};

/// An impulse signal with amplitude and decay characteristics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Impulse {
    /// Peak amplitude
    pub amplitude: f64,
    /// Decay rate per step
    pub decay: f64,
    /// Current value
    pub current: f64,
    /// Time since creation
    pub age: u64,
}

impl Impulse {
    /// Create a new impulse with given amplitude and decay.
    pub fn new(amplitude: f64, decay: f64) -> Self {
        Self {
            amplitude,
            decay: decay.clamp(0.0, 1.0),
            current: amplitude,
            age: 0,
        }
    }

    /// Step the impulse forward, applying decay.
    pub fn step(&mut self) -> f64 {
        self.current *= self.decay;
        self.age += 1;
        self.current
    }

    /// Check if the impulse has effectively died out.
    pub fn is_expired(&self, threshold: f64) -> bool {
        self.current.abs() < threshold
    }

    /// Reset the impulse to its initial amplitude.
    pub fn reset(&mut self) {
        self.current = self.amplitude;
        self.age = 0;
    }
}

/// Generator for creating impulses based on various patterns.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImpulseGenerator {
    /// Base amplitude for generated impulses
    pub base_amplitude: f64,
    /// Base decay rate
    pub base_decay: f64,
    /// Amplitude variance (for random generation)
    pub variance: f64,
    /// Pattern type
    pub pattern: ImpulsePattern,
    /// Internal step counter
    step_count: u64,
}

/// Impulse generation patterns.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ImpulsePattern {
    /// Constant amplitude impulses
    Constant,
    /// Sinusoidal modulation
    Sinusoidal,
    /// Random amplitude variation
    Random,
    /// Burst pattern (high-low-high)
    Burst,
}

impl Default for ImpulseGenerator {
    fn default() -> Self {
        Self {
            base_amplitude: 1.0,
            base_decay: 0.9,
            variance: 0.1,
            pattern: ImpulsePattern::Constant,
            step_count: 0,
        }
    }
}

impl ImpulseGenerator {
    /// Create a new generator with custom parameters.
    pub fn new(base_amplitude: f64, base_decay: f64, pattern: ImpulsePattern) -> Self {
        Self {
            base_amplitude,
            base_decay,
            variance: 0.1,
            pattern,
            step_count: 0,
        }
    }

    /// Generate the next impulse based on the configured pattern.
    pub fn generate(&mut self) -> Impulse {
        let mut rng = rand::thread_rng();
        self.step_count += 1;

        let amplitude = match self.pattern {
            ImpulsePattern::Constant => self.base_amplitude,
            ImpulsePattern::Sinusoidal => {
                let phase = (self.step_count as f64 * 0.1).sin();
                self.base_amplitude * (0.5 + 0.5 * phase)
            }
            ImpulsePattern::Random => {
                let var: f64 = rng.gen_range(-self.variance..self.variance);
                self.base_amplitude * (1.0 + var)
            }
            ImpulsePattern::Burst => {
                if self.step_count % 10 < 3 {
                    self.base_amplitude * 2.0
                } else {
                    self.base_amplitude * 0.5
                }
            }
        };

        Impulse::new(amplitude, self.base_decay)
    }

    /// Generate multiple impulses.
    pub fn generate_batch(&mut self, count: usize) -> Vec<Impulse> {
        (0..count).map(|_| self.generate()).collect()
    }

    /// Reset the internal step counter.
    pub fn reset(&mut self) {
        self.step_count = 0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_impulse_decay() {
        let mut imp = Impulse::new(1.0, 0.5);
        assert_eq!(imp.current, 1.0);

        imp.step();
        assert!((imp.current - 0.5).abs() < 1e-9);

        imp.step();
        assert!((imp.current - 0.25).abs() < 1e-9);
    }

    #[test]
    fn test_impulse_expiration() {
        let mut imp = Impulse::new(1.0, 0.1);
        for _ in 0..20 {
            imp.step();
        }
        assert!(imp.is_expired(0.001));
    }

    #[test]
    fn test_generator_constant() {
        let mut gen = ImpulseGenerator::new(1.0, 0.9, ImpulsePattern::Constant);
        let imp = gen.generate();
        assert_eq!(imp.amplitude, 1.0);
    }
}
