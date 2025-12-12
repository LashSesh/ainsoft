# AinSOFT – Celestial Resonance Impulse Engine

AinSOFT is a modern, modularly designed Python system for adaptive network experiments, payload orchestration, and
resonance-based decision-making. The stack combines a fully asynchronous probe/response pipeline, fixed-point attractor
optimization, agent-based blueprint components, 5D mesh topologies, and optional SOCKS5 proxies for all network connections.

---

## Table of Contents
- [Feature Overview](#feature-overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [CLI](#cli)
  - [REST-API](#rest-api)
  - [Python-API](#python-api)
  - [Fixed-Point Attractor](#fixed-point-attractor)
- [Pipeline Orchestrator](#pipeline-orchestrator)
- [MeshLayer](#meshlayer)
- [Hyperbion Sensorium & Seraphic Feedback](#hyperbion-sensorium--seraphic-feedback)
- [Ouroboros Trading Swarm](#ouroboros-trading-swarm)
- [Quantum-Bionic Field Integration](#quantum-bionic-field-integration)
- [AinSOFT Web3 Suite & ShadowGraph API](#ainsoft-web3-suite--shadowgraph-api)
- [Proxy Support](#proxy-support)
- [Tests](#tests)
- [Docker](#docker)
- [Project Structure](#project-structure)
- [Advanced Modules & Blueprints](#advanced-modules--blueprints)
- [Troubleshooting & Tips](#troubleshooting--tips)

---

## Feature Overview
- **Probe/Resonance Cycles**: UDP probes, response collectors, and signal analysis with adaptive thresholds.
- **Fixed-Point Attractor**: WT/DK/PI/SW operator chain with Mandorla consensus, DTT modulators, and feedback loops.
- **Pipeline Orchestration**: Plug-and-play generators, transformers (including steganography, HTTP builder), and dispatchers.
- **MeshLayer**: 5D/ND point clouds, triangulation, audit logging, topology and entropy control, REST management.
- **Blueprint Library**: GabrielCell swarms, Tripolar Resonance Modules, Emotion Regulation, Kyberios agent cores,
  HDAG state graphs, Vesica/Mandorla overlap checks, and Hyperbion/Seraphic Sensorium components.
- **Ouroboros Trading Swarm**: Multi-layer finance/DeFi layer with GabrielCell farms, Kyberios supervision,
  Field Tensor Routing, ShadowChain audit, and Consensus Staircase Protocol (CSP) for atomic execution.
- **Quantum-Bionic Field Integration**: CHAIOT-QDASH-compliant field operators (FieldState, TripolarResonanceKernel,
  Mandorla Field, Oriphiel5D, QLOGIC, O.P.H.A.N., CubeZoom) for epigenetic strategy mutations and dynamic
  layer mounts in the resonance field.
- **Proxy Capability**: Every network connection (sockets, dispatchers, impulses, probe emitters, etc.) supports
  configurable SOCKS5 proxies via PySocks.

---

## Architecture
AinSOFT is divided into several subsystems that can be used individually or in combination:

1. **Core (`ainsoft.core`)** – Resonance calculation, adaptive thresholds, feedback, impulse generation, and proxy socket helpers.
2. **Scan (`ainsoft.scan`)** – Probe emitters, response observers, and signal analyzers with optional proxy forwarding.
3. **Orchestrator (`ainsoft.orchestrator`)** – Scheduler, lifecycle, agent state, and the fixed-point attractor engine.
4. **Pipeline (`ainsoft.pipeline`)** – Generators, transformers, dispatchers, scorers, steganography, AION pipelines,
   fixed-point builders, MeshLayer blueprints, Hyperbion/Seraphic cores, and Ouroboros trading modules.
5. **Blueprints (`ainsoft.pipeline.blueprints`)** – Advanced agent and feedback modules (GabrielCell, Kyberios, DTT, etc.).
6. **Hyperbion (`ainsoft.pipeline.hyperbion`)** – Bio-resonant modules, sensorium cells, FSM gates, Seraphic feedback,
   audit/registry utilities, and state export.
7. **Configuration (`ainsoft.config`)** – Python defaults and YAML schema, including proxy settings and pipeline layouts.
8. **Interfaces (`ainsoft.interfaces`)** – CLI, FastAPI server, and logger.
9. **Tests (`ainsoft.tests`)** – Pytest suite for core logic, pipelines, proxy helpers, and MeshLayer.

Each module can be used independently or connected via the pipeline orchestrator. Operators and generators can be
registered via import strings or directly as callables.

---

## Prerequisites
- Python ≥ 3.11
- Recommended: Virtual environment (`python -m venv .venv`)
- Optional: Docker (for containerized operation)
- Optional: SciPy (for Delaunay triangulation in MeshLayer; k-NN mode works without SciPy)

---

## Installation
```bash
# Clone repository
git clone <repo-url>
cd ainsoft

# Optional virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -e .
```
Required dependencies are `click`, `fastapi`, `uvicorn`, `numpy`, `PySocks`, and `PyYAML`. For full mesh support,
`scipy` can be additionally installed.

---

## Configuration
Default values are located in `ainsoft/config/defaults.py` and `ainsoft/config/schema.yaml`. The YAML file can serve as
a central source from which CLI, API, or Python modules load pipeline, fixed-point, and proxy settings.

```yaml
pipeline:
  generators:
    - ainsoft.pipeline.scorpiosync_generators:fake_api_request_generator
  transformers:
    - ainsoft.pipeline.scorpiosync_generators:http_builder_transformer
    - ainsoft.pipeline.scorpiosync_generators:steganography_transformer
  dispatchers:
    - ainsoft.pipeline.network_dispatcher:network_dispatcher
fixpunkt:
  scorer: ainsoft.pipeline.triton_scorer:triton_scorer
  threshold_range: [0.1, 0.2, 0.3, 0.4, 0.5]
  consensus:
    callable: ainsoft.pipeline.fixpunktattraktor:mandorla_consensus
    kwargs: {threshold: 0.75}
proxy:
  enabled: false
  host: 127.0.0.1
  port: 1080
  username: null
  password: null
mesh:
  mode: knn
  k: 3
```

The pipeline builder automatically loads modules via `importlib`. Custom components can be integrated via fully qualified
names or as callables (during manual construction).

---

## Usage
### CLI
Start resonance cycles (Probe → Analysis → Impulse) directly from the shell:
```bash
python -m ainsoft.interfaces.cli 127.0.0.1 --port 8080 --cycles 3 --no-proxy
```
Proxy parameters can be set inline:
```bash
python -m ainsoft.interfaces.cli example.com --cycles 5 \
    --proxy-enabled --proxy-host 127.0.0.1 --proxy-port 1080
```

### REST-API
```bash
uvicorn ainsoft.interfaces.api:app --host 0.0.0.0 --port 8000
```
A cycle can then be triggered:
```bash
curl -X POST "http://localhost:8000/cycle/?target=127.0.0.1&port=8080"
```
Extended endpoints (e.g., MeshLayer) are available under `ainsoft.pipeline.meshlayer` and can be integrated into custom
FastAPI apps.

### Python-API
All modules can be orchestrated programmatically:
```python
from ainsoft.orchestrator.lifecycle import run_lifecycle_cycle
from ainsoft.config.defaults import DEFAULT_PROXY_CONFIG

run_lifecycle_cycle("127.0.0.1", 8080, proxy_config=DEFAULT_PROXY_CONFIG)
```

### Fixed-Point Attractor
```python
from ainsoft.config.defaults import DEFAULT_PROXY_CONFIG
from ainsoft.pipeline.aion_pipeline import (
    load_pipeline_config,
    build_fixpunkt_engine_from_config,
)

config = load_pipeline_config()
engine = build_fixpunkt_engine_from_config(config, proxy_cfg=DEFAULT_PROXY_CONFIG)
result = engine.run()
print("Fixed-point attractor:", result)
```
The engine uses WT/DK/PI/SW operators, Mandorla consensus, DTT modulators, and feedback components to identify the most
stable channel.

### Pipeline Orchestrator
```python
from ainsoft.pipeline.aion_pipeline import (
    build_orchestrator_from_config,
    load_pipeline_config,
)

config = load_pipeline_config()
orchestrator = build_orchestrator_from_config(config["pipeline"])
orchestrator.run(proxy_cfg=config.get("proxy"))
```
Generators → Transformers → Dispatchers are executed sequentially. Additional modules can be added in the YAML file or via
Python lists.

### MeshLayer
```python
import numpy as np
from ainsoft.pipeline.meshlayer import MeshLayer, example_score_func, example_grad_func

points = np.random.rand(10, 5)
mesh = MeshLayer(points, mode="knn", k=3)
mesh.build_mesh()
mesh.weight_edges(example_score_func)
mesh.solve()
mesh.gate(0.5)
clusters = mesh.coagula()
mesh.expand(example_grad_func, step=0.05)
print("Audit trail:", mesh.audit())
print("Clusters:", clusters)
```
MeshLayer supports audit logging, entropy control, export/import, and REST integration. SciPy enables Delaunay
triangulation; without SciPy, k-NN mode is automatically used.

### Hyperbion Sensorium & Seraphic Feedback
```python
from ainsoft.pipeline.hyperbion import (
    HyperbionModule,
    SensoriumCell,
    FSMCore,
    MandorlaField,
    Oriphiel5DMemory,
    SeraphicFeedbackModule,
)

# Hyperbion growth / fusion
root = HyperbionModule(name="root")
child_a = root.grow()
child_b = root.grow()
fused = child_a.fuse(child_b)

# Sensorium field with resonance gating
cells = [SensoriumCell() for _ in range(4)]
for left, right in zip(cells, cells[1:]):
    left.add_neighbor(right)
    right.add_neighbor(left)

fsm = FSMCore(threshold=0.65)
for cell in cells:
    fsm.gate(cell)

mandorla = MandorlaField()
memory = Oriphiel5DMemory()
for cell in cells:
    overlap = mandorla.update(cell.state, fused.state)
    memory.add_state(overlap)

feedback = SeraphicFeedbackModule()
pulse = feedback.process_feedback([0.4, 0.8, 0.2, 0.1, 0.6])
```
Hyperbion modules provide bio-resonant agent cores that can grow, mutate, and fuse. Sensorium cells measure
resonance with neighbors, `FSMCore` audits proof-of-resonance gates, `MandorlaField` and `Oriphiel5DMemory` combine
perception and intention into spiralized memory, while the Seraphic module embeds feedback pulses.

### Ouroboros Trading Swarm
```python
from ainsoft.pipeline.ouroboros import (
    build_default_swarm,
    KyberiosController,
    ThresholdPolicy,
    FieldTensorRouter,
    ShadowChain,
    CSPStateMachine,
)

swarm = build_default_swarm(num_cells=4)
controller = KyberiosController(swarm, ThresholdPolicy(threshold=0.55))
cycle = controller.run_cycle({"volatility": 0.3, "liquidity": 1.4})

router = FieldTensorRouter()
for response in cycle["responses"]:
    router.route(response, cycle["decision"], lambda msg: msg["score"] > 0.6)

shadow_chain = ShadowChain()
def quorum(intents):
    return len(intents) >= 2

executors = {"cex": lambda legs: True, "dex": lambda legs: True}
csp = CSPStateMachine(shadow_chain, quorum, executors)
csp.open_intents("cycle-42", ["leg-a", "leg-b"])
for leg in ("leg-a", "leg-b"):
    csp.add_intent(leg, {"score": 0.9})
csp.try_quorum(edge=0.95, tau_edge=0.7)
csp.execute([{"route": "multi-hop"}], venue="CEX")
```
The Ouroboros layer extends AinSOFT with a complete, auditable trading/DeFi simulation. GabrielCell farms provide
resonance evaluations, the Kyberios controller aggregates feedback and triggers actions, `FieldTensorRouter` distributes
messages field-based, and `CSPStateMachine` orchestrates atomic multi-leg strategies via the ShadowChain audit log.

### Quantum-Bionic Field Integration
```python
from ainsoft.pipeline import (
    ResonanceFieldState,
    ResonanceOperatorRegistry,
    GabrielFieldCell,
    MandorlaConvergenceField,
    QuantumOriphiel5DMemory,
    TripolarResonanceKernel,
    FieldTopologicalAdapter,
    TINTATransducer,
    QLogicKernel,
    OphanKernel,
    CubeZoomLayer,
    EpigeneticOperator,
    quantum_default_trident,
    quantum_default_modulator,
)

field_state = ResonanceFieldState({"omega": 0.8, "phase_bias": 0.4})
context = ResonanceFieldState({"baseline": 0.55, "spectrum": 0.7})

mandorla = MandorlaConvergenceField()
memory = QuantumOriphiel5DMemory()

cell = GabrielFieldCell(quantum_default_trident, memory, mandorla, quantum_default_modulator)
tripolar = TripolarResonanceKernel()
adapter = FieldTopologicalAdapter()
tinta = TINTATransducer()
qlogic = QLogicKernel()

events: list[str] = []

def trigger(state):
    events.append(f"singularity@{state.get('tripolar_output'):.2f}")

ophan = OphanKernel(trigger)
cube = CubeZoomLayer()
meta = EpigeneticOperator()
registry = ResonanceOperatorRegistry()
registry.register("tripolar", tripolar)

for _ in range(3):
    resonance = cell(None, context, field_state)
    tripolar(None, context, field_state)
    adapter(None, context, field_state)
    tinta(None, context, field_state)
    qlogic(None, context, field_state)
    ophan(None, context, field_state)

cube.mount(field_state, {"psi": 0.8, "rho": 0.6}, mode="inline")
meta.mutate(registry)  # Example of epigenetic mutation
```
Field integration follows the CHAIOT-QDASH meta-principle: Each operator acts as a field participant with identical
call signature (`__call__(input, context, field_state)`), `FieldState` manages entropy and shared memory, the Mandorla field
stabilizes perception/intention, while the Tripolar core generates resonance impulses. `QLogicKernel` analyzes field
entropy, `OphanKernel` triggers singularity events, and `CubeZoomLayer` enables dynamic overlay/inline mounts.
Epigenetic operators can register new variants at runtime, making AinSOFT fully field-based and self-healing.

### AinSOFT Web3 Suite & ShadowGraph API
```python
from ainsoft.config import load_phosphoros_web3_config
from ainsoft.pipeline import (
    PhosphorosKernel,
    ScorpioBridge,
    SeedDNAEngine,
    MutationEngine,
    SeedClusterEngine,
)
import time

config = load_phosphoros_web3_config()
kernel = PhosphorosKernel.from_config(config)
kernel.add_seed_phrase("seed phrase 1", mutate=True)
kernel.add_seed_phrase("seed phrase 2")
kernel.cluster()
kernel.bridge.start()
time.sleep(0.05)
kernel.bridge.stop()
kernel.export_state()
```
- **Core Modules:** `ScorpioBridge` provides the heartbeat (0.017 s standard), `SeedDNAEngine` generates 5D geometries,
  `MutationEngine` mutates seeds, `SeedClusterEngine` groups geometries, `SupervisorInterface`, `MetaMemoryCore`, and
  `ReverbRing` log activity. `PhosphorosKernel` connects all components for complete Web3 workflows.
- **Configuration & Loader:** The reference is located in `config/phosphoros_web3.yaml` and can be loaded or extended with
  `ainsoft.config.load_phosphoros_web3_config()`.
- **Export & Visualization:** `ExportModule` generates JSON/CSV snapshots (compatible with Seraphic Swarm), heatmaps can
  be accessed directly via `ReverbRing.get_heatmap()`. The kernel `tick` callback is automatically registered when the
  bridge is enabled in the configuration.

### AinSOFT Phantomload & GhostRPC Expansion
```python
from ainsoft.config import load_phantomload_config
from ainsoft.pipeline import (
    PhantomloadKernel,
    GhostRPCEngine,
    OuroborosQuadrupole,
    ProxyManager,
)

config = load_phantomload_config()
kernel = PhantomloadKernel.from_config(config, export_dir="./exports")
kernel.trigger(mode="sybil", nodes=12, mutate=True, autostart=False)
kernel.tick()  # manually execute a quadrupole pulse
status = kernel.status()
mesh = kernel.mesh_snapshot()
kernel.export_mesh(format="json", filename="phantom_mesh.json")
kernel.stop()
```
- **GhostRPC Engine:** Simulates phantom nodes, generates traffic waves with proxy rotation (`ProxyManager`), and automatically
  removes inactive participants via an idle timeout.
- **OuroborosQuadrupole:** Four-phase breath/clock generator that switches active channels on each `tick()`, providing
  unpredictable pulse sequences.
- **SeedDNA/Mutation Integration:** `PhantomloadKernel` uses existing seed/mutation components from the Web3 package
  to store each phantom identity as a 5D resonance vector in the mesh.
- **Supervisor & MetaMemory:** Activity values land in `SupervisorInterface`, long-term storage in `MetaMemoryCore`,
  while `ReverbRing` provides heatmap snapshots for live visualization.
- **REST Flow:** The FastAPI interface offers `/phantomload/trigger`, `/phantomload/status`, `/phantomload/stop`, and
  `/mesh/export?format=json|csv|obj` for Unity/VR imports. Changes can be applied live via `/supervisor/set`.
- **Configuration:** Reference values are under `config/phantomload.yaml` and can be loaded with
  `ainsoft.config.load_phantomload_config()`. Key parameters: Heartbeat (`bridge.heartbeat`), quadrupole mode,
  default node count, proxy lists, and mesh export settings.

## Seraphic Swarm Unity Visualizer
For high-quality 3D visualization of MeshLayer and fixed-point exports, a Unity project is included under
`unity/AinSOFTSeraphicSwarm`. Key highlights:

- **Editor Version:** Unity 2022.3 LTS with Universal Render Pipeline.
- **Packages:** `com.unity.nuget.newtonsoft-json`, `NativeWebSocket` (or compatible), URP, TextMeshPro.
- **Scripts:**
  - `MeshManager` – loads StreamingAssets (`mesh.json`, `mesh_0001.json`, …), performs timeline/playback, animates nodes/edges,
    and processes WebSocket updates (`ws://localhost:8765`, configurable in `MeshConfig`).
  - `MeshTimelineController` – UI for scrubbing, play/pause, snapshot labels.
  - `MeshInteractionController` – selection, info panel, cluster highlighting, and camera focus.
  - `OrbitCameraController` – mouse/touch orbit, pan & zoom.
  - `WebSocketMeshClient` + `UnityMainThreadDispatcher` – live streaming of mesh updates.
- **Visuals:** Glass/crystal materials with emission based on score/weight, Perlin "wind" for organic movement, fade-in/out on
  creation/removal of nodes & edges, score-dependent scaling.
- **UI:** Timeline slider, play/pause, info panel; optional cluster legend and camera lock via inspector.
- **Assets:** Example snapshot `Assets/StreamingAssets/mesh.json` and commented `README.md` in the project directory.

This enables scrubbing, playback, or live streaming and interactive analysis of mesh sequences from AinSOFT.

---

## Proxy Support
All networking functions accept a proxy configuration (`dict` or object with `enabled`, `host`, `port`, `username`,
`password`). When `enabled=True`, sockets are created via `socks.socksocket` and configured with the specified parameters.
Otherwise, regular `socket.socket` instances are used.

Proxy configs can be loaded via CLI flags, REST endpoints, Python APIs, or YAML. The helper function
`create_socket_with_optional_proxy` is located in `ainsoft.core.network` and is used by all networking modules.

---

## Tests
```bash
pytest
```
Tests cover probe emission, resonance calculation, pipeline and fixed-point flow, proxy sockets, and MeshLayer
(excluding optional SciPy features).

---

## Docker
```bash
docker build -t ainsoft .
docker run --rm ainsoft
```
The container entry script runs three CLI cycles against `127.0.0.1` by default. Alternative commands or proxy options
can be passed via `docker run ainsoft python -m ainsoft.interfaces.cli …`.

---

## Project Structure
```
ainsoft/
├── core/            # Resonance logic, impulses, thresholds, proxy helpers
├── scan/            # Probes, listeners, signal analyzer
├── orchestrator/    # Lifecycle, scheduler, fixed-point attractor
├── pipeline/        # Generators, transformers, dispatchers, MeshLayer, blueprints, Hyperbion
├── config/          # Defaults & YAML schema
├── interfaces/      # CLI, REST-API, logging
└── tests/           # Pytest suite
```

---

## Advanced Modules & Blueprints
- **GabrielCell / Kyberios / KyberiotesField** – Agent and swarm components for decentralized pipelines.
- **Tripolar Resonance Module (TRM2)** – Multi-polar decision logic for scorers or threshold adjustments.
- **Emotion Regulation Module (ERM)** – Feedback modulation for adaptive thresholds.
- **DTT Modulators** – Time-dependent control of thresholds, resonances, and agent behavior.
- **HDAG** – Hyperdimensional DAGs for context and task management.
- **Vesica/Mandorla Overlap** – Consensus checks for operator chains.
- **Steganography & API Mimicry Transformers** – Realistic payloads and hidden transmission channels.
- **MeshLayer-REST** – Extensible FastAPI endpoints for mesh control.
- **HyperbionModule / SensoriumCell / FSMCore / MandorlaField / SeraphicFeedbackModule** – Bio-resonant subsystems,
  proof-of-resonance gates, spiralized memory, and feedback embedding including audit/state export.
- **Ouroboros GabrielCellSwarm / KyberiosController / FieldTensorRouter / CSPStateMachine / ShadowChain** –
  Finance and DeFi-oriented decision and execution logic with audit trail and quorum control.

All components are implemented as callables and can be mixed in pipeline or fixed-point configurations.

---

## Troubleshooting & Tips
- **SciPy missing**: MeshLayer automatically falls back to k-NN triangulation. For Delaunay, run `pip install scipy`.
- **Proxy errors**: Ensure `PySocks` is installed and host/port are reachable.
- **Custom modules**: Use the schema `module.submodule:callable` so the orchestrator automatically loads components.
- **Audit logging**: MeshLayer operations maintain audit entries; for persistent logs, `StructuredAuditLogger` can be used.
- **State persistence**: MeshLayer has `export_state`/`import_state` and JSON exports for visualization.

With these building blocks, AinSOFT can be deployed as a research platform, orchestrated traffic simulator, adaptive agent
network, or experimental resonance laboratory.
