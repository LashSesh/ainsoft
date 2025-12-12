//! Configuration management for AinSOFT.

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

use crate::mesh::MeshMode;
use crate::phantomload::PhantomloadConfig;
use crate::web3::kernel::KernelConfig;

/// Main configuration structure.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Web3/Phosphoros configuration
    #[serde(default)]
    pub phosphoros: KernelConfig,

    /// Phantomload configuration
    #[serde(default)]
    pub phantomload: PhantomloadConfig,

    /// Mesh configuration
    #[serde(default)]
    pub mesh: MeshConfig,

    /// Scan configuration
    #[serde(default)]
    pub scan: ScanConfig,

    /// General settings
    #[serde(default)]
    pub general: GeneralConfig,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            phosphoros: KernelConfig::default(),
            phantomload: PhantomloadConfig::default(),
            mesh: MeshConfig::default(),
            scan: ScanConfig::default(),
            general: GeneralConfig::default(),
        }
    }
}

impl Config {
    /// Load configuration from a YAML file.
    pub fn from_file(path: impl AsRef<Path>) -> Result<Self, ConfigError> {
        let content = std::fs::read_to_string(path.as_ref())
            .map_err(|e| ConfigError::IoError(e.to_string()))?;

        serde_yaml::from_str(&content).map_err(|e| ConfigError::ParseError(e.to_string()))
    }

    /// Save configuration to a YAML file.
    pub fn save(&self, path: impl AsRef<Path>) -> Result<(), ConfigError> {
        let content =
            serde_yaml::to_string(self).map_err(|e| ConfigError::SerializeError(e.to_string()))?;

        std::fs::write(path.as_ref(), content).map_err(|e| ConfigError::IoError(e.to_string()))
    }

    /// Load from JSON file.
    pub fn from_json(path: impl AsRef<Path>) -> Result<Self, ConfigError> {
        let content = std::fs::read_to_string(path.as_ref())
            .map_err(|e| ConfigError::IoError(e.to_string()))?;

        serde_json::from_str(&content).map_err(|e| ConfigError::ParseError(e.to_string()))
    }

    /// Create default configuration file.
    pub fn create_default(path: impl AsRef<Path>) -> Result<(), ConfigError> {
        let config = Self::default();
        config.save(path)
    }
}

/// Mesh-specific configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshConfig {
    /// Default mesh mode
    pub mode: MeshMode,
    /// Default k for kNN
    pub k: usize,
    /// Default radius
    pub radius: f64,
    /// Maximum entropy
    pub max_entropy: f64,
    /// Export path
    pub export_path: Option<PathBuf>,
}

impl Default for MeshConfig {
    fn default() -> Self {
        Self {
            mode: MeshMode::Knn,
            k: 5,
            radius: 1.0,
            max_entropy: 10.0,
            export_path: None,
        }
    }
}

/// Scan-specific configuration.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScanConfig {
    /// Probe interval (seconds)
    pub interval: f64,
    /// Timeout (seconds)
    pub timeout: f64,
    /// Maximum records to keep
    pub max_records: usize,
    /// Anomaly detection threshold
    pub anomaly_threshold: f64,
}

impl Default for ScanConfig {
    fn default() -> Self {
        Self {
            interval: 0.1,
            timeout: 5.0,
            max_records: 10000,
            anomaly_threshold: 2.0,
        }
    }
}

/// General settings.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralConfig {
    /// Log level
    pub log_level: String,
    /// Data directory
    pub data_dir: PathBuf,
    /// Enable verbose output
    pub verbose: bool,
}

impl Default for GeneralConfig {
    fn default() -> Self {
        Self {
            log_level: "info".to_string(),
            data_dir: PathBuf::from("./data"),
            verbose: false,
        }
    }
}

/// Configuration errors.
#[derive(Debug, Clone)]
pub enum ConfigError {
    IoError(String),
    ParseError(String),
    SerializeError(String),
    ValidationError(String),
}

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConfigError::IoError(e) => write!(f, "IO error: {}", e),
            ConfigError::ParseError(e) => write!(f, "Parse error: {}", e),
            ConfigError::SerializeError(e) => write!(f, "Serialize error: {}", e),
            ConfigError::ValidationError(e) => write!(f, "Validation error: {}", e),
        }
    }
}

impl std::error::Error for ConfigError {}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.mesh.k, 5);
        assert_eq!(config.scan.timeout, 5.0);
    }

    #[test]
    fn test_save_and_load() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("config.yaml");

        let config = Config::default();
        config.save(&path).unwrap();

        let loaded = Config::from_file(&path).unwrap();
        assert_eq!(loaded.mesh.k, config.mesh.k);
    }
}
