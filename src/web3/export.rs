//! Export utilities for persisting research data.

use serde::{Deserialize, Serialize};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::{fs, io};

/// Export module for persisting mesh/cluster states.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportModule {
    /// Export directory
    pub export_dir: PathBuf,
}

impl Default for ExportModule {
    fn default() -> Self {
        Self {
            export_dir: std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
        }
    }
}

impl ExportModule {
    /// Create a new export module with specified directory.
    pub fn new(export_dir: impl AsRef<Path>) -> Self {
        Self {
            export_dir: export_dir.as_ref().to_path_buf(),
        }
    }

    /// Ensure the export directory exists.
    fn ensure_dir(&self) -> io::Result<()> {
        fs::create_dir_all(&self.export_dir)
    }

    /// Get the full path for a filename.
    fn full_path(&self, filename: &str) -> PathBuf {
        self.export_dir.join(filename)
    }

    /// Export data as JSON.
    pub fn export_as_json<T: Serialize>(&self, data: &T, filename: &str) -> io::Result<PathBuf> {
        self.ensure_dir()?;
        let path = self.full_path(filename);

        let file = fs::File::create(&path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, data)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        Ok(path)
    }

    /// Export rows as CSV.
    pub fn export_as_csv<I, R>(&self, rows: I, filename: &str) -> io::Result<PathBuf>
    where
        I: IntoIterator<Item = R>,
        R: IntoIterator<Item = String>,
    {
        self.ensure_dir()?;
        let path = self.full_path(filename);

        let mut file = fs::File::create(&path)?;
        for row in rows {
            let line: Vec<String> = row.into_iter().collect();
            writeln!(file, "{}", line.join(","))?;
        }

        Ok(path)
    }

    /// Export data as YAML.
    pub fn export_as_yaml<T: Serialize>(&self, data: &T, filename: &str) -> io::Result<PathBuf> {
        self.ensure_dir()?;
        let path = self.full_path(filename);

        let yaml_str = serde_yaml::to_string(data)
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        fs::write(&path, yaml_str)?;
        Ok(path)
    }

    /// Export raw bytes.
    pub fn export_raw(&self, data: &[u8], filename: &str) -> io::Result<PathBuf> {
        self.ensure_dir()?;
        let path = self.full_path(filename);
        fs::write(&path, data)?;
        Ok(path)
    }

    /// Import JSON data.
    pub fn import_json<T: for<'de> Deserialize<'de>>(&self, filename: &str) -> io::Result<T> {
        let path = self.full_path(filename);
        let content = fs::read_to_string(&path)?;
        serde_json::from_str(&content).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }

    /// Import YAML data.
    pub fn import_yaml<T: for<'de> Deserialize<'de>>(&self, filename: &str) -> io::Result<T> {
        let path = self.full_path(filename);
        let content = fs::read_to_string(&path)?;
        serde_yaml::from_str(&content).map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))
    }

    /// List files in export directory.
    pub fn list_exports(&self) -> io::Result<Vec<String>> {
        let entries = fs::read_dir(&self.export_dir)?;
        let mut files = Vec::new();

        for entry in entries {
            let entry = entry?;
            if let Some(name) = entry.file_name().to_str() {
                files.push(name.to_string());
            }
        }

        files.sort();
        Ok(files)
    }

    /// Delete an export file.
    pub fn delete_export(&self, filename: &str) -> io::Result<()> {
        let path = self.full_path(filename);
        fs::remove_file(path)
    }
}

/// Data structure for mesh export.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshExport {
    /// Point coordinates
    pub points: Vec<Vec<f64>>,
    /// Edge indices (pairs)
    pub edges: Vec<(usize, usize)>,
    /// Edge scores/weights
    pub edge_scores: std::collections::HashMap<String, f64>,
    /// Export metadata
    pub metadata: std::collections::HashMap<String, String>,
}

impl MeshExport {
    /// Create a new mesh export.
    pub fn new() -> Self {
        Self {
            points: Vec::new(),
            edges: Vec::new(),
            edge_scores: std::collections::HashMap::new(),
            metadata: std::collections::HashMap::new(),
        }
    }

    /// Add a point.
    pub fn add_point(&mut self, coords: Vec<f64>) {
        self.points.push(coords);
    }

    /// Add an edge.
    pub fn add_edge(&mut self, from: usize, to: usize, score: Option<f64>) {
        self.edges.push((from, to));
        if let Some(s) = score {
            self.edge_scores.insert(format!("{from}-{to}"), s);
        }
    }

    /// Add metadata.
    pub fn set_metadata(&mut self, key: impl Into<String>, value: impl Into<String>) {
        self.metadata.insert(key.into(), value.into());
    }
}

impl Default for MeshExport {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use tempfile::tempdir;

    #[test]
    fn test_export_json() {
        let dir = tempdir().unwrap();
        let export = ExportModule::new(dir.path());

        let mut data = HashMap::new();
        data.insert("key", "value");

        let path = export.export_as_json(&data, "test.json").unwrap();
        assert!(path.exists());

        let loaded: HashMap<String, String> = export.import_json("test.json").unwrap();
        assert_eq!(loaded.get("key"), Some(&"value".to_string()));
    }

    #[test]
    fn test_export_csv() {
        let dir = tempdir().unwrap();
        let export = ExportModule::new(dir.path());

        let rows = vec![
            vec!["a".to_string(), "b".to_string()],
            vec!["1".to_string(), "2".to_string()],
        ];

        let path = export.export_as_csv(rows, "test.csv").unwrap();
        assert!(path.exists());

        let content = fs::read_to_string(&path).unwrap();
        assert!(content.contains("a,b"));
        assert!(content.contains("1,2"));
    }

    #[test]
    fn test_mesh_export() {
        let mut mesh = MeshExport::new();
        mesh.add_point(vec![0.0, 0.0, 0.0]);
        mesh.add_point(vec![1.0, 1.0, 1.0]);
        mesh.add_edge(0, 1, Some(0.5));
        mesh.set_metadata("version", "1.0");

        assert_eq!(mesh.points.len(), 2);
        assert_eq!(mesh.edges.len(), 1);
        assert_eq!(mesh.edge_scores.get("0-1"), Some(&0.5));
    }
}
