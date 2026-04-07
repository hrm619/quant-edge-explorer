"""Tests for FastAPI server routes — conversations, artifacts, annotations."""

import sqlite3
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from explorer.history.db import get_memory_db
from explorer.history import repository as repo
from server.app import create_app
from server.dependencies import get_history_conn


@pytest.fixture
def history_conn():
    """In-memory history database for server tests (thread-safe)."""
    conn = get_memory_db(check_same_thread=False)
    yield conn
    conn.close()


@pytest.fixture
def client(history_conn):
    """FastAPI test client with overridden history DB dependency."""
    app = create_app()

    def override_history_conn() -> Generator[sqlite3.Connection, None, None]:
        # Reuse the same connection across requests (no close — fixture owns it)
        yield history_conn

    app.dependency_overrides[get_history_conn] = override_history_conn
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Conversations CRUD
# ---------------------------------------------------------------------------


class TestConversations:
    def test_create_conversation(self, client):
        resp = client.post("/api/v1/conversations", json={"title": "Test conv"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test conv"
        assert data["id"] is not None
        assert data["message_count"] == 0

    def test_create_conversation_no_title(self, client):
        resp = client.post("/api/v1/conversations", json={})
        assert resp.status_code == 201
        assert resp.json()["title"] is None

    def test_list_conversations(self, client):
        client.post("/api/v1/conversations", json={"title": "First"})
        client.post("/api/v1/conversations", json={"title": "Second"})

        resp = client.get("/api/v1/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_conversations_excludes_archived(self, client, history_conn):
        c1 = repo.create_conversation(history_conn, title="Active")
        c2 = repo.create_conversation(history_conn, title="Archived")
        repo.update_conversation(history_conn, c2["id"], archived_at="2026-04-07T00:00:00Z")

        resp = client.get("/api/v1/conversations")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Active"

    def test_list_conversations_archived_only(self, client, history_conn):
        c1 = repo.create_conversation(history_conn, title="Active")
        c2 = repo.create_conversation(history_conn, title="Archived")
        repo.update_conversation(history_conn, c2["id"], archived_at="2026-04-07T00:00:00Z")

        resp = client.get("/api/v1/conversations", params={"archived": True})
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Archived"

    def test_get_conversation(self, client, history_conn):
        conv = repo.create_conversation(history_conn, title="Detail test")
        repo.add_message(history_conn, conv["id"], "user", "Hello")
        repo.add_message(history_conn, conv["id"], "assistant", "Hi there")

        resp = client.get(f"/api/v1/conversations/{conv['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Detail test"
        assert len(data["messages"]) == 2

    def test_get_conversation_not_found(self, client):
        resp = client.get("/api/v1/conversations/nonexistent")
        assert resp.status_code == 404

    def test_update_conversation_title(self, client, history_conn):
        conv = repo.create_conversation(history_conn, title="Old title")

        resp = client.patch(
            f"/api/v1/conversations/{conv['id']}",
            json={"title": "New title"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New title"

    def test_update_conversation_starred(self, client, history_conn):
        conv = repo.create_conversation(history_conn, title="Star me")

        resp = client.patch(
            f"/api/v1/conversations/{conv['id']}",
            json={"starred": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["starred"] == 1

    def test_list_conversations_starred_filter(self, client, history_conn):
        c1 = repo.create_conversation(history_conn, title="Normal")
        c2 = repo.create_conversation(history_conn, title="Starred")
        repo.update_conversation(history_conn, c2["id"], starred=1)

        resp = client.get("/api/v1/conversations", params={"starred": True})
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Starred"

    def test_list_conversations_pagination(self, client, history_conn):
        for i in range(5):
            repo.create_conversation(history_conn, title=f"Conv {i}")

        resp = client.get("/api/v1/conversations", params={"limit": 2, "offset": 0})
        assert len(resp.json()) == 2

        resp = client.get("/api/v1/conversations", params={"limit": 2, "offset": 3})
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Artifacts CRUD
# ---------------------------------------------------------------------------


class TestArtifacts:
    def _seed_artifact(self, history_conn, kind="table", title="Test artifact"):
        conv = repo.create_conversation(history_conn, title="Conv")
        msg = repo.add_message(history_conn, conv["id"], "assistant", "Results")
        repo.add_tool_call(history_conn, msg["id"], "tc-1", "query_sql", {}, '{}')
        return repo.add_artifact(
            history_conn, conv["id"], "tc-1", kind, title,
            {"columns": ["a"], "rows": [{"a": 1}]}, "test data",
        )

    def test_list_artifacts(self, client, history_conn):
        self._seed_artifact(history_conn)
        self._seed_artifact(history_conn, kind="chart", title="Chart")

        resp = client.get("/api/v1/artifacts")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_artifacts_kind_filter(self, client, history_conn):
        self._seed_artifact(history_conn, kind="table")
        self._seed_artifact(history_conn, kind="chart")

        resp = client.get("/api/v1/artifacts", params={"kind": "table"})
        assert len(resp.json()) == 1
        assert resp.json()[0]["kind"] == "table"

    def test_get_artifact(self, client, history_conn):
        artifact = self._seed_artifact(history_conn)

        resp = client.get(f"/api/v1/artifacts/{artifact['id']}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test artifact"
        assert "spec" in resp.json()

    def test_get_artifact_not_found(self, client):
        resp = client.get("/api/v1/artifacts/nonexistent")
        assert resp.status_code == 404

    def test_update_artifact_flag(self, client, history_conn):
        artifact = self._seed_artifact(history_conn)

        resp = client.patch(
            f"/api/v1/artifacts/{artifact['id']}",
            json={"quality_flag": "trusted"},
        )
        assert resp.status_code == 200
        assert resp.json()["quality_flag"] == "trusted"

    def test_update_artifact_invalid_flag(self, client, history_conn):
        artifact = self._seed_artifact(history_conn)

        resp = client.patch(
            f"/api/v1/artifacts/{artifact['id']}",
            json={"quality_flag": "invalid"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Annotations CRUD
# ---------------------------------------------------------------------------


class TestAnnotations:
    def _seed_conversation(self, history_conn):
        return repo.create_conversation(history_conn, title="Annotated conv")

    def test_create_annotation(self, client, history_conn):
        conv = self._seed_conversation(history_conn)

        resp = client.post(
            f"/api/v1/conversations/{conv['id']}/annotations",
            json={"body": "This is interesting"},
        )
        assert resp.status_code == 201
        assert resp.json()["body"] == "This is interesting"

    def test_create_annotation_conversation_not_found(self, client):
        resp = client.post(
            "/api/v1/conversations/nonexistent/annotations",
            json={"body": "test"},
        )
        assert resp.status_code == 404

    def test_update_annotation(self, client, history_conn):
        conv = self._seed_conversation(history_conn)
        ann = repo.add_annotation(history_conn, conv["id"], "Draft")

        resp = client.patch(
            f"/api/v1/annotations/{ann['id']}",
            json={"body": "Revised"},
        )
        assert resp.status_code == 200
        assert resp.json()["body"] == "Revised"

    def test_update_annotation_not_found(self, client):
        resp = client.patch(
            "/api/v1/annotations/nonexistent",
            json={"body": "test"},
        )
        assert resp.status_code == 404

    def test_delete_annotation(self, client, history_conn):
        conv = self._seed_conversation(history_conn)
        ann = repo.add_annotation(history_conn, conv["id"], "Temp")

        resp = client.delete(f"/api/v1/annotations/{ann['id']}")
        assert resp.status_code == 204

    def test_delete_annotation_not_found(self, client):
        resp = client.delete("/api/v1/annotations/nonexistent")
        assert resp.status_code == 404
