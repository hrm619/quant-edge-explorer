"""SQLite + ChromaDB + OpenAI connection management."""

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import chromadb
import openai

from fantasy_data.db import DEFAULT_DB_PATH
from knowledge_base.embedder import (
    get_chroma_client,
    get_openai_client,
    get_or_create_collection,
)


@dataclass
class Connections:
    sqlite_path: str
    chroma_client: chromadb.ClientAPI
    openai_client: openai.OpenAI
    collections: dict[str, chromadb.Collection]
    sqlite_stats: str = ""
    chroma_stats: str = ""

    def get_sqlite_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    def get_collection(self, domain: str = "fantasy_football") -> chromadb.Collection:
        if domain not in self.collections:
            self.collections[domain] = get_or_create_collection(
                self.chroma_client, domain
            )
        return self.collections[domain]


def init_connections() -> Connections:
    """Initialize all data store connections and print startup summary."""
    sqlite_path = os.environ.get("FANTASY_DATA_DB", str(DEFAULT_DB_PATH))
    if not Path(sqlite_path).exists():
        raise FileNotFoundError(f"Fantasy data DB not found: {sqlite_path}")

    chroma_dir = os.environ.get(
        "CHROMA_PERSIST_DIR",
        str(Path.home() / ".knowledge-base" / "chroma"),
    )
    if not Path(chroma_dir).exists():
        raise FileNotFoundError(f"ChromaDB directory not found: {chroma_dir}")

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY not set")

    chroma_client = get_chroma_client(chroma_dir)
    openai_client = get_openai_client(openai_key)

    # Pre-load collections
    collections: dict[str, chromadb.Collection] = {}
    for col in chroma_client.list_collections():
        collections[col.name] = col

    # Gather stats for banner (caller handles display)
    conn = sqlite3.connect(sqlite_path)
    baseline_count = conn.execute(
        "SELECT count(*) FROM player_season_baseline"
    ).fetchone()[0]
    player_count = conn.execute("SELECT count(*) FROM players").fetchone()[0]
    conn.close()

    sqlite_stats = f"SQLite: {player_count:,} players | {baseline_count:,} baselines"
    chroma_stats_parts = [
        f"{name} — {col.count():,} chunks" for name, col in collections.items()
    ]
    chroma_stats = "ChromaDB: " + ", ".join(chroma_stats_parts) if chroma_stats_parts else ""

    return Connections(
        sqlite_path=sqlite_path,
        chroma_client=chroma_client,
        openai_client=openai_client,
        collections=collections,
        sqlite_stats=sqlite_stats,
        chroma_stats=chroma_stats,
    )
