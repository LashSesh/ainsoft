from pathlib import Path

import numpy as np

from ainsoft.config import load_phantomload_config
from ainsoft.pipeline import (
    GhostRPCEngine,
    OuroborosQuadrupole,
    PhantomNode,
    PhantomloadKernel,
    ProxyManager,
)


def test_ouroboros_quadrupole_cycle():
    quad = OuroborosQuadrupole()
    activations = {quad.advance() for _ in range(8)}
    assert activations == {(0, 2), (1, 3), (0, 1), (2, 3)}


def test_proxy_manager_rotation_modes():
    manager = ProxyManager()
    manager.configure(["socks5://a", "socks5://b"], mode="round_robin")
    assert manager.acquire() == "socks5://a"
    assert manager.acquire() == "socks5://b"
    manager.configure(["x"], mode="random")
    assert manager.acquire() == "x"


def test_ghost_rpc_engine_tick_updates_nodes():
    engine = GhostRPCEngine(idle_timeout=0.5, decay=0.5)
    geometry = np.arange(5, dtype=float)
    engine.add_node(PhantomNode("node-1", geometry, "seed"))
    engine.add_node(PhantomNode("node-2", geometry * 2, "seed2"))
    event = engine.tick((0, 2))
    assert event is not None
    status = engine.status()
    assert status["nodes"] >= 1
    assert len(event["active_nodes"]) <= 2


def test_phantomload_kernel_trigger_and_export(tmp_path: Path):
    config = load_phantomload_config()
    kernel = PhantomloadKernel.from_config(config, export_dir=tmp_path)
    kernel.trigger(mode="sybil", nodes=3, mutate=False, autostart=False)
    kernel.tick()
    status = kernel.status()
    assert status["nodes"] >= 1
    mesh = kernel.mesh_snapshot()
    assert "nodes" in mesh and mesh["nodes"]
    export_path = kernel.export_mesh(format="json", filename="mesh.json")
    assert export_path.exists()
    kernel.stop()
    assert kernel.status()["running"] is False
