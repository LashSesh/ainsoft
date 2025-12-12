"""Tests for the probe emitter module."""

from __future__ import annotations

from ainsoft.scan.probe_emitter import emit_probe_pattern


def test_emit_probe():
    result = emit_probe_pattern("127.0.0.1")
    assert "status" in result
    assert result["status"] in {"sent", "error"}

