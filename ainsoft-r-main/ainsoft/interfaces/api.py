"""REST API for triggering AinSOFT cycles with proxy support."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from ainsoft.orchestrator.lifecycle import run_lifecycle_cycle
from ainsoft.config import load_phantomload_config
from ainsoft.pipeline import PhantomloadKernel

app = FastAPI()


class ProxyPayload(BaseModel):
    """Payload schema describing SOCKS5 proxy settings."""

    enabled: bool = False
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None


class CycleRequest(BaseModel):
    """API request body for triggering a cycle."""

    target: str
    port: int = 8080
    proxy: Optional[ProxyPayload] = None


class PhantomTriggerRequest(BaseModel):
    """Request body for starting a phantomload simulation."""

    mode: str = "sybil"
    nodes: int = 16
    mutate: bool = True
    autostart: Optional[bool] = None


class ProxyConfigureRequest(BaseModel):
    """Update the proxy rotation for the phantom kernel."""

    mode: str = "round_robin"
    proxies: List[str] = []


class SupervisorUpdateRequest(BaseModel):
    """Payload for updating supervisor parameters."""

    params: dict[str, float]


_phantom_config = load_phantomload_config()
_exports_dir = Path(_phantom_config.get("phantomload", {}).get("export", {}).get("export_path", "./exports"))
phantom_kernel = PhantomloadKernel.from_config(_phantom_config, export_dir=_exports_dir)


@app.post("/cycle/")
def api_cycle(request: CycleRequest):
    """Trigger a single lifecycle cycle via HTTP with optional proxy config."""

    proxy_config = request.proxy.dict() if request.proxy else None
    run_lifecycle_cycle(request.target, request.port, proxy_config=proxy_config)
    return {
        "status": "ok",
        "target": request.target,
        "port": request.port,
        "proxy_enabled": proxy_config["enabled"] if proxy_config else False,
    }


@app.post("/phantomload/trigger")
def api_phantomload_trigger(request: PhantomTriggerRequest):
    """Start or reconfigure the phantomload simulation."""

    status = phantom_kernel.trigger(
        mode=request.mode,
        nodes=request.nodes,
        mutate=request.mutate,
        autostart=request.autostart,
    )
    return {"status": "running", "details": status}


@app.get("/phantomload/status")
def api_phantomload_status():
    """Return the current phantomload kernel status."""

    return phantom_kernel.status()


@app.post("/phantomload/stop")
def api_phantomload_stop():
    """Stop the phantomload heartbeat and clear nodes."""

    phantom_kernel.stop()
    return {"status": "stopped"}


@app.get("/mesh/export")
def api_mesh_export(format: str = "json", filename: Optional[str] = None):
    """Export the current phantom mesh snapshot in the requested format."""

    path = phantom_kernel.export_mesh(format=format, filename=filename)
    return {"status": "exported", "format": format, "path": str(path)}


@app.get("/supervisor/params")
def api_supervisor_params():
    """Expose the supervisor snapshot for dashboards."""

    return phantom_kernel.supervisor_params()


@app.post("/supervisor/set")
def api_supervisor_set(request: SupervisorUpdateRequest):
    """Update supervisor state with arbitrary float parameters."""

    phantom_kernel.apply_supervisor_update(request.params)
    return {"status": "updated"}


@app.post("/proxy/configure")
def api_proxy_configure(request: ProxyConfigureRequest):
    """Update the proxy rotation list used by the phantom kernel."""

    phantom_kernel.configure_proxy(request.proxies, mode=request.mode)
    return {"status": "configured", "mode": request.mode, "count": len(request.proxies)}

