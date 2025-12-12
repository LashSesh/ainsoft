# AinSOFT – Celestial Resonance Impulse Engine

AinSOFT ist ein modernes, modular aufgebautes Python-System für adaptive Netzwerkexperimente, Payload-Orchestrierung und
resonanzbasierte Entscheidungsfindung. Der Stack kombiniert eine vollständig asynchrone Probe-/Response-Pipeline,
Fixpunktattraktor-Optimierung, agentenbasierte Blueprint-Bausteine, 5D-Mesh-Topologien sowie optionale SOCKS5-Proxys für
sämtliche Netzwerkverbindungen.

---

## Inhaltsverzeichnis
- [Funktionsübersicht](#funktionsübersicht)
- [Architektur](#architektur)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Bedienung](#bedienung)
  - [CLI](#cli)
  - [REST-API](#rest-api)
  - [Python-API](#python-api)
  - [Fixpunktattraktor](#fixpunktattraktor)
- [Pipeline-Orchestrator](#pipeline-orchestrator)
- [MeshLayer](#meshlayer)
- [Hyperbion Sensorium & Seraphic Feedback](#hyperbion-sensorium--seraphic-feedback)
- [Ouroboros Trading Swarm](#ouroboros-trading-swarm)
- [Quantenbionische Feldintegration](#quantenbionische-feldintegration)
- [AinSOFT Web3 Suite & ShadowGraph API](#ainsoft-web3-suite--shadowgraph-api)
- [Proxy-Unterstützung](#proxy-unterstützung)
- [Tests](#tests)
- [Docker](#docker)
- [Projektstruktur](#projektstruktur)
- [Weiterführende Module & Blueprints](#weiterführende-module--blueprints)
- [Troubleshooting & Tipps](#troubleshooting--tipps)

---

## Funktionsübersicht
- **Probe-/Resonanz-Zyklen**: UDP-Probes, Response-Kollektoren und Signal-Analyse mit adaptiven Schwellwerten.
- **Fixpunktattraktor**: WT/DK/PI/SW-Operatorenkette mit Mandorla-Konsens, DTT-Modulatoren und Feedback-Schleifen.
- **Pipeline-Orchestrierung**: Plug-and-Play-Generatoren, -Transformer (u. a. Steganografie, HTTP-Builder) und Dispatcher.
- **MeshLayer**: 5D/ND-Punktwolken, Triangulation, Audit-Logging, Topologie- und Entropiekontrolle, REST-Steuerung.
- **Blueprint-Bibliothek**: GabrielCell-Schwärme, Tripolar Resonance Module, Emotion Regulation, Kyberios-Agentenkerne,
  HDAG-Stategraphen, Vesica/Mandorla-Overlap-Checks sowie Hyperbion-/Seraphic-Sensorium-Komponenten.
- **Ouroboros Trading Swarm**: Mehrschichtiger Finanz-/DeFi-Layer mit GabrielCell-Farmen, Kyberios-Supervision,
  Field Tensor Routing, ShadowChain-Audit und Consensus Staircase Protocol (CSP) für atomare Ausführungen.
- **Quantenbionische Feldintegration**: CHAIOT-QDASH-konforme Feldoperatoren (FieldState, TripolarResonanzkern,
  Mandorla-Feld, Oriphiel5D, QLOGIC, O.P.H.A.N., CubeZoom) für epigenetische Strategiemutationen und dynamische
  Layer-Mounts im Resonanzfeld.
- **Proxy-Fähigkeit**: Jede Netzwerkverbindung (Sockets, Dispatcher, Impulse, Probe-Emitter etc.) unterstützt
  konfigurierbare SOCKS5-Proxys via PySocks.

---

## Architektur
AinSOFT gliedert sich in mehrere Subsysteme, die einzeln oder kombiniert genutzt werden können:

1. **Core (`ainsoft.core`)** – Resonanzberechnung, adaptive Thresholds, Feedback, Impulserzeugung und Proxy-Socket-Helfer.
2. **Scan (`ainsoft.scan`)** – Probe-Emitter, Response-Observer und Signal-Analyser mit optionaler Proxyweiterleitung.
3. **Orchestrator (`ainsoft.orchestrator`)** – Scheduler, Lifecycle, Agenten-State und die Fixpunktattraktor-Engine.
4. **Pipeline (`ainsoft.pipeline`)** – Generatoren, Transformer, Dispatcher, Scorer, Steganografie, AION-Pipelines,
   Fixpunkt-Builders, MeshLayer-Blueprints, Hyperbion/Seraphic-Kerne und die Ouroboros-Trading-Module.
5. **Blueprints (`ainsoft.pipeline.blueprints`)** – Erweiterte Agenten- und Feedbackmodule (GabrielCell, Kyberios, DTT usw.).
6. **Hyperbion (`ainsoft.pipeline.hyperbion`)** – Bio-resonante Module, Sensorium-Zellen, FSM-Gates, Seraphic Feedback,
   Audit/Registry-Utilities und State-Export.
7. **Konfiguration (`ainsoft.config`)** – Python-Defaults und YAML-Schema, inkl. Proxy-Settings und Pipeline-Layouts.
8. **Interfaces (`ainsoft.interfaces`)** – CLI, FastAPI-Server und Logger.
9. **Tests (`ainsoft.tests`)** – Pytest-Suite für Kernlogik, Pipelines, Proxy-Helfer und MeshLayer.

Jedes Modul lässt sich eigenständig nutzen oder mit dem Pipeline-Orchestrator verbinden. Operatoren und Generatoren können
per Import-String oder direkt als Callables registriert werden.

---

## Voraussetzungen
- Python ≥ 3.11
- Empfohlen: Virtuelle Umgebung (`python -m venv .venv`)
- Optional: Docker (für Containerbetrieb)
- Optional: SciPy (für Delaunay-Triangulation im MeshLayer; k-NN-Modus funktioniert ohne SciPy)

---

## Installation
```bash
# Repository klonen
git clone <repo-url>
cd ainsoft

# Optionale virtuelle Umgebung
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install --upgrade pip
pip install -e .
```
Pflichtabhängigkeiten sind `click`, `fastapi`, `uvicorn`, `numpy`, `PySocks` und `PyYAML`. Für vollständige Mesh-Unterstützung
kann zusätzlich `scipy` installiert werden.

---

## Konfiguration
Standardwerte befinden sich in `ainsoft/config/defaults.py` und `ainsoft/config/schema.yaml`. Die YAML-Datei kann als
zentrale Quelle dienen, aus der CLI, API oder Python-Module Pipeline-, Fixpunkt- und Proxy-Einstellungen laden.

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

Der Pipeline-Builder lädt Module automatisch über `importlib`. Eigene Komponenten können per vollqualifiziertem Namen oder
als Callables (beim manuellen Aufbau) eingebunden werden.

---

## Bedienung
### CLI
Starte Resonanzzyklen (Probe → Analyse → Impuls) direkt aus der Shell:
```bash
python -m ainsoft.interfaces.cli 127.0.0.1 --port 8080 --cycles 3 --no-proxy
```
Proxy-Parameter lassen sich inline setzen:
```bash
python -m ainsoft.interfaces.cli example.com --cycles 5 \
    --proxy-enabled --proxy-host 127.0.0.1 --proxy-port 1080
```

### REST-API
```bash
uvicorn ainsoft.interfaces.api:app --host 0.0.0.0 --port 8000
```
Anschließend kann ein Zyklus ausgelöst werden:
```bash
curl -X POST "http://localhost:8000/cycle/?target=127.0.0.1&port=8080"
```
Erweiterte Endpunkte (z. B. MeshLayer) stehen unter `ainsoft.pipeline.meshlayer` bereit und lassen sich in eigene FastAPI-
Apps einbinden.

### Python-API
Alle Module können programmgesteuert orchestriert werden:
```python
from ainsoft.orchestrator.lifecycle import run_lifecycle_cycle
from ainsoft.config.defaults import DEFAULT_PROXY_CONFIG

run_lifecycle_cycle("127.0.0.1", 8080, proxy_config=DEFAULT_PROXY_CONFIG)
```

### Fixpunktattraktor
```python
from ainsoft.config.defaults import DEFAULT_PROXY_CONFIG
from ainsoft.pipeline.aion_pipeline import (
    load_pipeline_config,
    build_fixpunkt_engine_from_config,
)

config = load_pipeline_config()
engine = build_fixpunkt_engine_from_config(config, proxy_cfg=DEFAULT_PROXY_CONFIG)
result = engine.run()
print("Fixpunktattraktor:", result)
```
Die Engine nutzt WT/DK/PI/SW-Operatoren, Mandorla-Konsens, DTT-Modulatoren und Feedback-Bausteine, um den stabilsten Kanal
zu identifizieren.

### Pipeline-Orchestrator
```python
from ainsoft.pipeline.aion_pipeline import (
    build_orchestrator_from_config,
    load_pipeline_config,
)

config = load_pipeline_config()
orchestrator = build_orchestrator_from_config(config["pipeline"])
orchestrator.run(proxy_cfg=config.get("proxy"))
```
Generatoren → Transformer → Dispatcher werden seriell ausgeführt. Zusätzliche Module lassen sich in der YAML-Datei oder per
Python-Liste hinzufügen.

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
Der MeshLayer unterstützt Audit-Logging, Entropiekontrolle, Export/Import und REST-Integration. SciPy ermöglicht Delaunay-
Triangulation, ohne SciPy wird automatisch der k-NN-Modus genutzt.

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
Die Hyperbion-Module liefern bio-resonante Agentenkerne, die wachsen, mutieren und fusionieren können. Sensorium-Zellen messen
Resonanz mit Nachbarn, `FSMCore` auditiert Proof-of-Resonance-Gates, `MandorlaField` und `Oriphiel5DMemory` kombinieren
Perzeption und Intention zu einem spiralisierten Gedächtnis, während das Seraphic-Modul Feedbackimpulse einbettet.

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
Der Ouroboros-Layer ergänzt AinSOFT um eine vollständige, auditierbare Trading-/DeFi-Simulation. GabrielCell-Farmen liefern
Resonanzbewertungen, der Kyberios-Controller fasst Feedback zusammen und löst Aktionen aus, `FieldTensorRouter` verteilt
Nachrichten feldbasiert und `CSPStateMachine` orchestriert atomare Mehrbein-Strategien über den ShadowChain-Auditlog.

### Quantenbionische Feldintegration
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
meta.mutate(registry)  # Beispiel für epigenetische Mutation
```
Die Feldintegration folgt dem CHAIOT-QDASH-Meta-Prinzip: Jeder Operator agiert als Feldteilnehmer mit identischem
Call-Signature (`__call__(input, context, field_state)`), `FieldState` verwaltet Entropie und Shared Memory, das Mandorla-Feld
stabilisiert Perzeption/Intention, während der Tripolar-Kern Resonanz-Impulse erzeugt. `QLogicKernel` analysiert die
Feldentropie, `OphanKernel` löst Singularitätsereignisse aus und `CubeZoomLayer` erlaubt dynamische Overlay-/Inline-Mounts.
Epigenetische Operatoren können zur Laufzeit neue Varianten registrieren, wodurch AinSOFT vollständig feldbasiert und
selbstheilend bleibt.

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
- **Kernmodule:** `ScorpioBridge` liefert den Heartbeat (0.017 s standard), `SeedDNAEngine` erzeugt 5D-Geometrien,
  `MutationEngine` mutiert Seeds, `SeedClusterEngine` gruppiert Geometrien, `SupervisorInterface`, `MetaMemoryCore` und
  `ReverbRing` protokollieren Aktivität. `PhosphorosKernel` verknüpft alle Bausteine für vollständige Web3-Workflows.
- **Konfiguration & Loader:** Die Referenz befindet sich in `config/phosphoros_web3.yaml` und lässt sich mit
  `ainsoft.config.load_phosphoros_web3_config()` laden oder erweitern.
- **Export & Visualisierung:** `ExportModule` erzeugt JSON-/CSV-Snapshots (kompatibel mit Seraphic Swarm), Heatmaps können
  direkt über `ReverbRing.get_heatmap()` genutzt werden. Das Kernel-`tick`-Callback wird automatisch registriert, wenn die
  Bridge in der Konfiguration aktiviert ist.

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
kernel.tick()  # manuell einen Quadrupol-Puls ausführen
status = kernel.status()
mesh = kernel.mesh_snapshot()
kernel.export_mesh(format="json", filename="phantom_mesh.json")
kernel.stop()
```
- **GhostRPC Engine:** Simuliert Phantom-Nodes, erzeugt Traffic-Wellen samt Proxy-Rotation (`ProxyManager`) und entfernt
  inaktive Teilnehmer automatisch über ein Idle-Timeout.
- **OuroborosQuadrupole:** Vierphasiger Atem-/Taktgenerator, der bei jedem `tick()` die aktiven Channels wechselt und so
  unvorhersehbare Pulsfolgen liefert.
- **SeedDNA-/Mutation-Integration:** `PhantomloadKernel` nutzt die vorhandenen Seed-/Mutationsbausteine aus dem Web3-Paket,
  um jede Phantom-Identität als 5D-Resonanzvektor im Mesh abzulegen.
- **Supervisor & MetaMemory:** Aktivitätswerte landen im `SupervisorInterface`, Langzeitspeicher im `MetaMemoryCore`,
  während `ReverbRing` Heatmap-Snapshots für Live-Visualisierung bereitstellt.
- **REST-Flow:** Die FastAPI-Oberfläche bietet `/phantomload/trigger`, `/phantomload/status`, `/phantomload/stop` sowie
  `/mesh/export?format=json|csv|obj` für Unity/VR-Importe. Änderungen können über `/supervisor/set` live eingespielt werden.
- **Konfiguration:** Referenzwerte liegen unter `config/phantomload.yaml` und lassen sich mit
  `ainsoft.config.load_phantomload_config()` laden. Wichtige Parameter: Heartbeat (`bridge.heartbeat`), Quadrupol-Modus,
  Default-Node-Anzahl, Proxy-Listen und Mesh-Export-Einstellungen.

## Seraphic Swarm Unity Visualizer
Für hochqualitative 3D-Visualisierung der MeshLayer- und Fixpunkt-Exports liegt ein Unity-Projekt unter
`unity/AinSOFTSeraphicSwarm` bei. Wichtige Eckpunkte:

- **Editor-Version:** Unity 2022.3 LTS mit Universal Render Pipeline.
- **Pakete:** `com.unity.nuget.newtonsoft-json`, `NativeWebSocket` (oder kompatibel), URP, TextMeshPro.
- **Skripte:**
  - `MeshManager` – lädt StreamingAssets (`mesh.json`, `mesh_0001.json`, …), führt Timeline/Playback, animiert Nodes/Edges
    und verarbeitet WebSocket-Updates (`ws://localhost:8765`, konfigurierbar in `MeshConfig`).
  - `MeshTimelineController` – UI für Scrubbing, Play/Pause, Snapshot-Beschriftung.
  - `MeshInteractionController` – Selektion, Info-Panel, Cluster-Highlighting und Kamera-Fokus.
  - `OrbitCameraController` – Maus-/Touch-Orbit, Pan & Zoom.
  - `WebSocketMeshClient` + `UnityMainThreadDispatcher` – Live-Streaming der MeshUpdates.
- **Visuals:** Glas-/Kristall-Materialien mit Emission nach Score/Weight, Perlin-"Wind" für organische Bewegung, Fade-in/out bei
  Erzeugung/Entfernung von Nodes & Edges, Score-abhängige Skalierung.
- **UI:** Timeline-Slider, Play/Pause, Info-Panel; optional Cluster-Legende und Kamera-Lock via Inspector.
- **Assets:** Beispiel-Snapshot `Assets/StreamingAssets/mesh.json` sowie kommentierte `README.md` im Projektverzeichnis.

Damit lassen sich Mesh-Sequenzen aus AinSOFT scrubben, abspielen oder live streamen und interaktiv analysieren.

---

## Proxy-Unterstützung
Alle Netzwerkfunktionen akzeptieren eine Proxy-Konfiguration (`dict` oder Objekt mit `enabled`, `host`, `port`, `username`,
`password`). Wenn `enabled=True`, werden Sockets über `socks.socksocket` erzeugt und mit den angegebenen Parametern
konfiguriert. Andernfalls kommen reguläre `socket.socket`-Instanzen zum Einsatz.

Proxy-Configs können über CLI-Flags, REST-Endpunkte, Python-APIs oder YAML geladen werden. Die Helper-Funktion
`create_socket_with_optional_proxy` befindet sich in `ainsoft.core.network` und wird von allen Netzwerkmodulen verwendet.

---

## Tests
```bash
pytest
```
Die Tests decken Probe-Emission, Resonanzberechnung, Pipeline- und Fixpunkt-Flow, Proxy-Sockets sowie den MeshLayer
(abzüglich optionaler SciPy-Features) ab.

---

## Docker
```bash
docker build -t ainsoft .
docker run --rm ainsoft
```
Das Container-Entry-Script startet standardmäßig drei CLI-Zyklen gegen `127.0.0.1`. Alternative Kommandos oder Proxy-Optionen
lassen sich via `docker run ainsoft python -m ainsoft.interfaces.cli …` übergeben.

---

## Projektstruktur
```
ainsoft/
├── core/            # Resonanzlogik, Impulse, Thresholds, Proxy-Helfer
├── scan/            # Probes, Listener, Signal-Analyzer
├── orchestrator/    # Lifecycle, Scheduler, Fixpunktattraktor
├── pipeline/        # Generatoren, Transformer, Dispatcher, MeshLayer, Blueprints, Hyperbion
├── config/          # Defaults & YAML-Schema
├── interfaces/      # CLI, REST-API, Logging
└── tests/           # Pytest-Suite
```

---

## Weiterführende Module & Blueprints
- **GabrielCell / Kyberios / KyberiotesField** – Agenten- und Schwarm-Bausteine für dezentrale Pipelines.
- **Tripolar Resonance Module (TRM2)** – Multipolare Entscheidungslogik für Scorer oder Threshold-Anpassungen.
- **Emotion Regulation Module (ERM)** – Feedback-Modulation für adaptive Schwellen.
- **DTT-Modulatoren** – Zeitabhängige Steuerung von Schwellen, Resonanzen und Agenten-Verhalten.
- **HDAG** – Hyperdimensionale DAGs zur Kontext- und Task-Verwaltung.
- **Vesica/Mandorla Overlap** – Konsensprüfungen für Operatorenketten.
- **Steganografie- & API-Mimikry-Transformer** – Realistische Payloads und versteckte Übertragungskanäle.
- **MeshLayer-REST** – Erweiterbare FastAPI-Endpoints zur Mesh-Steuerung.
- **HyperbionModule / SensoriumCell / FSMCore / MandorlaField / SeraphicFeedbackModule** – Bio-resonante Subsysteme,
  Proof-of-Resonance-Gates, spiralisiertes Gedächtnis und Feedback-Einbettung inklusive Audit/State-Export.
- **Ouroboros GabrielCellSwarm / KyberiosController / FieldTensorRouter / CSPStateMachine / ShadowChain** –
  Finanz- und DeFi-orientierte Entscheidungs- und Ausführungslogik mit Audit-Trail und Quorumsteuerung.

Alle Komponenten sind als Callables implementiert und können in Pipeline- oder Fixpunktkonfigurationen gemischt werden.

---

## Troubleshooting & Tipps
- **SciPy fehlt**: MeshLayer fällt automatisch auf k-NN-Triangulation zurück. Für Delaunay `pip install scipy` ausführen.
- **Proxy-Fehler**: Stellen Sie sicher, dass `PySocks` installiert ist und Host/Port erreichbar sind.
- **Custom Module**: Nutzen Sie das Schema `module.submodule:callable`, damit der Orchestrator Komponenten automatisch lädt.
- **Audit-Logging**: MeshLayer-Operationen führen Audit-Einträge; für persistente Logs kann `StructuredAuditLogger` verwendet
  werden.
- **State Persistence**: MeshLayer besitzt `export_state`/`import_state` sowie JSON-Exports für Visualisierung.

Mit diesen Bausteinen lässt sich AinSOFT als Forschungsplattform, orchestrierter Traffic-Simulator, adaptives Agentennetz
oder experimentelles Resonanzlabor einsetzen.
