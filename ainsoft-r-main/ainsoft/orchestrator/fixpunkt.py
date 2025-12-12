"""Helpers to execute the Fixpunktattraktor pipeline."""

from __future__ import annotations

from typing import Optional

from ainsoft.core.network import ProxyConfig
from ainsoft.pipeline.aion_pipeline import (
    build_fixpunkt_engine_from_config,
    load_pipeline_config,
)


def run_fixpunkt_cycle(
    config_path: str = "ainsoft/config/schema.yaml",
    *,
    proxy_config: Optional[ProxyConfig] = None,
):
    """Run the Fixpunktattraktor pipeline once using the supplied configuration."""

    config = load_pipeline_config(config_path)
    engine = build_fixpunkt_engine_from_config(config, proxy_cfg=proxy_config)
    return engine.run()


__all__ = ["run_fixpunkt_cycle"]
