"""History database connection factory and schema initialization."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_HISTORY_PATH = Path.home() / ".quant-edge" / "history.db"
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_history_db(path: Path | str = DEFAULT_HISTORY_PATH) -> sqlite3.Connection:
    """Open (or create) the history database and ensure schema exists."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    init_schema(conn)
    return conn


def get_memory_db(check_same_thread: bool = True) -> sqlite3.Connection:
    """Create an in-memory history database (for tests)."""
    conn = sqlite3.connect(":memory:", check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Apply the schema DDL if tables don't exist yet."""
    schema_sql = _SCHEMA_PATH.read_text()
    conn.executescript(schema_sql)
