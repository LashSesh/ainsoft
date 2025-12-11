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
use ainsoft::resonance::{
    CalibratorConfig, HarmonicPattern, HarmonicScheduler, NeedleConfig, NeedleEmitter,
    NeedleType, ResonanceCalibrator, ResonanceMode, SchedulerConfig, SpectralAnalyzer,
    SpectralConfig,
};
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

    /// Network resonance calibration (Shaolin needle method)
    Resonance {
        #[command(subcommand)]
        action: ResonanceAction,
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
enum ResonanceAction {
    /// Calibrate network resonance (find characteristic frequencies)
    Calibrate {
        /// Target endpoints (URLs or addresses)
        #[arg(short, long, required = true)]
        targets: Vec<String>,

        /// Resonance mode (observe, calibrate, map, sweep, adaptive)
        #[arg(short, long, default_value = "observe")]
        mode: String,

        /// Maximum number of probes
        #[arg(short, long, default_value = "100")]
        probes: u64,

        /// Session timeout in seconds
        #[arg(long, default_value = "60")]
        timeout: f64,

        /// Mean interval between probes (seconds)
        #[arg(short, long, default_value = "1.0")]
        interval: f64,

        /// Needle type (whisper, touch, pulse, echo, cipher)
        #[arg(short, long, default_value = "whisper")]
        needle: String,
    },

    /// Generate harmonic timing schedule
    Schedule {
        /// Number of timing slots to generate
        #[arg(short, long, default_value = "50")]
        count: usize,

        /// Harmonic pattern (poisson, brownian, multimodal, circadian, fibonacci, pink)
        #[arg(short, long, default_value = "poisson")]
        pattern: String,

        /// Mean interval (seconds)
        #[arg(short, long, default_value = "1.0")]
        interval: f64,

        /// Minimum interval (seconds)
        #[arg(long, default_value = "0.01")]
        min: f64,

        /// Maximum interval (seconds)
        #[arg(long, default_value = "10.0")]
        max: f64,
    },

    /// Analyze latency spectrum from file
    Spectrum {
        /// Input file with latency samples (JSON array or one per line)
        #[arg(short, long)]
        input: PathBuf,

        /// FFT window size (power of 2)
        #[arg(short, long, default_value = "256")]
        window: usize,

        /// Output format (json, text)
        #[arg(short, long, default_value = "text")]
        format: String,
    },

    /// Test needle emission (dry run)
    Test {
        /// Number of needles to emit
        #[arg(short, long, default_value = "10")]
        count: usize,

        /// Needle type
        #[arg(short, long, default_value = "whisper")]
        needle: String,

        /// Show timing details
        #[arg(short, long)]
        verbose: bool,
    },

    /// Show resonance module information
    Info,
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
            println!("  - resonance: Network calibration (Shaolin needle method)");
            println!();
            println!("Config file: {}", cli.config.display());
        }

        Commands::Resonance { action } => match action {
            ResonanceAction::Calibrate {
                targets,
                mode,
                probes,
                timeout,
                interval,
                needle,
            } => {
                let res_mode = match mode.as_str() {
                    "observe" => ResonanceMode::Observe,
                    "calibrate" => ResonanceMode::Calibrate,
                    "map" => ResonanceMode::Map,
                    "sweep" => ResonanceMode::Sweep,
                    "adaptive" => ResonanceMode::Adaptive,
                    _ => ResonanceMode::Observe,
                };

                let needle_type = match needle.as_str() {
                    "whisper" => NeedleType::Whisper,
                    "touch" => NeedleType::Touch,
                    "pulse" => NeedleType::Pulse,
                    "echo" => NeedleType::Echo,
                    "cipher" => NeedleType::Cipher,
                    _ => NeedleType::Whisper,
                };

                let config = CalibratorConfig {
                    mode: res_mode,
                    max_probes: probes,
                    session_timeout: timeout,
                    needle: NeedleConfig {
                        needle_type,
                        ..Default::default()
                    },
                    scheduler: SchedulerConfig {
                        pattern: res_mode.recommended_pattern(),
                        mean_interval: interval,
                        ..Default::default()
                    },
                    ..Default::default()
                };

                let mut calibrator = ResonanceCalibrator::new(config);
                calibrator.add_targets(targets.iter().map(String::as_str));

                info!("Starting resonance calibration: mode={:?}, targets={}", res_mode, targets.len());
                calibrator.start();

                // Simulation loop (dry run - actual network calls would go here)
                let mut tick = 0u64;
                while calibrator.should_continue() && tick < probes {
                    if let Some(needle) = calibrator.emit() {
                        // In a real implementation, we would send the needle here
                        // and call record_return when response arrives
                        info!("Emitted needle {} to {} (phase={:.2})",
                              needle.id, needle.target, needle.phase);

                        // Simulate response (for demo)
                        let simulated_latency = 10.0 + rand::random::<f64>() * 50.0;
                        calibrator.record_return(needle.id, &needle.target, simulated_latency);
                    }
                    tick += 1;

                    let delay = calibrator.next_delay();
                    std::thread::sleep(delay.min(std::time::Duration::from_millis(100)));
                }

                let result = calibrator.complete();
                println!("\nResonance Calibration Results:");
                println!("  Mode: {:?}", result.mode);
                println!("  Targets: {}", result.targets.len());
                println!("  Probes sent: {}", result.probes_sent);
                println!("  Probes returned: {}", result.probes_returned);
                println!("  Duration: {:.2}s", result.duration);
                println!("  Mean latency: {:.2}ms", result.mean_latency_ms);
                println!("  Latency std: {:.2}ms", result.latency_std_ms);

                if !result.resonance_frequencies.is_empty() {
                    println!("  Resonance frequencies: {:?}", result.resonance_frequencies);
                }

                if !result.auto_tune_adjustments.is_empty() {
                    println!("\nAuto-tune adjustments:");
                    for adj in &result.auto_tune_adjustments {
                        println!("    {}", adj);
                    }
                }

                // Export results
                let output_path = cli.output.unwrap_or_else(|| PathBuf::from("."));
                let filename = output_path.join("resonance_result.json");
                let json = serde_json::to_string_pretty(&result)?;
                std::fs::write(&filename, json)?;
                println!("\nExported to: {}", filename.display());
            }

            ResonanceAction::Schedule { count, pattern, interval, min, max } => {
                let harm_pattern = match pattern.as_str() {
                    "poisson" => HarmonicPattern::Poisson,
                    "brownian" => HarmonicPattern::Brownian,
                    "multimodal" => HarmonicPattern::MultiModal,
                    "circadian" => HarmonicPattern::Circadian,
                    "fibonacci" => HarmonicPattern::Fibonacci,
                    "pink" => HarmonicPattern::PinkNoise,
                    _ => HarmonicPattern::Poisson,
                };

                let config = SchedulerConfig {
                    pattern: harm_pattern,
                    mean_interval: interval,
                    min_interval: min,
                    max_interval: max,
                    ..Default::default()
                };

                let mut scheduler = HarmonicScheduler::new(config);
                let slots = scheduler.generate_slots(count);
                let stats = scheduler.stats(&slots);

                println!("Harmonic Schedule ({:?} pattern):", harm_pattern);
                println!("  Slots generated: {}", slots.len());
                println!("  Mean delay: {:.4}s", stats.mean_delay);
                println!("  Std deviation: {:.4}s", stats.std_dev);
                println!("  CV: {:.2}", stats.coefficient_of_variation);
                println!("  Total time: {:.2}s", stats.total_time);
                println!();
                println!("First 10 slots:");
                for slot in slots.iter().take(10) {
                    println!("  #{}: delay={:.4}s, phase={:.2}, amplitude={:.2}",
                             slot.sequence, slot.delay, slot.phase, slot.amplitude);
                }
            }

            ResonanceAction::Spectrum { input, window, format } => {
                let content = std::fs::read_to_string(&input)?;

                // Try to parse as JSON array first, then as line-separated values
                let samples: Vec<f64> = if content.trim().starts_with('[') {
                    serde_json::from_str(&content)?
                } else {
                    content.lines()
                        .filter_map(|l| l.trim().parse::<f64>().ok())
                        .collect()
                };

                if samples.is_empty() {
                    eprintln!("No samples found in input file");
                    std::process::exit(1);
                }

                let config = SpectralConfig {
                    window_size: window,
                    ..Default::default()
                };

                let mut analyzer = SpectralAnalyzer::new(config);

                // Add samples with synthetic timestamps
                for (i, &sample) in samples.iter().enumerate() {
                    analyzer.add_sample(sample, i as f64 * 0.1);
                }

                if let Some(result) = analyzer.analyze() {
                    if format == "json" {
                        println!("{}", serde_json::to_string_pretty(&result)?);
                    } else {
                        println!("Spectral Analysis Results:");
                        println!("  Samples analyzed: {}", samples.len());
                        println!("  Sample rate: {:.2} Hz", result.sample_rate);
                        println!("  Dominant frequency: {:.4} Hz", result.dominant_freq);
                        println!("  Total energy: {:.4}", result.total_energy);
                        println!("  Spectral centroid: {:.4} Hz", result.centroid);
                        println!("  Spectral spread: {:.4} Hz", result.spread);

                        if !result.resonance_points.is_empty() {
                            println!("\nResonance points detected:");
                            for rp in &result.resonance_points {
                                println!("  - {:.4} Hz (Q={:.2}, amplitude={:.4})",
                                         rp.frequency, rp.q_factor, rp.amplitude);
                            }
                        }

                        let peaks: Vec<_> = result.bins.iter().filter(|b| b.is_peak).collect();
                        if !peaks.is_empty() {
                            println!("\nSpectral peaks:");
                            for peak in peaks.iter().take(5) {
                                println!("  - {:.4} Hz: magnitude={:.4}",
                                         peak.frequency, peak.magnitude);
                            }
                        }
                    }
                } else {
                    eprintln!("Not enough samples for spectral analysis (need {} samples)", window);
                    std::process::exit(1);
                }
            }

            ResonanceAction::Test { count, needle, verbose } => {
                let needle_type = match needle.as_str() {
                    "whisper" => NeedleType::Whisper,
                    "touch" => NeedleType::Touch,
                    "pulse" => NeedleType::Pulse,
                    "echo" => NeedleType::Echo,
                    "cipher" => NeedleType::Cipher,
                    _ => NeedleType::Whisper,
                };

                let config = NeedleConfig {
                    needle_type,
                    min_interval_us: 1000, // 1ms for testing
                    ..Default::default()
                };

                let mut emitter = NeedleEmitter::new(config);
                emitter.add_target("test-target-1");
                emitter.add_target("test-target-2");

                println!("Needle Emission Test ({:?}):", needle_type);
                println!("  Payload size: {} bytes", needle_type.payload_size());
                let (min_lat, max_lat) = needle_type.expected_latency_range();
                println!("  Expected latency: {:.1}-{:.1}ms", min_lat, max_lat);
                println!();

                for i in 0..count {
                    if let Some(n) = emitter.emit_next(i as u32, (i as f64) / count as f64) {
                        if verbose {
                            println!("  #{}: id={}, target={}, fp={:08x}, phase={:.2}",
                                     i, n.id, n.target, n.fingerprint, n.phase);
                        }
                        // Simulate return
                        emitter.record_return(n.id);
                    }
                }

                let stats = emitter.stats();
                println!("\nStatistics:");
                println!("  Total emitted: {}", stats.total_emitted);
                println!("  Total returned: {}", stats.total_returned);
                println!("  Return rate: {:.1}%", stats.return_rate * 100.0);
            }

            ResonanceAction::Info => {
                println!("AinSOFT Resonance Module - Shaolin Needle Method");
                println!();
                println!("The resonance module provides precision network calibration tools");
                println!("that blend naturally with ambient traffic patterns.");
                println!();
                println!("Components:");
                println!("  - NeedleEmitter: Micro-probes with sub-ms timing control");
                println!("  - SpectralAnalyzer: Frequency-domain latency analysis");
                println!("  - HarmonicScheduler: Traffic-blending timing patterns");
                println!("  - ResonanceCalibrator: Orchestration for network research");
                println!();
                println!("Needle Types:");
                println!("  - whisper: Single-byte timing probe (minimal footprint)");
                println!("  - touch: HTTP HEAD request timing");
                println!("  - pulse: TCP SYN timing measurement");
                println!("  - echo: DNS resolution timing");
                println!("  - cipher: TLS handshake timing");
                println!();
                println!("Harmonic Patterns:");
                println!("  - poisson: Natural traffic distribution");
                println!("  - brownian: Random walk with drift");
                println!("  - multimodal: Human-like interaction patterns");
                println!("  - circadian: Daily activity rhythms");
                println!("  - fibonacci: Golden ratio spacing");
                println!("  - pink: 1/f frequency distribution");
                println!();
                println!("Resonance Modes:");
                println!("  - observe: Passive, minimal footprint");
                println!("  - calibrate: Active resonance point detection");
                println!("  - map: Network topology modeling");
                println!("  - sweep: Full spectrum analysis");
                println!("  - adaptive: Self-tuning based on responses");
            }
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
