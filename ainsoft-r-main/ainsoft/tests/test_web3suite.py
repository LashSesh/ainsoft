from pathlib import Path
import threading
import time

import numpy as np

from ainsoft.config import load_phosphoros_web3_config
from ainsoft.pipeline import (
    ExportModule,
    MetaMemoryCore,
    MutationEngine,
    PhosphorosKernel,
    ReverbRing,
    ScorpioBridge,
    SeedClusterEngine,
    SeedDNAEngine,
)


def test_seed_dna_engine_encoding_is_deterministic():
    engine = SeedDNAEngine()
    vector_a = engine.encode("example phrase")
    vector_b = engine.encode("example phrase")
    assert vector_a.shape == (5,)
    np.testing.assert_array_equal(vector_a, vector_b)


def test_mutation_engine_generates_mutant():
    dna = SeedDNAEngine()
    mutation = MutationEngine(dna, mutation_rate=0.2)
    mutant = mutation.generate_mutant("seed")
    assert len(mutant) == len(dna.phrase_to_seed("seed"))


def test_seed_cluster_engine_fallback_without_sklearn():
    seeds = [np.arange(5), np.ones(5), np.ones(5) * 2]
    engine = SeedClusterEngine(n_clusters=2)
    labels = engine.cluster_seeds(seeds)
    assert len(labels) == len(seeds)
    assert set(labels) <= {0, 1}


def test_meta_memory_core_bounds_history():
    memory = MetaMemoryCore(max_history=2)
    memory.store({"value": 1})
    memory.store({"value": 2})
    memory.store({"value": 3})
    assert len(memory.get_history()) == 2
    assert memory.get_history()[0]["value"] == 2


def test_reverb_ring_heatmap_snapshot():
    ring = ReverbRing()
    ring.log({"a": 1})
    ring.log({"b": 2})
    heatmap = ring.get_heatmap()
    assert len(heatmap) == 2
    assert heatmap[0]["a"] == 1


def test_export_module_writes_json(tmp_path: Path):
    exporter = ExportModule(export_dir=tmp_path)
    data = {"values": [1, 2, 3]}
    path = exporter.export_as_json(data, filename="test.json")
    assert path.exists()
    assert path.read_text().strip().startswith("{")


def test_scorpio_bridge_invokes_callback():
    bridge = ScorpioBridge(tick_interval=0.001)
    event = threading.Event()

    def callback() -> None:
        event.set()
        bridge.stop()

    bridge.register_callback(callback)
    bridge.start()
    assert event.wait(0.1)
    bridge.stop()


def test_phosphoros_kernel_from_config(tmp_path: Path):
    config = load_phosphoros_web3_config()
    kernel = PhosphorosKernel.from_config(config, export_dir=tmp_path)
    kernel.add_seed_phrase("example seed", mutate=True)
    kernel.cluster()
    kernel.bridge.start()
    time.sleep(0.01)
    kernel.bridge.stop()
    export_path = kernel.export_state()
    assert export_path.exists()
    assert kernel.supervisor.snapshot()["n_seeds"] >= 1
