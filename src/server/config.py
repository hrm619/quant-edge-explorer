"""Server configuration — frozen dataclass with lru_cache singleton."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", "")
    )
    openai_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )
    fantasy_data_db: str = field(
        default_factory=lambda: os.environ.get("FANTASY_DATA_DB", "")
    )
    chroma_persist_dir: str = field(
        default_factory=lambda: os.environ.get(
            "CHROMA_PERSIST_DIR",
            str(Path.home() / ".knowledge-base" / "chroma"),
        )
    )
    history_db_path: str = field(
        default_factory=lambda: os.environ.get(
            "HISTORY_DB_PATH",
            str(Path.home() / ".quant-edge" / "history.db"),
        )
    )
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"
    model: str = "claude-sonnet-4-20250514"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
