-- History database schema for quant-edge-explorer.
-- Stores conversations, messages, tool calls, artifacts, and annotations.

CREATE TABLE IF NOT EXISTS conversations (
    id              TEXT PRIMARY KEY,
    title           TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    archived_at     TEXT,
    starred         INTEGER NOT NULL DEFAULT 0,
    message_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,      -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    phase           TEXT,               -- 'planning' | 'execution' | NULL
    created_at      TEXT NOT NULL,
    ordinal         INTEGER NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id              TEXT PRIMARY KEY,
    message_id      TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    tool_input      TEXT NOT NULL,      -- JSON
    tool_result     TEXT,               -- JSON
    duration_ms     INTEGER,
    status          TEXT NOT NULL DEFAULT 'success',  -- 'success' | 'error'
    error_message   TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id              TEXT PRIMARY KEY,
    tool_call_id    TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    kind            TEXT NOT NULL,      -- 'table' | 'chart' | 'citation_set'
    title           TEXT,
    spec            TEXT NOT NULL,      -- JSON: table data, Plotly spec, or citation list
    searchable_text TEXT NOT NULL,
    quality_flag    TEXT NOT NULL DEFAULT 'unflagged',  -- 'unflagged' | 'trusted' | 'untrusted'
    created_at      TEXT NOT NULL,
    FOREIGN KEY (tool_call_id) REFERENCES tool_calls(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS annotations (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    body            TEXT NOT NULL,      -- Markdown
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Full-text search over messages
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    content='messages',
    content_rowid='rowid'
);

-- FTS sync triggers for messages
CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
END;

CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES ('delete', old.rowid, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.rowid, new.content);
END;

-- Full-text search over artifacts
CREATE VIRTUAL TABLE IF NOT EXISTS artifacts_fts USING fts5(
    title,
    searchable_text,
    content='artifacts',
    content_rowid='rowid'
);

-- FTS sync triggers for artifacts
CREATE TRIGGER IF NOT EXISTS artifacts_fts_insert AFTER INSERT ON artifacts BEGIN
    INSERT INTO artifacts_fts(rowid, title, searchable_text)
        VALUES (new.rowid, COALESCE(new.title, ''), new.searchable_text);
END;

CREATE TRIGGER IF NOT EXISTS artifacts_fts_delete AFTER DELETE ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifacts_fts, rowid, title, searchable_text)
        VALUES ('delete', old.rowid, COALESCE(old.title, ''), old.searchable_text);
END;

CREATE TRIGGER IF NOT EXISTS artifacts_fts_update AFTER UPDATE ON artifacts BEGIN
    INSERT INTO artifacts_fts(artifacts_fts, rowid, title, searchable_text)
        VALUES ('delete', old.rowid, COALESCE(old.title, ''), old.searchable_text);
    INSERT INTO artifacts_fts(rowid, title, searchable_text)
        VALUES (new.rowid, COALESCE(new.title, ''), new.searchable_text);
END;

-- Indices
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, ordinal);
CREATE INDEX IF NOT EXISTS idx_tool_calls_message ON tool_calls(message_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_conversation ON artifacts(conversation_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_kind ON artifacts(kind);
CREATE INDEX IF NOT EXISTS idx_artifacts_quality ON artifacts(quality_flag);
CREATE INDEX IF NOT EXISTS idx_conversations_archived ON conversations(archived_at);
CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
