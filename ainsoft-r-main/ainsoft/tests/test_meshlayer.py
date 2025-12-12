"""Tests for the AinSOFT mesh layer blueprint."""

from __future__ import annotations

from pathlib import Path
import random

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from ainsoft.pipeline.meshlayer import (
    MeshLayer,
    OperatorRegistry,
    StructuredAuditLogger,
    example_grad_func,
    example_score_func,
    example_targeting_func,
    create_mesh_app,
    export_mesh_json,
    fuzz_meshlayer,
    gate,
    coagula,
    solve,
    expand,
)


def test_meshlayer_build_weight_and_export(tmp_path):
    points = [
        [0.1, 0.2, 0.3, 0.4, 0.5],
        [0.2, 0.1, 0.4, 0.3, 0.6],
        [0.3, 0.2, 0.5, 0.4, 0.7],
        [0.4, 0.3, 0.6, 0.5, 0.8],
    ]

    logger = StructuredAuditLogger(str(tmp_path / "audit.jsonl"))
    registry = OperatorRegistry()
    registry.register("solve", solve)
    registry.register("gate", gate)
    registry.register("coagula", coagula)
    registry.register("expand", expand)

    layer = MeshLayer(points, mode="knn", k=2, logger=logger, operator_registry=registry)
    layer.build_mesh()
    assert layer.meshbuilder.edges

    layer.weight_edges(example_score_func)
    assert layer.meshbuilder.edge_scores

    layer.solve()
    layer.gate(0.2)
    layer.expand(example_grad_func, step=0.05)
    clusters = layer.coagula()
    assert isinstance(clusters, dict)

    coherence, betti = layer.check_topology()
    assert isinstance(coherence, bool)
    assert isinstance(betti, list)

    stable, entropy = layer.check_entropy()
    assert isinstance(stable, bool)
    assert entropy >= 0

    target = layer.find_targets(example_targeting_func)
    assert target is None or isinstance(target, int)

    state_path = tmp_path / "layer.pkl"
    json_path = tmp_path / "mesh.json"

    layer.export_state(str(state_path))
    reloaded = MeshLayer.import_state(str(state_path))
    assert isinstance(reloaded, MeshLayer)

    layer.export_json(str(json_path))
    assert json_path.exists()

    export_mesh_json(layer, str(tmp_path / "mesh2.json"))
    assert (tmp_path / "mesh2.json").exists()

    audit_file = tmp_path / "audit.jsonl"
    assert audit_file.exists()
    assert audit_file.read_text().strip() != ""


def test_mesh_app_endpoints(tmp_path):
    points = [[random.random() for _ in range(5)] for _ in range(6)]
    layer = MeshLayer(points, mode="knn", k=3)

    app = create_mesh_app(layer, export_path=str(tmp_path / "mesh_export.json"))
    client = TestClient(app)

    assert client.post("/mesh/build").status_code == 200
    assert client.post("/mesh/weight").json()["status"] == "edges weighted"
    assert client.post("/mesh/solve").json()["status"] == "solved"
    assert client.post("/mesh/gate/0.4").json()["status"] == "gated"
    assert client.post("/mesh/expand", params={"step": 0.05}).json()["status"] == "expanded"

    edges = client.get("/mesh/edges").json()["edges"]
    assert isinstance(edges, list)

    audit = client.get("/mesh/audit").json()["audit"]
    assert isinstance(audit, list)

    entropy_payload = client.get("/mesh/entropy").json()
    assert "entropy" in entropy_payload

    topology_payload = client.get("/mesh/topology").json()
    assert "betti" in topology_payload

    export_payload = client.get("/mesh/export").json()
    assert Path(export_payload["path"]).name == "mesh_export.json"
    assert (tmp_path / "mesh_export.json").exists()

    # ensure fuzz helper executes without raising
    fuzz_meshlayer(n_tests=1, dim=3, n_points=5)
