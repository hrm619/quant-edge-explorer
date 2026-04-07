"""CRUD operations for the conversation history database."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def create_conversation(conn: sqlite3.Connection, title: str | None = None) -> dict:
    """Create a new conversation. Returns the row as a dict."""
    now = _now()
    cid = _uuid()
    conn.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (cid, title, now, now),
    )
    conn.commit()
    return {"id": cid, "title": title, "created_at": now, "updated_at": now,
            "archived_at": None, "starred": 0, "message_count": 0}


def update_conversation(
    conn: sqlite3.Connection,
    conversation_id: str,
    *,
    title: str | None = ...,
    starred: int | None = ...,
    archived_at: str | None = ...,
) -> dict | None:
    """Update mutable fields on a conversation. Returns updated row or None."""
    sets: list[str] = []
    params: list = []

    if title is not ...:
        sets.append("title = ?")
        params.append(title)
    if starred is not ...:
        sets.append("starred = ?")
        params.append(starred)
    if archived_at is not ...:
        sets.append("archived_at = ?")
        params.append(archived_at)

    if not sets:
        return get_conversation(conn, conversation_id)

    sets.append("updated_at = ?")
    params.append(_now())
    params.append(conversation_id)

    conn.execute(
        f"UPDATE conversations SET {', '.join(sets)} WHERE id = ?",
        params,
    )
    conn.commit()
    return get_conversation(conn, conversation_id)


def get_conversation(conn: sqlite3.Connection, conversation_id: str) -> dict | None:
    """Fetch a single conversation by id."""
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    return dict(row) if row else None


def list_conversations(
    conn: sqlite3.Connection,
    *,
    archived: bool = False,
    starred: bool | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List conversations with optional filters."""
    clauses: list[str] = []
    params: list = []

    if archived:
        clauses.append("c.archived_at IS NOT NULL")
    else:
        clauses.append("c.archived_at IS NULL")

    if starred is not None:
        clauses.append("c.starred = ?")
        params.append(1 if starred else 0)

    if q:
        # Search across conversation titles and message content via FTS
        clauses.append("""(
            c.title LIKE ? OR c.id IN (
                SELECT m.conversation_id FROM messages m
                JOIN messages_fts ON messages_fts.rowid = m.rowid
                WHERE messages_fts MATCH ?
            )
        )""")
        params.extend([f"%{q}%", q])

    where = " AND ".join(clauses) if clauses else "1=1"

    rows = conn.execute(
        f"""SELECT c.* FROM conversations c
            WHERE {where}
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


def add_message(
    conn: sqlite3.Connection,
    conversation_id: str,
    role: str,
    content: str,
    phase: str | None = None,
) -> dict:
    """Append a message to a conversation. Returns the row as a dict."""
    now = _now()
    mid = _uuid()

    # Get next ordinal
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), -1) + 1 FROM messages WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()
    ordinal = row[0]

    conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content, phase, created_at, ordinal) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (mid, conversation_id, role, content, phase, now, ordinal),
    )

    # Update message count and timestamp on conversation
    conn.execute(
        "UPDATE conversations SET message_count = message_count + 1, updated_at = ? WHERE id = ?",
        (now, conversation_id),
    )
    conn.commit()

    return {"id": mid, "conversation_id": conversation_id, "role": role,
            "content": content, "phase": phase, "created_at": now, "ordinal": ordinal}


def get_messages(
    conn: sqlite3.Connection,
    conversation_id: str,
) -> list[dict]:
    """Get all messages for a conversation, ordered by ordinal."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY ordinal",
        (conversation_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Tool calls
# ---------------------------------------------------------------------------


def add_tool_call(
    conn: sqlite3.Connection,
    message_id: str,
    tool_id: str,
    tool_name: str,
    tool_input: dict,
    tool_result: str,
    duration_ms: int | None = None,
    status: str = "success",
    error_message: str | None = None,
) -> dict:
    """Record a tool call. Returns the row as a dict."""
    now = _now()
    conn.execute(
        "INSERT INTO tool_calls (id, message_id, tool_name, tool_input, tool_result, "
        "duration_ms, status, error_message, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tool_id, message_id, tool_name, json.dumps(tool_input), tool_result,
         duration_ms, status, error_message, now),
    )
    conn.commit()

    return {"id": tool_id, "message_id": message_id, "tool_name": tool_name,
            "tool_input": tool_input, "tool_result": tool_result,
            "duration_ms": duration_ms, "status": status,
            "error_message": error_message, "created_at": now}


def get_tool_calls(conn: sqlite3.Connection, message_id: str) -> list[dict]:
    """Get all tool calls for a message."""
    rows = conn.execute(
        "SELECT * FROM tool_calls WHERE message_id = ? ORDER BY created_at",
        (message_id,),
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        # Parse JSON fields
        if isinstance(d["tool_input"], str):
            d["tool_input"] = json.loads(d["tool_input"])
        results.append(d)
    return results


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


def add_artifact(
    conn: sqlite3.Connection,
    conversation_id: str,
    tool_call_id: str,
    kind: str,
    title: str | None,
    spec: dict,
    searchable_text: str,
) -> dict:
    """Record an artifact. Returns the row as a dict."""
    now = _now()
    aid = _uuid()
    conn.execute(
        "INSERT INTO artifacts (id, tool_call_id, conversation_id, kind, title, spec, "
        "searchable_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (aid, tool_call_id, conversation_id, kind, title, json.dumps(spec),
         searchable_text, now),
    )
    conn.commit()

    return {"id": aid, "tool_call_id": tool_call_id, "conversation_id": conversation_id,
            "kind": kind, "title": title, "spec": spec,
            "searchable_text": searchable_text, "quality_flag": "unflagged",
            "created_at": now}


def update_artifact_flag(
    conn: sqlite3.Connection,
    artifact_id: str,
    quality_flag: str,
) -> dict | None:
    """Update an artifact's quality flag. Returns updated row or None."""
    if quality_flag not in ("unflagged", "trusted", "untrusted"):
        raise ValueError(f"Invalid quality_flag: {quality_flag}")

    conn.execute(
        "UPDATE artifacts SET quality_flag = ? WHERE id = ?",
        (quality_flag, artifact_id),
    )
    conn.commit()
    return get_artifact(conn, artifact_id)


def get_artifact(conn: sqlite3.Connection, artifact_id: str) -> dict | None:
    """Fetch a single artifact by id."""
    row = conn.execute(
        "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    if isinstance(d["spec"], str):
        d["spec"] = json.loads(d["spec"])
    return d


def list_artifacts(
    conn: sqlite3.Connection,
    *,
    q: str | None = None,
    kind: str | None = None,
    quality_flag: str | None = None,
    conversation_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List artifacts with optional filters."""
    clauses: list[str] = []
    params: list = []

    if kind:
        clauses.append("a.kind = ?")
        params.append(kind)
    if quality_flag:
        clauses.append("a.quality_flag = ?")
        params.append(quality_flag)
    if conversation_id:
        clauses.append("a.conversation_id = ?")
        params.append(conversation_id)
    if q:
        clauses.append("""a.rowid IN (
            SELECT rowid FROM artifacts_fts WHERE artifacts_fts MATCH ?
        )""")
        params.append(q)

    where = " AND ".join(clauses) if clauses else "1=1"

    rows = conn.execute(
        f"""SELECT a.* FROM artifacts a
            WHERE {where}
            ORDER BY a.created_at DESC
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d["spec"], str):
            d["spec"] = json.loads(d["spec"])
        results.append(d)
    return results


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


def add_annotation(
    conn: sqlite3.Connection,
    conversation_id: str,
    body: str,
) -> dict:
    """Create an annotation on a conversation."""
    now = _now()
    aid = _uuid()
    conn.execute(
        "INSERT INTO annotations (id, conversation_id, body, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (aid, conversation_id, body, now, now),
    )
    conn.commit()
    return {"id": aid, "conversation_id": conversation_id, "body": body,
            "created_at": now, "updated_at": now}


def update_annotation(
    conn: sqlite3.Connection,
    annotation_id: str,
    body: str,
) -> dict | None:
    """Update an annotation's body."""
    now = _now()
    conn.execute(
        "UPDATE annotations SET body = ?, updated_at = ? WHERE id = ?",
        (body, now, annotation_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM annotations WHERE id = ?", (annotation_id,)
    ).fetchone()
    return dict(row) if row else None


def delete_annotation(conn: sqlite3.Connection, annotation_id: str) -> bool:
    """Hard delete an annotation. Returns True if a row was deleted."""
    cursor = conn.execute(
        "DELETE FROM annotations WHERE id = ?", (annotation_id,)
    )
    conn.commit()
    return cursor.rowcount > 0


def get_annotations(conn: sqlite3.Connection, conversation_id: str) -> list[dict]:
    """Get all annotations for a conversation."""
    rows = conn.execute(
        "SELECT * FROM annotations WHERE conversation_id = ? ORDER BY created_at",
        (conversation_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Full-text search
# ---------------------------------------------------------------------------


def search_messages(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Search messages via FTS5. Returns messages with conversation context."""
    rows = conn.execute(
        """SELECT m.*, c.title as conversation_title
           FROM messages m
           JOIN messages_fts ON messages_fts.rowid = m.rowid
           JOIN conversations c ON c.id = m.conversation_id
           WHERE messages_fts MATCH ?
           ORDER BY m.created_at DESC
           LIMIT ?""",
        (query, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def search_artifacts(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Search artifacts via FTS5."""
    rows = conn.execute(
        """SELECT a.*
           FROM artifacts a
           JOIN artifacts_fts ON artifacts_fts.rowid = a.rowid
           WHERE artifacts_fts MATCH ?
           ORDER BY a.created_at DESC
           LIMIT ?""",
        (query, limit),
    ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d["spec"], str):
            d["spec"] = json.loads(d["spec"])
        results.append(d)
    return results


# ---------------------------------------------------------------------------
# Conversation with full detail
# ---------------------------------------------------------------------------


def get_conversation_with_messages(
    conn: sqlite3.Connection,
    conversation_id: str,
) -> dict | None:
    """Fetch a conversation with all messages, tool calls, and artifacts."""
    conv = get_conversation(conn, conversation_id)
    if not conv:
        return None

    messages = get_messages(conn, conversation_id)
    for msg in messages:
        msg["tool_calls"] = get_tool_calls(conn, msg["id"])

    conv["messages"] = messages
    conv["artifacts"] = list_artifacts(conn, conversation_id=conversation_id, limit=1000)
    conv["annotations"] = get_annotations(conn, conversation_id)
    return conv
