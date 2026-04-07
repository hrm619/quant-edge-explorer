"""Tests for the conversation history database."""

import json

import pytest

from explorer.history.db import get_memory_db
from explorer.history import repository as repo


@pytest.fixture
def conn():
    """In-memory history database for tests."""
    db = get_memory_db()
    yield db
    db.close()


@pytest.fixture
def conversation(conn):
    """A pre-created conversation for tests that need one."""
    return repo.create_conversation(conn, title="Test conversation")


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


class TestCreateConversation:
    def test_creates_with_title(self, conn):
        conv = repo.create_conversation(conn, title="WR target share analysis")
        assert conv["id"] is not None
        assert conv["title"] == "WR target share analysis"
        assert conv["message_count"] == 0
        assert conv["archived_at"] is None
        assert conv["starred"] == 0

    def test_creates_without_title(self, conn):
        conv = repo.create_conversation(conn)
        assert conv["title"] is None

    def test_unique_ids(self, conn):
        c1 = repo.create_conversation(conn, title="First")
        c2 = repo.create_conversation(conn, title="Second")
        assert c1["id"] != c2["id"]


class TestGetConversation:
    def test_returns_conversation(self, conn, conversation):
        result = repo.get_conversation(conn, conversation["id"])
        assert result["title"] == "Test conversation"

    def test_returns_none_for_missing(self, conn):
        assert repo.get_conversation(conn, "nonexistent") is None


class TestUpdateConversation:
    def test_update_title(self, conn, conversation):
        updated = repo.update_conversation(conn, conversation["id"], title="New title")
        assert updated["title"] == "New title"

    def test_update_starred(self, conn, conversation):
        updated = repo.update_conversation(conn, conversation["id"], starred=1)
        assert updated["starred"] == 1

    def test_update_archived(self, conn, conversation):
        updated = repo.update_conversation(conn, conversation["id"], archived_at="2026-04-07T00:00:00Z")
        assert updated["archived_at"] == "2026-04-07T00:00:00Z"


class TestListConversations:
    def test_lists_active(self, conn):
        repo.create_conversation(conn, title="Active")
        repo.create_conversation(conn, title="Archived")
        # Archive the second
        rows = repo.list_conversations(conn)
        assert len(rows) == 2

    def test_excludes_archived_by_default(self, conn):
        c1 = repo.create_conversation(conn, title="Active")
        c2 = repo.create_conversation(conn, title="Archived")
        repo.update_conversation(conn, c2["id"], archived_at="2026-04-07T00:00:00Z")

        rows = repo.list_conversations(conn, archived=False)
        assert len(rows) == 1
        assert rows[0]["title"] == "Active"

    def test_lists_archived_only(self, conn):
        c1 = repo.create_conversation(conn, title="Active")
        c2 = repo.create_conversation(conn, title="Archived")
        repo.update_conversation(conn, c2["id"], archived_at="2026-04-07T00:00:00Z")

        rows = repo.list_conversations(conn, archived=True)
        assert len(rows) == 1
        assert rows[0]["title"] == "Archived"

    def test_filters_starred(self, conn):
        c1 = repo.create_conversation(conn, title="Normal")
        c2 = repo.create_conversation(conn, title="Starred")
        repo.update_conversation(conn, c2["id"], starred=1)

        rows = repo.list_conversations(conn, starred=True)
        assert len(rows) == 1
        assert rows[0]["title"] == "Starred"

    def test_pagination(self, conn):
        for i in range(5):
            repo.create_conversation(conn, title=f"Conv {i}")

        rows = repo.list_conversations(conn, limit=2, offset=0)
        assert len(rows) == 2

        rows = repo.list_conversations(conn, limit=2, offset=3)
        assert len(rows) == 2

    def test_ordered_by_updated_at_desc(self, conn):
        c1 = repo.create_conversation(conn, title="First")
        c2 = repo.create_conversation(conn, title="Second")
        # Add a message to c1 to update its timestamp
        repo.add_message(conn, c1["id"], "user", "hello")

        rows = repo.list_conversations(conn)
        assert rows[0]["title"] == "First"  # Most recently updated


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class TestMessages:
    def test_add_and_get(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "user", "Hello")
        assert msg["role"] == "user"
        assert msg["content"] == "Hello"
        assert msg["ordinal"] == 0

        messages = repo.get_messages(conn, conversation["id"])
        assert len(messages) == 1

    def test_ordinal_auto_increments(self, conn, conversation):
        m1 = repo.add_message(conn, conversation["id"], "user", "First")
        m2 = repo.add_message(conn, conversation["id"], "assistant", "Second")
        m3 = repo.add_message(conn, conversation["id"], "user", "Third")

        assert m1["ordinal"] == 0
        assert m2["ordinal"] == 1
        assert m3["ordinal"] == 2

    def test_phase_stored(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "Plan", phase="planning")
        messages = repo.get_messages(conn, conversation["id"])
        assert messages[0]["phase"] == "planning"

    def test_updates_conversation_count(self, conn, conversation):
        repo.add_message(conn, conversation["id"], "user", "Hello")
        repo.add_message(conn, conversation["id"], "assistant", "Hi")

        conv = repo.get_conversation(conn, conversation["id"])
        assert conv["message_count"] == 2


# ---------------------------------------------------------------------------
# Tool calls
# ---------------------------------------------------------------------------


class TestToolCalls:
    def test_add_and_get(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "Running query")
        tc = repo.add_tool_call(
            conn, msg["id"], "tc-1", "query_sql",
            {"sql": "SELECT 1", "description": "test"},
            '{"rows": [], "row_count": 0}',
            duration_ms=42,
        )

        assert tc["tool_name"] == "query_sql"
        assert tc["duration_ms"] == 42

        calls = repo.get_tool_calls(conn, msg["id"])
        assert len(calls) == 1
        assert calls[0]["tool_input"] == {"sql": "SELECT 1", "description": "test"}

    def test_error_status(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "Error")
        tc = repo.add_tool_call(
            conn, msg["id"], "tc-2", "query_sql",
            {"sql": "BAD SQL"},
            '{"error": "syntax error"}',
            status="error",
            error_message="syntax error",
        )

        calls = repo.get_tool_calls(conn, msg["id"])
        assert calls[0]["status"] == "error"
        assert calls[0]["error_message"] == "syntax error"


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


class TestArtifacts:
    def test_add_and_get(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "Results")
        tc = repo.add_tool_call(
            conn, msg["id"], "tc-1", "query_sql",
            {"sql": "SELECT 1"}, '{"rows": []}',
        )

        artifact = repo.add_artifact(
            conn, conversation["id"], "tc-1", "table",
            "WR Regression Candidates",
            {"columns": ["player", "tgt_share"], "rows": [["Hill", 0.30]]},
            "player tgt_share Hill 0.30",
        )

        assert artifact["kind"] == "table"
        assert artifact["quality_flag"] == "unflagged"

        fetched = repo.get_artifact(conn, artifact["id"])
        assert fetched["spec"]["columns"] == ["player", "tgt_share"]

    def test_update_quality_flag(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "Results")
        repo.add_tool_call(conn, msg["id"], "tc-1", "query_sql", {}, '{}')
        artifact = repo.add_artifact(
            conn, conversation["id"], "tc-1", "table",
            "Test", {"data": []}, "test data",
        )

        updated = repo.update_artifact_flag(conn, artifact["id"], "trusted")
        assert updated["quality_flag"] == "trusted"

    def test_invalid_quality_flag_raises(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "x")
        repo.add_tool_call(conn, msg["id"], "tc-1", "query_sql", {}, '{}')
        artifact = repo.add_artifact(
            conn, conversation["id"], "tc-1", "table", "T", {}, "t",
        )

        with pytest.raises(ValueError, match="Invalid quality_flag"):
            repo.update_artifact_flag(conn, artifact["id"], "bad_value")

    def test_list_with_kind_filter(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "x")
        repo.add_tool_call(conn, msg["id"], "tc-1", "query_sql", {}, '{}')
        repo.add_tool_call(conn, msg["id"], "tc-2", "generate_chart", {}, '{}')

        repo.add_artifact(conn, conversation["id"], "tc-1", "table", "T1", {}, "t")
        repo.add_artifact(conn, conversation["id"], "tc-2", "chart", "C1", {}, "c")

        tables = repo.list_artifacts(conn, kind="table")
        assert len(tables) == 1
        assert tables[0]["kind"] == "table"

    def test_list_excludes_untrusted_by_flag(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "x")
        repo.add_tool_call(conn, msg["id"], "tc-1", "query_sql", {}, '{}')
        a1 = repo.add_artifact(conn, conversation["id"], "tc-1", "table", "Good", {}, "good")
        a2 = repo.add_artifact(conn, conversation["id"], "tc-1", "table", "Bad", {}, "bad")
        repo.update_artifact_flag(conn, a2["id"], "untrusted")

        trusted = repo.list_artifacts(conn, quality_flag="unflagged")
        assert len(trusted) == 1
        assert trusted[0]["title"] == "Good"


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


class TestAnnotations:
    def test_add_and_get(self, conn, conversation):
        ann = repo.add_annotation(conn, conversation["id"], "This looks promising")
        assert ann["body"] == "This looks promising"

        annotations = repo.get_annotations(conn, conversation["id"])
        assert len(annotations) == 1

    def test_update(self, conn, conversation):
        ann = repo.add_annotation(conn, conversation["id"], "Draft note")
        updated = repo.update_annotation(conn, ann["id"], "Revised note")
        assert updated["body"] == "Revised note"

    def test_delete(self, conn, conversation):
        ann = repo.add_annotation(conn, conversation["id"], "Temp note")
        assert repo.delete_annotation(conn, ann["id"]) is True
        assert repo.get_annotations(conn, conversation["id"]) == []

    def test_delete_nonexistent(self, conn):
        assert repo.delete_annotation(conn, "nonexistent") is False


# ---------------------------------------------------------------------------
# Full-text search
# ---------------------------------------------------------------------------


class TestFTS:
    def test_message_search(self, conn, conversation):
        repo.add_message(conn, conversation["id"], "user", "target share regression candidates")
        repo.add_message(conn, conversation["id"], "assistant", "Here are the WR results")

        results = repo.search_messages(conn, "target share")
        assert len(results) == 1
        assert "target share" in results[0]["content"]

    def test_message_search_no_results(self, conn, conversation):
        repo.add_message(conn, conversation["id"], "user", "hello world")
        results = repo.search_messages(conn, "nonexistent query term")
        assert len(results) == 0

    def test_artifact_search(self, conn, conversation):
        msg = repo.add_message(conn, conversation["id"], "assistant", "x")
        repo.add_tool_call(conn, msg["id"], "tc-1", "query_sql", {}, '{}')

        repo.add_artifact(
            conn, conversation["id"], "tc-1", "table",
            "WR Regression Candidates",
            {"columns": ["player"]},
            "player target_share yards_per_route_run Hill Adams",
        )

        results = repo.search_artifacts(conn, "target_share")
        assert len(results) == 1
        assert results[0]["title"] == "WR Regression Candidates"

    def test_conversation_search_via_fts(self, conn):
        c1 = repo.create_conversation(conn, title="WR analysis")
        c2 = repo.create_conversation(conn, title="RB analysis")
        repo.add_message(conn, c1["id"], "user", "Show me wide receiver target share data")
        repo.add_message(conn, c2["id"], "user", "Show me running back snap counts")

        # Search should find c1 via message content
        results = repo.list_conversations(conn, q="target share")
        assert len(results) == 1
        assert results[0]["id"] == c1["id"]

    def test_conversation_search_via_title(self, conn):
        repo.create_conversation(conn, title="WR target share deep dive")
        repo.create_conversation(conn, title="RB snap analysis")

        results = repo.list_conversations(conn, q="target share")
        assert len(results) == 1
        assert "target share" in results[0]["title"]


# ---------------------------------------------------------------------------
# Full conversation detail
# ---------------------------------------------------------------------------


class TestGetConversationWithMessages:
    def test_returns_full_detail(self, conn, conversation):
        msg1 = repo.add_message(conn, conversation["id"], "user", "Query")
        msg2 = repo.add_message(conn, conversation["id"], "assistant", "Results")
        repo.add_tool_call(
            conn, msg2["id"], "tc-1", "query_sql",
            {"sql": "SELECT 1"}, '{"rows": []}',
        )
        repo.add_artifact(
            conn, conversation["id"], "tc-1", "table",
            "Test", {"data": []}, "test",
        )
        repo.add_annotation(conn, conversation["id"], "Note")

        detail = repo.get_conversation_with_messages(conn, conversation["id"])

        assert detail["title"] == "Test conversation"
        assert len(detail["messages"]) == 2
        assert len(detail["messages"][1]["tool_calls"]) == 1
        assert len(detail["artifacts"]) == 1
        assert len(detail["annotations"]) == 1

    def test_returns_none_for_missing(self, conn):
        assert repo.get_conversation_with_messages(conn, "nonexistent") is None
