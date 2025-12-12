"""Command line interface for AinSOFT with proxy-aware controls."""

from __future__ import annotations

from typing import Any, Dict

import click

from ainsoft.config.defaults import DEFAULT_PROXY_CONFIG

from ainsoft.orchestrator.lifecycle import run_lifecycle_cycle


@click.command()
@click.argument("target")
@click.option("--port", default=8080, help="Target port (default: 8080)")
@click.option("--cycles", default=1, help="Number of cycles to execute")
@click.option(
    "--proxy-enabled/--no-proxy",
    default=DEFAULT_PROXY_CONFIG["enabled"],
    help="Toggle SOCKS5 proxy usage for network operations.",
)
@click.option("--proxy-host", default=None, help="SOCKS5 proxy host")
@click.option("--proxy-port", default=None, type=int, help="SOCKS5 proxy port")
@click.option("--proxy-username", default=None, help="SOCKS5 proxy username")
@click.option("--proxy-password", default=None, help="SOCKS5 proxy password")
def main(
    target: str,
    port: int,
    cycles: int,
    proxy_enabled: bool,
    proxy_host: str | None,
    proxy_port: int | None,
    proxy_username: str | None,
    proxy_password: str | None,
) -> None:
    """Run one or more resonance cycles against *target* with optional proxy."""

    proxy_config: Dict[str, Any] = dict(DEFAULT_PROXY_CONFIG)
    proxy_config.update(
        {
            "enabled": proxy_enabled,
            "host": proxy_host or proxy_config.get("host"),
            "port": proxy_port or proxy_config.get("port"),
            "username": proxy_username or proxy_config.get("username"),
            "password": proxy_password or proxy_config.get("password"),
        }
    )

    if proxy_config["enabled"] and (not proxy_config["host"] or not proxy_config["port"]):
        raise click.BadParameter("Proxy enabled but host/port missing.")

    for i in range(cycles):
        click.echo(f"--- Zyklus {i + 1} ---")
        run_lifecycle_cycle(target, port, proxy_config=proxy_config)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

