"""Dependency injection for FastAPI routes."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

from explorer.connections import Connections, init_connections
from explorer.history.db import get_history_db
from server.config import Settings, get_settings

_connections: Connections | None = None


def get_connections(settings: Settings | None = None) -> Connections:
    """Singleton explorer connections (SQLite + ChromaDB + OpenAI)."""
    global _connections
    if _connections is None:
        _connections = init_connections()
    return _connections


def get_history_conn(
    settings: Settings | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Yield a history DB connection per request."""
    s = settings or get_settings()
    conn = get_history_db(Path(s.history_db_path))
    try:
        yield conn
    finally:
        conn.close()
