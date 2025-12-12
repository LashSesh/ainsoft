# AinSOFT - Universal Web3 Research Framework

A universal research framework for Web3 resonance networks and mesh topology analysis, written in Rust.

## Overview

AinSOFT provides tools for:

- **Core resonance systems**: Oscillators, feedback loops, and adaptive thresholds
- **Web3 integration**: Phantom wallet simulation, seed phrase geometry encoding
- **Mesh topology**: N-dimensional point clouds, kNN graphs, topology analysis
- **Network probing**: Signal analysis and response observation

## Installation

```bash
cargo install --path .
```

Or build from source:

```bash
cargo build --release
```

## Usage

### CLI Commands

```bash
# Show framework information
ainsoft info

# Initialize configuration
ainsoft init

# Web3 Commands
ainsoft web3 encode "seed phrase one" "seed phrase two"
ainsoft web3 cluster -i seeds.txt -k 5
ainsoft web3 run --ticks 100

# Phantom RPC Simulation
ainsoft phantom spawn -c 10 -s "base-seed" --mutate
ainsoft phantom simulate -m steady -t 100 -e "http://localhost:8545"
ainsoft phantom export -o state.json

# Mesh Commands
ainsoft mesh generate -p 100 -d 5 -o mesh.json
ainsoft mesh build -i points.json -m knn -k 5
ainsoft mesh analyze -i mesh.json
```

### Library Usage

```rust
use ainsoft::web3::{SeedDnaEngine, PhosphorosKernel};
use ainsoft::mesh::{MeshLayer, MeshLayerConfig};

// Encode seed phrases to 5D geometry
let engine = SeedDnaEngine::default();
let geometry = engine.encode("example seed phrase");

// Build mesh from points
let points = vec![
    vec![0.0, 0.0, 0.0, 0.0, 0.0],
    vec![1.0, 1.0, 1.0, 1.0, 1.0],
];
let mut mesh = MeshLayer::new(points, MeshLayerConfig::default());
mesh.build_mesh();
mesh.weight_edges_default();

// Check topology
let (coherent, betti) = mesh.check_topology();
println!("Coherent: {}, Betti: {:?}", coherent, betti);
```

## Modules

### Core (`ainsoft::core`)
- `Oscillator` - Resonance value computation
- `Feedback` / `FeedbackLoop` - Feedback mechanisms
- `Threshold` / `AdaptiveThreshold` - Signal gating
- `Substrate` / `SubstrateLayer` - Resonance propagation
- `ProxyConfig` - Network proxy support

### Web3 (`ainsoft::web3`)
- `SeedDnaEngine` - Seed phrase to geometry encoding
- `MutationEngine` - Variant generation
- `SeedClusterEngine` - K-means clustering
- `PhosphorosKernel` - High-level orchestrator
- `ScorpioBridge` - Heartbeat scheduler
- `ExportModule` - Data persistence

### Phantomload (`ainsoft::phantomload`)
- `GhostRpcManager` - RPC wave coordination
- `GhostRpcNode` / `GhostRpcWave` - Node simulation
- `PhantomCell` / `PhantomCellManager` - Cell management
- `PhantomHeatmap` - Activity visualization
- `PhantomloadKernel` - High-level orchestrator

### Mesh (`ainsoft::mesh`)
- `PointCloud` - N-dimensional point storage
- `MeshBuilder` - Graph construction (kNN, radius, complete)
- `MeshLayer` - High-level mesh orchestration
- `TopologyGuard` - Coherence analysis
- `EntropyControl` - Complexity tracking
- Operators: `solve`, `gate`, `coagula`, `expand`

### Scan (`ainsoft::scan`)
- `ProbeEmitter` - Network probe generation
- `ResponseObserver` - Response collection
- `SignalAnalyzer` - Adaptive threshold analysis

## Legacy Python reference

The original Python-based resonance lab (including modules such as `ScorpioSync`, `Fixpunktattraktor`, and the early calibration routines) is archived under [`ainsoft-r-main`](ainsoft-r-main/). It can be used as a reference for pre-Web3 core behaviors alongside the current Rust implementation.

## Configuration

Create `ainsoft.yaml`:

```yaml
phosphoros:
  tick_interval: 0.017
  bridge_enabled: true
  mutation_rate: 0.1
  n_clusters: 3

phantomload:
  heatmap_width: 100
  heatmap_height: 100
  heatmap_decay: 0.95

mesh:
  mode: knn
  k: 5
  max_entropy: 10.0

scan:
  interval: 0.1
  timeout: 5.0
  anomaly_threshold: 2.0

general:
  log_level: info
  verbose: false
```

## License

MIT
