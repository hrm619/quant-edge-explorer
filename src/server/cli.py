"""CLI entry point for the quant-edge server."""

from __future__ import annotations

import click
import uvicorn


@click.group()
def main() -> None:
    """Quant-Edge Explorer — server commands."""


@main.command()
@click.option("--host", default="127.0.0.1", help="Bind address.")
@click.option("--port", default=8000, type=int, help="Port number.")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development.")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI server."""
    uvicorn.run("server.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
