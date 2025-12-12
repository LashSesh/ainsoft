"""Web3 expansion pack utilities for AinSOFT.

This module provides a collection of helper classes for the Phosphoros
Web3 suite blueprint.  The goal is to expose lightweight, dependency-free
building blocks that mirror the behaviour described in the blueprint
document while remaining testable inside the core repository.

The implementation deliberately keeps optional integrations (for example
``scikit-learn`` based clustering) guarded so that the suite continues to
work in environments where those packages are not available.  Each class
is designed to operate on plain Python/numpy structures and can therefore
be wired into the existing pipeline orchestration layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import random
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, List, MutableMapping, Optional, Sequence

import numpy as np

try:  # pragma: no cover - optional dependency
    from sklearn.cluster import KMeans
except Exception:  # pragma: no cover - sklearn is optional
    KMeans = None  # type: ignore


TickCallback = Callable[[], None]


class ScorpioBridge:
    """Heartbeat driven scheduler for blueprint callbacks.

    The bridge executes registered callbacks in a dedicated daemon thread
    using a fixed tick interval.  It can be used as the timing backbone for
    synthetic API traffic or mesh synchronisation logic.
    """

    def __init__(self, tick_interval: float = 0.017) -> None:
        self.tick_interval = tick_interval
        self._running = False
        self._callbacks: List[TickCallback] = []
        self._thread: Optional[threading.Thread] = None

    def register_callback(self, callback: TickCallback) -> None:
        """Register a function that will be called on every heartbeat."""

        self._callbacks.append(callback)

    def start(self) -> None:
        """Start the heartbeat loop in a background thread."""

        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the heartbeat loop and wait for the thread to exit."""

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.tick_interval * 4)

    def _run(self) -> None:
        while self._running:
            for callback in list(self._callbacks):
                try:
                    callback()
                except Exception as exc:  # pragma: no cover - defensive log
                    print(f"ScorpioBridge callback error: {exc}")
            time.sleep(self.tick_interval)


class SeedDNAEngine:
    """Derives 5D geometry vectors from seed phrases."""

    def __init__(self, trm_func: Optional[Callable[[np.ndarray], np.ndarray]] = None) -> None:
        self.trm_func = trm_func or (lambda x: x)

    @staticmethod
    def phrase_to_seed(phrase: str) -> List[int]:
        """Convert a phrase into deterministic 16-bit chunks using SHA-256."""

        digest = hashlib.sha256(phrase.encode("utf-8")).hexdigest()
        return [int(digest[i : i + 4], 16) for i in range(0, 32, 4)]

    @staticmethod
    def seed_to_geometry(seed: Sequence[int]) -> np.ndarray:
        """Create a 5D vector representation from a sequence of integers."""

        vector = np.array(seed[:5], dtype=float)
        if vector.size < 5:
            vector = np.pad(vector, (0, 5 - vector.size))
        return vector

    def encode(self, phrase: str) -> np.ndarray:
        """Return a TRM-modulated geometry vector for the given phrase."""

        seed = self.phrase_to_seed(phrase)
        geometry = self.seed_to_geometry(seed)
        transformed = self.trm_func(geometry)
        return np.asarray(transformed, dtype=float)


class MutationEngine:
    """Generates mutated variants of deterministic seed phrases."""

    def __init__(self, dna_engine: SeedDNAEngine, *, mutation_rate: float = 0.1) -> None:
        self.dna_engine = dna_engine
        self.mutation_rate = mutation_rate

    def mutate_seed(self, seed: Sequence[int]) -> List[float]:
        """Apply a bounded random perturbation to a seed sequence."""

        return [x + (random.random() - 0.5) * 2 * self.mutation_rate for x in seed]

    def generate_mutant(self, phrase: str) -> List[float]:
        """Create a mutated seed from a phrase."""

        base_seed = self.dna_engine.phrase_to_seed(phrase)
        return self.mutate_seed(base_seed)


class SeedClusterEngine:
    """Cluster seeds using KMeans if available, otherwise a simple heuristic."""

    def __init__(self, n_clusters: int = 3) -> None:
        self.n_clusters = max(1, n_clusters)

    def cluster_seeds(self, seeds: Sequence[Sequence[float]]) -> List[int]:
        """Return cluster labels for the provided seeds."""

        if not seeds:
            return []

        array = np.asarray(seeds, dtype=float)
        if array.ndim == 1:
            array = array.reshape(-1, 1)

        if KMeans is not None and len(array) >= self.n_clusters:
            model = KMeans(n_clusters=self.n_clusters, n_init="auto")
            labels = model.fit_predict(array)
            return labels.tolist()

        # Fallback: assign clusters by modulo index to avoid dependency
        return [idx % self.n_clusters for idx in range(len(array))]


class SupervisorInterface:
    """Stores aggregated activity data for visualisation or dashboards."""

    def __init__(self) -> None:
        self.state: MutableMapping[str, float] = {}

    def update(self, activity: MutableMapping[str, float]) -> None:
        self.state.update(activity)

    def snapshot(self) -> MutableMapping[str, float]:
        return dict(self.state)


class MetaMemoryCore:
    """Keeps a bounded history of activity snapshots."""

    def __init__(self, max_history: Optional[int] = None) -> None:
        self.max_history = max_history
        self.history: List[MutableMapping[str, float]] = []

    def store(self, record: MutableMapping[str, float]) -> None:
        self.history.append(dict(record))
        if self.max_history is not None and len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

    def get_history(self) -> List[MutableMapping[str, float]]:
        return list(self.history)


class ExportModule:
    """Persist mesh/cluster states as JSON or CSV."""

    def __init__(self, export_dir: Optional[Path] = None) -> None:
        self.export_dir = Path(export_dir or Path.cwd())

    def export_as_json(self, data: MutableMapping[str, object], filename: str = "export.json") -> Path:
        path = self.export_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return path

    def export_as_csv(self, rows: Iterable[Sequence[object]], filename: str = "export.csv") -> Path:
        import csv

        path = self.export_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for row in rows:
                writer.writerow(row)
        return path


class ReverbRing:
    """Lightweight activity log that can be used to build heatmaps."""

    def __init__(self) -> None:
        self.activity_log: List[MutableMapping[str, float]] = []

    def log(self, activity: MutableMapping[str, float]) -> None:
        self.activity_log.append(dict(activity))

    def get_heatmap(self) -> List[MutableMapping[str, float]]:
        return list(self.activity_log)


@dataclass
class PhosphorosKernel:
    """High-level manager that wires together the Web3 suite modules."""

    bridge: ScorpioBridge = field(default_factory=ScorpioBridge)
    dna_engine: SeedDNAEngine = field(default_factory=SeedDNAEngine)
    mutation_engine: MutationEngine = field(init=False)
    cluster_engine: SeedClusterEngine = field(default_factory=lambda: SeedClusterEngine(n_clusters=3))
    supervisor: SupervisorInterface = field(default_factory=SupervisorInterface)
    meta_memory: MetaMemoryCore = field(default_factory=MetaMemoryCore)
    export: ExportModule = field(default_factory=ExportModule)
    reverb: ReverbRing = field(default_factory=ReverbRing)
    seeds: List[np.ndarray] = field(default_factory=list)
    clusters: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.mutation_engine = MutationEngine(self.dna_engine)

    def add_seed_phrase(self, phrase: str, *, mutate: bool = False) -> np.ndarray:
        """Encode a phrase and optionally log a mutated variant."""

        geometry = self.dna_engine.encode(phrase)
        self.seeds.append(geometry)
        self.reverb.log({"seed": float(np.linalg.norm(geometry)), "timestamp": time.time()})
        if mutate:
            mutant = self.mutation_engine.generate_mutant(phrase)
            self.reverb.log({"mutant": float(sum(mutant)), "timestamp": time.time()})
        return geometry

    def cluster(self) -> List[int]:
        """Cluster the current seeds and cache the cluster labels."""

        if not self.seeds:
            self.clusters = []
            return []
        labels = self.cluster_engine.cluster_seeds(self.seeds)
        self.clusters = labels
        return labels

    def tick(self) -> None:
        """Default heartbeat callback that records high-level metrics."""

        activity = {
            "tick_time": time.time(),
            "n_seeds": float(len(self.seeds)),
            "n_clusters": float(len(set(self.clusters)) if self.clusters else 0),
        }
        self.supervisor.update(activity)
        self.meta_memory.store(activity)
        self.reverb.log(activity)

    def export_state(self, filename: str = "web3_state.json") -> Path:
        """Serialise the kernel state via the export module."""

        data = {
            "seeds": [seed.tolist() for seed in self.seeds],
            "clusters": list(self.clusters),
            "history": self.meta_memory.get_history(),
            "supervisor": self.supervisor.snapshot(),
        }
        return self.export.export_as_json(data, filename=filename)

    def attach_default_tick(self) -> None:
        """Register the :meth:`tick` callback with the ScorpioBridge."""

        self.bridge.register_callback(self.tick)

    @classmethod
    def from_config(
        cls,
        config: MutableMapping[str, object],
        *,
        export_dir: Optional[Path] = None,
    ) -> "PhosphorosKernel":
        """Create a kernel instance from a configuration mapping."""

        phosphoros_cfg = config.get("phosphoros", {}) if config else {}

        bridge_cfg = phosphoros_cfg.get("scorpio_bridge", {})  # type: ignore[assignment]
        bridge = ScorpioBridge(tick_interval=float(bridge_cfg.get("heartbeat_interval", 0.017)))

        dna_engine = SeedDNAEngine()
        mutation_rate = float(phosphoros_cfg.get("mutation_engine", {}).get("mutation_rate", 0.1))  # type: ignore[index]
        mutation_engine = MutationEngine(dna_engine, mutation_rate=mutation_rate)

        cluster_cfg = phosphoros_cfg.get("seed_cluster", {})  # type: ignore[assignment]
        cluster_engine = SeedClusterEngine(n_clusters=int(cluster_cfg.get("n_clusters", 3)))

        meta_cfg = phosphoros_cfg.get("meta_memory", {})  # type: ignore[assignment]
        meta_memory = MetaMemoryCore(max_history=meta_cfg.get("max_history"))  # type: ignore[arg-type]

        export_cfg = phosphoros_cfg.get("export", {})  # type: ignore[assignment]
        if export_dir is not None:
            export_base = Path(export_dir)
        else:
            export_path_cfg = export_cfg.get("export_path")  # type: ignore[assignment]
            export_base = Path(export_path_cfg) if export_path_cfg else None
        export_module = ExportModule(export_dir=export_base)

        kernel = cls(
            bridge=bridge,
            dna_engine=dna_engine,
            cluster_engine=cluster_engine,
            meta_memory=meta_memory,
            export=export_module,
        )
        kernel.mutation_engine = mutation_engine
        if bridge_cfg.get("enabled", True):
            kernel.attach_default_tick()
        return kernel


__all__ = [
    "ScorpioBridge",
    "SeedDNAEngine",
    "MutationEngine",
    "SeedClusterEngine",
    "SupervisorInterface",
    "MetaMemoryCore",
    "ExportModule",
    "ReverbRing",
    "PhosphorosKernel",
]

