//! AinSOFT CLI - Universal Web3 Research Framework
//!
//! A research framework for Web3 resonance networks and mesh topology analysis.

use clap::{Parser, Subcommand};
use std::path::PathBuf;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use ainsoft::config::Config;
use ainsoft::mesh::{MeshLayer, MeshLayerConfig, PointCloud};
use ainsoft::phantomload::PhantomloadKernel;
use ainsoft::web3::PhosphorosKernel;

/// AinSOFT - Universal Web3 Research Framework
#[derive(Parser, Debug)]
#[command(name = "ainsoft")]
#[command(author = "AinSOFT Team")]
#[command(version = ainsoft::VERSION)]
#[command(about = "Universal research framework for Web3 resonance networks", long_about = None)]
struct Cli {
    /// Configuration file path
    #[arg(short, long, default_value = "ainsoft.yaml")]
    config: PathBuf,

    /// Verbosity level
    #[arg(short, long, action = clap::ArgAction::Count)]
    verbose: u8,

    /// Output directory
    #[arg(short, long)]
    output: Option<PathBuf>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Initialize a new configuration file
    Init {
        /// Force overwrite existing config
        #[arg(short, long)]
        force: bool,
    },

    /// Web3/Phosphoros research commands
    Web3 {
        #[command(subcommand)]
        action: Web3Action,
    },

    /// Phantom RPC simulation commands
    Phantom {
        #[command(subcommand)]
        action: PhantomAction,
    },

    /// Mesh topology commands
    Mesh {
        #[command(subcommand)]
        action: MeshAction,
    },

    /// Show framework information
    Info,
}

#[derive(Subcommand, Debug)]
enum Web3Action {
    /// Encode seed phrases to geometry vectors
    Encode {
        /// Seed phrases to encode
        #[arg(required = true)]
        phrases: Vec<String>,

        /// Apply mutations
        #[arg(short, long)]
        mutate: bool,

        /// Output format (json, csv)
        #[arg(short, long, default_value = "json")]
        format: String,
    },

    /// Cluster seed geometries
    Cluster {
        /// Input file with seed phrases (one per line)
        #[arg(short, long)]
        input: PathBuf,

        /// Number of clusters
        #[arg(short = 'k', long, default_value = "3")]
        clusters: usize,
    },

    /// Run interactive kernel
    Run {
        /// Number of ticks to run
        #[arg(short, long)]
        ticks: Option<u64>,
    },
}

#[derive(Subcommand, Debug)]
enum PhantomAction {
    /// Spawn phantom cells
    Spawn {
        /// Number of cells to spawn
        #[arg(short, long, default_value = "10")]
        count: usize,

        /// Base seed phrase
        #[arg(short, long, default_value = "phantom")]
        seed: String,

        /// Apply mutations
        #[arg(short, long)]
        mutate: bool,
    },

    /// Run phantom RPC simulation
    Simulate {
        /// Simulation mode (burst, steady, random)
        #[arg(short, long, default_value = "steady")]
        mode: String,

        /// Number of ticks
        #[arg(short, long, default_value = "100")]
        ticks: u64,

        /// Target endpoint
        #[arg(short, long, default_value = "http://localhost:8545")]
        endpoint: String,
    },

    /// Export simulation state
    Export {
        /// Output filename
        #[arg(short, long, default_value = "phantom_state.json")]
        output: String,
    },
}

#[derive(Subcommand, Debug)]
enum MeshAction {
    /// Build mesh from points
    Build {
        /// Input file with points (JSON array)
        #[arg(short, long)]
        input: PathBuf,

        /// Mesh mode (knn, radius, complete)
        #[arg(short, long, default_value = "knn")]
        mode: String,

        /// k parameter for kNN
        #[arg(short, long, default_value = "5")]
        k: usize,
    },

    /// Analyze mesh topology
    Analyze {
        /// Input mesh file (JSON)
        #[arg(short, long)]
        input: PathBuf,
    },

    /// Generate random test mesh
    Generate {
        /// Number of points
        #[arg(short, long, default_value = "100")]
        points: usize,

        /// Number of dimensions
        #[arg(short, long, default_value = "5")]
        dims: usize,

        /// Output filename
        #[arg(short, long, default_value = "mesh.json")]
        output: String,
    },
}

fn setup_logging(verbosity: u8) {
    let level = match verbosity {
        0 => Level::WARN,
        1 => Level::INFO,
        2 => Level::DEBUG,
        _ => Level::TRACE,
    };

    let subscriber = FmtSubscriber::builder()
        .with_max_level(level)
        .with_target(false)
        .finish();

    tracing::subscriber::set_global_default(subscriber).expect("setting default subscriber failed");
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    setup_logging(cli.verbose);

    match cli.command {
        Commands::Init { force } => {
            if cli.config.exists() && !force {
                eprintln!("Config file already exists. Use --force to overwrite.");
                std::process::exit(1);
            }
            Config::create_default(&cli.config)?;
            println!("Created default configuration: {}", cli.config.display());
        }

        Commands::Info => {
            println!("AinSOFT - Universal Web3 Research Framework");
            println!("Version: {}", ainsoft::VERSION);
            println!();
            println!("Modules:");
            println!("  - core: Resonance systems, oscillators, feedback loops");
            println!("  - web3: Seed phrase encoding, clustering, Phosphoros kernel");
            println!("  - phantomload: Phantom RPC simulation, cell management");
            println!("  - mesh: Point clouds, topology, triangulation");
            println!("  - scan: Network probing, signal analysis");
            println!();
            println!("Config file: {}", cli.config.display());
        }

        Commands::Web3 { action } => match action {
            Web3Action::Encode { phrases, mutate, format } => {
                let mut kernel = PhosphorosKernel::default();

                let mut results = Vec::new();
                for phrase in &phrases {
                    let geometry = kernel.add_seed_phrase(phrase, mutate);
                    results.push(serde_json::json!({
                        "phrase": phrase,
                        "geometry": geometry.as_slice(),
                        "norm": geometry.norm()
                    }));
                }

                if format == "csv" {
                    println!("phrase,g0,g1,g2,g3,g4,norm");
                    for r in &results {
                        let g = r["geometry"].as_array().unwrap();
                        println!(
                            "{},{},{},{},{},{},{:.4}",
                            r["phrase"].as_str().unwrap(),
                            g[0], g[1], g[2], g[3], g[4],
                            r["norm"].as_f64().unwrap()
                        );
                    }
                } else {
                    println!("{}", serde_json::to_string_pretty(&results)?);
                }
            }

            Web3Action::Cluster { input, clusters } => {
                let content = std::fs::read_to_string(&input)?;
                let phrases: Vec<&str> = content.lines().filter(|l| !l.is_empty()).collect();

                let mut kernel = PhosphorosKernel::with_config(
                    ainsoft::web3::kernel::KernelConfig {
                        n_clusters: clusters,
                        ..Default::default()
                    }
                );

                for phrase in &phrases {
                    kernel.add_seed_phrase(phrase, false);
                }

                let labels = kernel.cluster();
                let score = kernel.silhouette_score();

                println!("Clustered {} phrases into {} clusters", phrases.len(), clusters);
                println!("Silhouette score: {:.4}", score);
                println!();
                for (phrase, label) in phrases.iter().zip(labels.iter()) {
                    println!("  [{}] {}", label, phrase);
                }
            }

            Web3Action::Run { ticks } => {
                info!("Starting Phosphoros kernel...");
                let mut kernel = PhosphorosKernel::default();

                let max_ticks = ticks.unwrap_or(10);
                for i in 0..max_ticks {
                    kernel.tick();
                    if i % 10 == 0 {
                        info!("Tick {} completed", i);
                    }
                }

                let output = cli.output.unwrap_or_else(|| PathBuf::from("."));
                let path = kernel.export_state("web3_state.json")?;
                println!("Exported state to: {}", path.display());
            }
        },

        Commands::Phantom { action } => match action {
            PhantomAction::Spawn { count, seed, mutate } => {
                let mut kernel = PhantomloadKernel::default();
                let ids = kernel.spawn_cells(count, &seed, mutate);

                println!("Spawned {} phantom cells:", ids.len());
                for id in &ids {
                    println!("  - {}", id);
                }
            }

            PhantomAction::Simulate { mode, ticks, endpoint } => {
                info!("Starting phantom simulation: mode={}, ticks={}", mode, ticks);
                let mut kernel = PhantomloadKernel::default();

                // Spawn some cells first
                kernel.spawn_cells(10, "phantom", true);
                kernel.start_wave(&mode, "default", &endpoint);

                for i in 0..ticks {
                    kernel.tick();
                    if i % 10 == 0 {
                        let status = kernel.status();
                        info!("Tick {}: cells={}", i, status["cell_count"]);
                    }
                }

                kernel.stop_wave();
                println!("Simulation completed: {} ticks", ticks);

                let status = kernel.status();
                println!("{}", serde_json::to_string_pretty(&status)?);
            }

            PhantomAction::Export { output } => {
                let kernel = PhantomloadKernel::default();
                let path = kernel.export_state(&output)?;
                println!("Exported to: {}", path.display());
            }
        },

        Commands::Mesh { action } => match action {
            MeshAction::Build { input, mode, k } => {
                let content = std::fs::read_to_string(&input)?;
                let points: Vec<Vec<f64>> = serde_json::from_str(&content)?;

                let mesh_mode = match mode.as_str() {
                    "knn" => ainsoft::mesh::MeshMode::Knn,
                    "radius" => ainsoft::mesh::MeshMode::Radius,
                    "complete" => ainsoft::mesh::MeshMode::Complete,
                    _ => ainsoft::mesh::MeshMode::Knn,
                };

                let config = MeshLayerConfig {
                    mode: mesh_mode,
                    k,
                    ..Default::default()
                };

                let mut layer = MeshLayer::new(points, config);
                layer.build_mesh();
                layer.weight_edges_default();

                println!("Built mesh:");
                println!("  Points: {}", layer.point_count());
                println!("  Edges: {}", layer.edge_count());

                let (coherent, betti) = layer.check_topology();
                println!("  Coherent: {}", coherent);
                println!("  Betti numbers: {:?}", betti);

                let output = cli.output.unwrap_or_else(|| PathBuf::from("."));
                let path = layer.export_json("mesh_output.json")?;
                println!("Exported to: {}", path.display());
            }

            MeshAction::Analyze { input } => {
                let content = std::fs::read_to_string(&input)?;
                let data: serde_json::Value = serde_json::from_str(&content)?;

                let points: Vec<Vec<f64>> = serde_json::from_value(data["points"].clone())?;
                let mut layer = MeshLayer::new(points, Default::default());
                layer.build_mesh();
                layer.weight_edges_default();

                let (coherent, betti) = layer.check_topology();
                let (stable, entropy) = layer.check_entropy();

                println!("Mesh Analysis:");
                println!("  Points: {}", layer.point_count());
                println!("  Edges: {}", layer.edge_count());
                println!("  Coherent: {}", coherent);
                println!("  Betti numbers: {:?}", betti);
                println!("  Entropy: {:.4}", entropy);
                println!("  Stable: {}", stable);
            }

            MeshAction::Generate { points, dims, output } => {
                use rand::Rng;
                let mut rng = rand::thread_rng();

                let point_data: Vec<Vec<f64>> = (0..points)
                    .map(|_| (0..dims).map(|_| rng.gen_range(0.0..100.0)).collect())
                    .collect();

                let mut layer = MeshLayer::new(point_data, Default::default());
                layer.build_mesh();
                layer.weight_edges_default();

                let path = layer.export_json(&output)?;
                println!("Generated mesh with {} points, {} dims", points, dims);
                println!("Exported to: {}", path.display());
            }
        },
    }

    Ok(())
}
