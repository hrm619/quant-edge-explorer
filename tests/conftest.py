"""Test fixtures — in-memory SQLite, mock ChromaDB, mock OpenAI."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import chromadb
import pytest


@pytest.fixture
def sqlite_conn():
    """In-memory SQLite with fantasy-data schema and test data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE players (
            player_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL,
            position_group TEXT,
            team TEXT,
            age INTEGER,
            years_pro INTEGER,
            draft_round INTEGER,
            rookie_flag INTEGER DEFAULT 0,
            team_change_flag INTEGER DEFAULT 0,
            injury_concern_flag INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );

        CREATE TABLE player_season_baseline (
            baseline_id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            team TEXT,
            snap_share REAL,
            target_share REAL,
            air_yards_share REAL,
            yards_per_route_run REAL,
            catch_rate_over_expected REAL,
            pff_receiving_grade REAL,
            adp_consensus REAL,
            adp_positional_rank INTEGER,
            sharp_consensus_rank INTEGER,
            sharp_pos_rank INTEGER,
            adp_divergence_pos INTEGER,
            adp_divergence_flag INTEGER DEFAULT 0,
            data_trust_weight REAL DEFAULT 1.0,
            fantasy_pts_ppr REAL,
            fpts_per_game_ppr REAL,
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            UNIQUE(player_id, season)
        );

        CREATE TABLE coaching_staff (
            staff_id TEXT PRIMARY KEY,
            team TEXT NOT NULL,
            season INTEGER NOT NULL,
            head_coach TEXT,
            offensive_coordinator TEXT,
            system_tag TEXT,
            hc_continuity_flag INTEGER DEFAULT 1,
            oc_continuity_flag INTEGER DEFAULT 1,
            UNIQUE(team, season)
        );

        -- Seed test data
        INSERT INTO players VALUES
            ('AdamDa01', 'Davante Adams', 'WR', 'PASS_CATCHER', 'NYJ', 32, 11, 2, 0, 1, 0, 1),
            ('HillTy01', 'Tyreek Hill', 'WR', 'PASS_CATCHER', 'MIA', 31, 9, 5, 0, 0, 0, 1),
            ('McCaCh01', 'Christian McCaffrey', 'RB', 'BACKFIELD', 'SF', 28, 7, 1, 0, 0, 1, 1);

        INSERT INTO player_season_baseline VALUES
            ('AdamDa01_2025', 'AdamDa01', 2025, 'NYJ', 0.92, 0.28, 0.32, 2.1, -0.02, 78.5, 35.0, 15, 8, 6, 9, 1, 0.40, NULL, NULL),
            ('HillTy01_2025', 'HillTy01', 2025, 'MIA', 0.95, 0.30, 0.35, 2.5, 0.04, 85.2, 10.0, 4, 3, 2, -2, 0, 1.0, NULL, NULL),
            ('McCaCh01_2025', 'McCaCh01', 2025, 'SF', 0.70, 0.12, 0.08, 1.4, 0.01, 72.0, 8.0, 3, 2, 1, -2, 0, 0.55, NULL, NULL);

        INSERT INTO coaching_staff VALUES
            ('NYJ_2025', 'NYJ', 2025, 'Aaron Glenn', 'Todd Downing', 'PRO_STYLE', 0, 0),
            ('MIA_2025', 'MIA', 2025, 'Mike McDaniel', 'Frank Smith', 'SHANAHAN_ZONE', 1, 0),
            ('SF_2025', 'SF', 2025, 'Kyle Shanahan', 'Grant Cohn', 'SHANAHAN_ZONE', 1, 0);
    """)

    yield conn
    conn.close()


@pytest.fixture
def mock_connections(sqlite_conn, tmp_path):
    """Mock Connections object with real SQLite and mock ChromaDB/OpenAI."""
    from explorer.connections import Connections

    # Use in-memory ChromaDB
    chroma_client = chromadb.Client()
    collection = chroma_client.get_or_create_collection(
        name="fantasy_football",
        metadata={"hnsw:space": "cosine"},
    )

    # Add test chunks with mock embeddings
    collection.add(
        ids=["chunk_1", "chunk_2", "chunk_3"],
        embeddings=[[0.1] * 1536, [0.2] * 1536, [0.3] * 1536],
        documents=[
            "[SOURCE: barrett | DATE: 2025-03-15 | TYPE: youtube] Davante Adams is in a tough spot with the Jets.",
            "[SOURCE: barrett | DATE: 2025-03-20 | TYPE: youtube] Tyreek Hill remains elite in the Shanahan-adjacent scheme.",
            "[SOURCE: jj | DATE: 2025-04-01 | TYPE: youtube] McCaffrey injury concern is real but his efficiency numbers are unmatched.",
        ],
        metadatas=[
            {"analyst": "barrett", "trust_tier": "core", "source_type": "youtube", "published_at": "2025-03-15", "season": 2025, "content_tag": "preview", "title": "Jets WR Preview", "content_id": "c1"},
            {"analyst": "barrett", "trust_tier": "core", "source_type": "youtube", "published_at": "2025-03-20", "season": 2025, "content_tag": "preview", "title": "Dolphins Offense Review", "content_id": "c2"},
            {"analyst": "jj", "trust_tier": "core", "source_type": "youtube", "published_at": "2025-04-01", "season": 2025, "content_tag": "preview", "title": "RB Tiers 2025", "content_id": "c3"},
        ],
    )

    # Mock OpenAI client that returns fixed embeddings
    mock_openai = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.embedding = [0.15] * 1536
    mock_response = MagicMock()
    mock_response.data = [mock_embedding]
    mock_openai.embeddings.create.return_value = mock_response

    # Write SQLite to temp file so connections can open it
    db_path = str(tmp_path / "test.db")
    disk_conn = sqlite3.connect(db_path)
    sqlite_conn.backup(disk_conn)
    disk_conn.close()

    return Connections(
        sqlite_path=db_path,
        chroma_client=chroma_client,
        openai_client=mock_openai,
        collections={"fantasy_football": collection},
    )


@pytest.fixture
def charts_dir(tmp_path):
    """Temporary directory for chart output."""
    d = tmp_path / "charts"
    d.mkdir()
    return d
