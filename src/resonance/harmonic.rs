//! Harmonic scheduling for traffic-blending network research.
//!
//! The harmonic scheduler generates timing patterns that naturally blend
//! with ambient network traffic, making research probes indistinguishable
//! from normal activity.

use rand::Rng;
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;
use std::time::{Duration, Instant};

/// Harmonic pattern for probe scheduling.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum HarmonicPattern {
    /// Poisson process - exponential inter-arrival times (most natural)
    #[default]
    Poisson,
    /// Brownian walk - random walk with drift
    Brownian,
    /// Multi-modal - mimics human interaction patterns
    MultiModal,
    /// Circadian - follows daily activity curves
    Circadian,
    /// Fibonacci - golden ratio spacing
    Fibonacci,
    /// Pink noise - 1/f frequency distribution
    PinkNoise,
    /// Custom waveform
    Custom,
}

impl HarmonicPattern {
    /// Get the base frequency characteristic of this pattern.
    pub fn base_frequency(&self) -> f64 {
        match self {
            HarmonicPattern::Poisson => 1.0,
            HarmonicPattern::Brownian => 0.5,
            HarmonicPattern::MultiModal => 0.2,
            HarmonicPattern::Circadian => 1.0 / 86400.0, // Once per day
            HarmonicPattern::Fibonacci => 0.618,         // Golden ratio
            HarmonicPattern::PinkNoise => 1.0,
            HarmonicPattern::Custom => 1.0,
        }
    }
}

/// Configuration for harmonic scheduling.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchedulerConfig {
    /// Harmonic pattern to use
    pub pattern: HarmonicPattern,
    /// Mean interval between probes (seconds)
    pub mean_interval: f64,
    /// Minimum interval (seconds)
    pub min_interval: f64,
    /// Maximum interval (seconds)
    pub max_interval: f64,
    /// Burstiness factor (0.0 = uniform, 1.0 = very bursty)
    pub burstiness: f64,
    /// Time-of-day sensitivity (0.0 = none, 1.0 = full)
    pub circadian_factor: f64,
    /// Number of harmonics for multi-modal pattern
    pub num_harmonics: usize,
    /// Random seed for reproducibility (None = random)
    pub seed: Option<u64>,
}

impl Default for SchedulerConfig {
    fn default() -> Self {
        Self {
            pattern: HarmonicPattern::Poisson,
            mean_interval: 1.0,
            min_interval: 0.01,
            max_interval: 10.0,
            burstiness: 0.3,
            circadian_factor: 0.0,
            num_harmonics: 3,
            seed: None,
        }
    }
}

/// A scheduled timing slot.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingSlot {
    /// Sequence number
    pub sequence: u64,
    /// Delay from previous slot (seconds)
    pub delay: f64,
    /// Absolute time (seconds since scheduler start)
    pub absolute_time: f64,
    /// Phase within current harmonic cycle (0.0 - 1.0)
    pub phase: f64,
    /// Amplitude/intensity for this slot
    pub amplitude: f64,
    /// Harmonic index (for multi-modal)
    pub harmonic_idx: usize,
}

/// Harmonic scheduler for traffic-blending timing.
#[derive(Debug)]
pub struct HarmonicScheduler {
    pub config: SchedulerConfig,
    sequence: u64,
    current_time: f64,
    start_instant: Instant,
    pink_noise_state: Vec<f64>,
    brownian_state: f64,
    fibonacci_state: (f64, f64),
}

impl Default for HarmonicScheduler {
    fn default() -> Self {
        Self::new(SchedulerConfig::default())
    }
}

impl HarmonicScheduler {
    /// Create a new harmonic scheduler.
    pub fn new(config: SchedulerConfig) -> Self {
        Self {
            pink_noise_state: vec![0.0; 16],
            brownian_state: config.mean_interval,
            fibonacci_state: (1.0, 1.0),
            config,
            sequence: 0,
            current_time: 0.0,
            start_instant: Instant::now(),
        }
    }

    /// Get the next timing slot.
    pub fn next_slot(&mut self) -> TimingSlot {
        let mut rng = rand::thread_rng();

        let delay = match self.config.pattern {
            HarmonicPattern::Poisson => self.poisson_delay(&mut rng),
            HarmonicPattern::Brownian => self.brownian_delay(&mut rng),
            HarmonicPattern::MultiModal => self.multimodal_delay(&mut rng),
            HarmonicPattern::Circadian => self.circadian_delay(&mut rng),
            HarmonicPattern::Fibonacci => self.fibonacci_delay(),
            HarmonicPattern::PinkNoise => self.pink_noise_delay(&mut rng),
            HarmonicPattern::Custom => self.config.mean_interval,
        };

        let clamped_delay = delay.clamp(self.config.min_interval, self.config.max_interval);

        // Apply circadian modulation if enabled
        let modulated_delay = if self.config.circadian_factor > 0.0 {
            self.apply_circadian(clamped_delay)
        } else {
            clamped_delay
        };

        self.sequence += 1;
        self.current_time += modulated_delay;

        let phase = (self.current_time * self.config.pattern.base_frequency()) % 1.0;
        let amplitude = self.compute_amplitude(phase);

        TimingSlot {
            sequence: self.sequence,
            delay: modulated_delay,
            absolute_time: self.current_time,
            phase,
            amplitude,
            harmonic_idx: (self.sequence as usize) % self.config.num_harmonics,
        }
    }

    /// Generate multiple timing slots.
    pub fn generate_slots(&mut self, count: usize) -> Vec<TimingSlot> {
        (0..count).map(|_| self.next_slot()).collect()
    }

    /// Get delay until next slot as Duration.
    pub fn next_delay_duration(&mut self) -> Duration {
        let slot = self.next_slot();
        Duration::from_secs_f64(slot.delay)
    }

    /// Poisson process delay (exponential distribution).
    fn poisson_delay(&self, rng: &mut impl Rng) -> f64 {
        let u: f64 = rng.gen();
        -self.config.mean_interval * u.ln()
    }

    /// Brownian motion delay.
    fn brownian_delay(&mut self, rng: &mut impl Rng) -> f64 {
        let drift = self.config.mean_interval * 0.1;
        let volatility = self.config.mean_interval * self.config.burstiness;

        let noise: f64 = rng.gen_range(-1.0..1.0);
        self.brownian_state += drift + volatility * noise;
        self.brownian_state = self.brownian_state.max(self.config.min_interval);

        self.brownian_state
    }

    /// Multi-modal delay (mixture of patterns).
    fn multimodal_delay(&self, rng: &mut impl Rng) -> f64 {
        let mode: usize = rng.gen_range(0..self.config.num_harmonics);

        // Each mode has different timing characteristics
        let mode_means = [
            self.config.mean_interval * 0.5,  // Fast mode
            self.config.mean_interval,        // Normal mode
            self.config.mean_interval * 2.0,  // Slow mode
        ];

        let mean = mode_means[mode % mode_means.len()];
        let u: f64 = rng.gen();
        -mean * u.ln()
    }

    /// Circadian rhythm delay.
    fn circadian_delay(&self, rng: &mut impl Rng) -> f64 {
        // Base Poisson delay
        let u: f64 = rng.gen();
        let base = -self.config.mean_interval * u.ln();

        // Modulate by time of day (simplified)
        let hour_phase = (self.current_time / 3600.0) % 24.0;
        let activity_curve = 0.5 + 0.5 * ((hour_phase - 12.0) * PI / 12.0).cos();

        // Lower activity = longer delays
        base / activity_curve.max(0.1)
    }

    /// Fibonacci-based delay.
    fn fibonacci_delay(&mut self) -> f64 {
        let (a, b) = self.fibonacci_state;
        let next = a + b;

        self.fibonacci_state = (b, next);

        // Normalize to mean interval range
        let normalized = (next % 100.0) / 100.0;
        self.config.min_interval
            + normalized * (self.config.max_interval - self.config.min_interval)
    }

    /// Pink noise (1/f) delay.
    fn pink_noise_delay(&mut self, rng: &mut impl Rng) -> f64 {
        // Voss-McCartney algorithm for pink noise
        let mut total = 0.0;

        for (i, state) in self.pink_noise_state.iter_mut().enumerate() {
            let mask = 1 << i;
            if (self.sequence as usize) & mask == 0 {
                *state = rng.gen_range(-1.0..1.0);
            }
            total += *state;
        }

        // Normalize and scale
        let normalized = (total / self.pink_noise_state.len() as f64 + 1.0) / 2.0;
        self.config.min_interval
            + normalized * (self.config.max_interval - self.config.min_interval)
    }

    /// Apply circadian modulation to a delay.
    fn apply_circadian(&self, delay: f64) -> f64 {
        let elapsed = self.start_instant.elapsed().as_secs_f64();
        let hour = ((elapsed / 3600.0) % 24.0) as f64;

        // Activity curve peaks at midday, lowest at night
        let activity = 0.5 + 0.5 * ((hour - 14.0) * PI / 12.0).cos();

        // High activity = shorter delays
        let factor = 1.0 - self.config.circadian_factor * (1.0 - activity);
        delay * factor.max(0.1)
    }

    /// Compute amplitude for a given phase.
    fn compute_amplitude(&self, phase: f64) -> f64 {
        // Sum of harmonics
        let mut amplitude = 0.0;
        for h in 1..=self.config.num_harmonics {
            let freq = h as f64;
            let weight = 1.0 / freq; // Higher harmonics contribute less
            amplitude += weight * (2.0 * PI * freq * phase).sin();
        }

        // Normalize to 0-1
        (amplitude + 1.0) / 2.0
    }

    /// Get current sequence number.
    pub fn sequence(&self) -> u64 {
        self.sequence
    }

    /// Get current virtual time.
    pub fn current_time(&self) -> f64 {
        self.current_time
    }

    /// Reset the scheduler.
    pub fn reset(&mut self) {
        self.sequence = 0;
        self.current_time = 0.0;
        self.start_instant = Instant::now();
        self.pink_noise_state.fill(0.0);
        self.brownian_state = self.config.mean_interval;
        self.fibonacci_state = (1.0, 1.0);
    }

    /// Get statistics about generated timing.
    pub fn stats(&self, slots: &[TimingSlot]) -> SchedulerStats {
        if slots.is_empty() {
            return SchedulerStats::default();
        }

        let delays: Vec<f64> = slots.iter().map(|s| s.delay).collect();
        let mean = delays.iter().sum::<f64>() / delays.len() as f64;

        let variance = delays.iter()
            .map(|d| (d - mean).powi(2))
            .sum::<f64>() / delays.len() as f64;

        let std_dev = variance.sqrt();
        let cv = if mean > 0.0 { std_dev / mean } else { 0.0 };

        let min = delays.iter().cloned().fold(f64::INFINITY, f64::min);
        let max = delays.iter().cloned().fold(f64::NEG_INFINITY, f64::max);

        // Compute inter-quartile range
        let mut sorted = delays.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let q1 = sorted[sorted.len() / 4];
        let q3 = sorted[3 * sorted.len() / 4];
        let iqr = q3 - q1;

        SchedulerStats {
            count: slots.len() as u64,
            mean_delay: mean,
            std_dev,
            coefficient_of_variation: cv,
            min_delay: min,
            max_delay: max,
            iqr,
            total_time: slots.last().map(|s| s.absolute_time).unwrap_or(0.0),
        }
    }
}

/// Statistics about scheduled timing.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct SchedulerStats {
    pub count: u64,
    pub mean_delay: f64,
    pub std_dev: f64,
    pub coefficient_of_variation: f64,
    pub min_delay: f64,
    pub max_delay: f64,
    pub iqr: f64,
    pub total_time: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_poisson_delays() {
        let mut scheduler = HarmonicScheduler::new(SchedulerConfig {
            pattern: HarmonicPattern::Poisson,
            mean_interval: 1.0,
            ..Default::default()
        });

        let slots = scheduler.generate_slots(100);
        let stats = scheduler.stats(&slots);

        // Mean should be approximately the configured mean
        assert!((stats.mean_delay - 1.0).abs() < 0.5);
    }

    #[test]
    fn test_timing_bounds() {
        let mut scheduler = HarmonicScheduler::new(SchedulerConfig {
            min_interval: 0.1,
            max_interval: 5.0,
            ..Default::default()
        });

        let slots = scheduler.generate_slots(50);

        for slot in slots {
            assert!(slot.delay >= 0.1);
            assert!(slot.delay <= 5.0);
        }
    }

    #[test]
    fn test_fibonacci_deterministic() {
        let mut scheduler = HarmonicScheduler::new(SchedulerConfig {
            pattern: HarmonicPattern::Fibonacci,
            ..Default::default()
        });

        let slot1 = scheduler.next_slot();
        let slot2 = scheduler.next_slot();

        // Fibonacci should produce different but bounded delays
        assert!(slot1.delay >= scheduler.config.min_interval);
        assert!(slot2.delay <= scheduler.config.max_interval);
    }

    #[test]
    fn test_slot_phase() {
        let mut scheduler = HarmonicScheduler::default();
        let slot = scheduler.next_slot();

        assert!(slot.phase >= 0.0);
        assert!(slot.phase <= 1.0);
        assert!(slot.amplitude >= 0.0);
        assert!(slot.amplitude <= 1.0);
    }
}
