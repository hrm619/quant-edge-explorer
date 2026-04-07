# PRD: Quant-Edge Explorer — Web App & Server Layer

**Status:** Draft v2 — revised to reflect existing implementation
**Date:** April 7, 2026
**Author:** hrm619 + Claude
**Companion to:** `prd_data_explorer.md` (the CLI explorer this layer wraps)

-----

## 1. Problem

The CLI explorer works well for single-session research, but three things are missing as the tool becomes a daily driver:

- **Visual rendering.** Tables print as monospace blocks; charts open in a separate browser tab via HTML files. There's no integrated view where prose, tables, and charts live side by side and stay together.
- **Memory and history.** Every CLI session is ephemeral. There's no way to find "the exploration where I noticed the WR target share pattern three weeks ago" without grepping shell history.
- **Artifact recall across conversations.** The platform's value compounds as the library of validated edges grows. Without a structured store of every table and chart generated, that compounding doesn't happen — each session starts from zero.

The web app solves all three. It is a personal research tool, not a SaaS — the constraints reflect that.

-----

## 2. Current State

Significant foundation work is already complete. The PRD describes what needs to be **built on top of** this, not built from scratch.

### What exists

| Component | Status | Key files |
|-----------|--------|-----------|
| **Two-phase agent loop** | Complete | `src/explorer/agent.py` — `run_agent_turn()` with callback hooks for plan, tool_start, tool_end |
| **History schema** | Complete | `src/explorer/history/schema.sql` — 6 tables (conversations, messages, tool_calls, artifacts, annotations) + FTS5 + triggers + indices |
| **History repository** | Complete | `src/explorer/history/repository.py` — Full CRUD for all tables, FTS search for messages and artifacts |
| **FastAPI server** | Complete | `src/server/app.py` — factory with CORS, routers for chat/conversations/artifacts |
| **SSE streaming chat** | Complete | `src/server/routers/chat.py` — bridges sync agent loop to async SSE via queue, persists all history |
| **Conversation CRUD** | Complete | `src/server/routers/conversations.py` — list/create/update/get + annotations CRUD |
| **Artifact CRUD** | Complete | `src/server/routers/artifacts.py` — list/get/update quality flag |
| **Title generation** | Complete | `src/server/titles.py` — Haiku-based title generation, called after first exchange |
| **Config & DI** | Complete | `src/server/config.py` + `dependencies.py` — Settings dataclass, connection singletons |
| **Pydantic schemas** | Complete | `src/server/schemas.py` — ChatRequest, ConversationSummary/Detail, Artifact, Annotations |
| **Chart engine** | Complete | `src/explorer/chart_engine.py` — `ChartSpec` already separates `figure` dict from HTML rendering |
| **Server tests** | Partial | `tests/test_server_routes.py` (268 lines), `tests/test_history_db.py` (381 lines) |

### What's missing

| Component | Status | Notes |
|-----------|--------|-------|
| **Server CLI** (`server/cli.py`) | Not started | `pyproject.toml` declares `quant-edge = "server.cli:main"` but module doesn't exist |
| **CLI as HTTP client** | Not started | `src/explorer/main.py` still runs the agent loop in-process |
| **Token-level streaming** | Not started | Current SSE emits `text_delta` as one block after agent completes; no per-token streaming |
| **React web app** | Not started | No `app/` directory |

### Architectural note: the PRD SSE events vs current SSE events

The current server emits these events: `conversation`, `phase`, `plan`, `tool_call_start`, `tool_call_end`, `artifact`, `text_delta`, `done`, `error`, `title_updated`.

This is a richer protocol than the original PRD proposed. The key difference from the original PRD's event model: the current implementation has `phase` events (planning/execution) and `plan` events that the original PRD didn't account for (it didn't know about the two-phase agent loop). The current protocol is correct and should be kept.

**Gap:** The `text_delta` event currently emits the full response text in a single event after the agent loop completes. True per-token streaming would require refactoring `agent.py` to use `client.messages.stream()` instead of `client.messages.create()`. This is a Phase 0 task.

-----

## 3. Solution

A React web app that provides a chat interface, persistent history, and an artifact browser. The FastAPI server already exists and wraps the `explorer` module. The web app is the primary new deliverable.

**Key architectural calls:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent runtime | FastAPI server (`localhost`) — **already built** | One source of truth for prompts, tools, data access |
| Frontend stack | Vite + React + TypeScript + Tailwind + shadcn/ui | Modern, fast, taste-forward. shadcn is a primitive library, not a design system |
| Repo placement | `/app` directory inside `quant-edge-explorer` | Monorepo. Simpler for solo dev |
| Data model | Conversations + Messages + ToolCalls + Artifacts — **already built** | Enables artifact search across conversations |
| Streaming | SSE (Server-Sent Events) — **already built** | Simpler than WebSockets, sufficient for one-way agent-to-client streaming |
| CLI mode | Dual-mode: in-process (default) + HTTP client (opt-in via `--server`) | Avoids forcing server dependency for quick CLI sessions |
| Auth | None for v1 | Single user, localhost. Tailscale when collaborator #2 arrives |
| Mobile | Not supported | Desktop tool. Optimize for 1440px+ |

### CLI dual-mode decision (revised from v1)

The original PRD mandated that the CLI become an HTTP client of the server, requiring the server to be running before the CLI could be used. This is a UX regression for a solo research tool — today you type `explore` and you're working.

**Revised approach:** The CLI keeps its in-process mode as the default. A `--server` flag (or auto-detect if port 8000 is listening) switches to HTTP client mode. History unification is achieved by having both the in-process CLI and the server write to the same SQLite history DB via `history/repository.py`. SQLite WAL mode handles concurrent readers/single-writer fine for a single-user tool.

This means:
- `explore` — works immediately, writes to `~/.quant-edge/history.db`
- `explore --server` — connects to running server, same history
- `quant-edge serve` — starts the FastAPI server for the web app
- The web app always talks to the server

-----

## 4. Repository Structure

New code is in bold. Existing files are shown for context.

```
quant-edge-explorer/
├── pyproject.toml                     # Existing — no new deps needed
├── config/
│   ├── priors.yaml                    # Existing
│   └── chart_registry.yaml           # Existing
├── src/explorer/                      # Existing CLI explorer module
│   ├── main.py                        # Existing — add --server flag + history persistence
│   ├── agent.py                       # Existing — add token-level streaming support
│   ├── system_prompt.py               # Existing — no changes
│   ├── tools.py                       # Existing — no changes
│   ├── tool_handlers.py               # Existing — no changes
│   ├── chart_engine.py                # Existing — no changes (ChartSpec.figure already available)
│   ├── canonical_charts.py            # Existing — no changes
│   ├── connections.py                 # Existing — no changes
│   ├── cli_render.py                  # Existing — no changes
│   └── history/
│       ├── db.py                      # Existing — no changes
│       ├── repository.py              # Existing — no changes
│       └── schema.sql                 # Existing — no changes
├── src/server/                        # Existing — extend
│   ├── __init__.py                    # Existing
│   ├── app.py                         # Existing — no changes
│   ├── config.py                      # Existing — no changes
│   ├── dependencies.py                # Existing — no changes
│   ├── schemas.py                     # Existing — no changes
│   ├── titles.py                      # Existing — no changes
│   ├── **cli.py**                     # **NEW** — `quant-edge serve` command
│   └── routers/
│       ├── chat.py                    # Existing — add per-token streaming
│       ├── conversations.py           # Existing — no changes
│       └── artifacts.py               # Existing — no changes
├── **app/**                           # **NEW** — React web app
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   │   ├── ChatRoute.tsx
│   │   │   ├── ArtifactsRoute.tsx       # Phase 3
│   │   │   └── ConversationRoute.tsx
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ConversationSidebar.tsx
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── ToolCallCard.tsx
│   │   │   │   ├── PlanCard.tsx           # Displays planning phase output
│   │   │   │   ├── InputBox.tsx
│   │   │   │   └── StreamingIndicator.tsx
│   │   │   ├── artifacts/
│   │   │   │   ├── TableArtifact.tsx
│   │   │   │   ├── ChartArtifact.tsx
│   │   │   │   └── CitationArtifact.tsx
│   │   │   ├── errors/
│   │   │   │   ├── ErrorBoundary.tsx      # Catches rendering errors
│   │   │   │   └── ConnectionStatus.tsx   # Server reachability indicator
│   │   │   └── ui/                        # shadcn primitives (added via CLI as needed)
│   │   ├── hooks/
│   │   │   ├── useConversation.ts
│   │   │   ├── useConversationList.ts
│   │   │   └── useArtifactSearch.ts
│   │   ├── lib/
│   │   │   ├── api.ts                     # Typed fetch wrappers
│   │   │   ├── sse.ts                     # SSE event parser
│   │   │   └── types.ts                   # Mirrors Pydantic models
│   │   └── styles/
│   │       └── globals.css
└── tests/
    ├── test_server_routes.py              # Existing — extend as needed
    ├── test_history_db.py                 # Existing — no changes
    └── (existing CLI tests)
```

-----

## 5. Data Model

The history database is already implemented as `explorer_history.db` (default: `~/.quant-edge/history.db`), separate from `fantasy_data.db` and `knowledge_base.db`.

### 5.1 Existing schema (no changes needed)

The schema in `src/explorer/history/schema.sql` already includes:

- **conversations** — id, title, created_at, updated_at, archived_at, starred, message_count
- **messages** — id, conversation_id, role, content, phase (planning/execution), created_at, ordinal
- **tool_calls** — id, message_id, tool_name, tool_input (JSON), tool_result (JSON), duration_ms, status, error_message, created_at
- **artifacts** — id, tool_call_id, conversation_id, kind, title, spec (JSON), searchable_text, quality_flag (unflagged/trusted/untrusted), created_at
- **annotations** — id, conversation_id, body (Markdown), created_at, updated_at
- **messages_fts** — FTS5 over message content, with insert/delete/update triggers
- **artifacts_fts** — FTS5 over artifact title + searchable_text, with triggers
- All relevant indices

The `phase` column on messages is a feature the original PRD didn't anticipate — it tracks whether a message came from the planning or execution phase of the two-phase agent loop. The web app should use this to render planning output differently (see `PlanCard` component in §7.2).

### 5.2 Quality flag semantics

Every artifact starts as `unflagged`. The user can mark it `trusted` (good analysis, surface prominently) or `untrusted` (bad query or misleading result, exclude from default search). Flags are per-artifact, not per-conversation.

The artifact browser default view shows `unflagged` + `trusted`. A filter toggle includes `untrusted` when debugging or auditing.

### 5.3 Soft delete semantics

Conversations have an `archived_at` timestamp. When set, the conversation disappears from the default sidebar but remains in the database. An "Archived" view in the sidebar lets the user see and unarchive them. No hard delete in v1.

-----

## 6. FastAPI Server

### 6.1 Existing endpoints (already implemented)

| Method | Path | Status |
|--------|------|--------|
| `POST` | `/api/v1/chat` | **Done** — SSE streaming, persists history, generates titles |
| `POST` | `/api/v1/conversations` | **Done** |
| `GET` | `/api/v1/conversations` | **Done** — archived, starred, q (FTS), limit, offset |
| `GET` | `/api/v1/conversations/{id}` | **Done** — includes messages, tool calls, artifacts, annotations |
| `PATCH` | `/api/v1/conversations/{id}` | **Done** — title, starred, archived_at |
| `GET` | `/api/v1/artifacts` | **Done** — q (FTS), kind, quality_flag, conversation_id, limit, offset |
| `GET` | `/api/v1/artifacts/{id}` | **Done** |
| `PATCH` | `/api/v1/artifacts/{id}` | **Done** — quality_flag |
| `POST` | `/api/v1/conversations/{id}/annotations` | **Done** |
| `PATCH` | `/api/v1/annotations/{id}` | **Done** |
| `DELETE` | `/api/v1/annotations/{id}` | **Done** |
| `GET` | `/health` | **Done** |

### 6.2 SSE event protocol (existing)

The current SSE protocol emits these events from `POST /api/v1/chat`:

```
event: conversation
data: {"conversation_id": "uuid"}

event: phase
data: {"phase": "planning"}

event: plan
data: {"text": "Research plan: ..."}

event: phase
data: {"phase": "execution"}

event: tool_call_start
data: {"id": "uuid", "name": "query_sql", "input": {...}}

event: tool_call_end
data: {"id": "uuid", "name": "query_sql", "status": "success", "duration_ms": 142, "row_count": 47}

event: artifact
data: {"id": "uuid", "kind": "table", "title": "...", "spec": {...}}

event: text_delta
data: {"text": "Full response text..."}

event: done
data: {"conversation_id": "uuid", "message_id": "uuid"}

event: title_updated
data: {"conversation_id": "uuid", "title": "WR target share regression candidates"}

event: error
data: {"message": "..."}
```

### 6.3 Gap: per-token streaming

**Current behavior:** The agent loop calls `client.messages.create()` (blocking), waits for the full response, then emits one `text_delta` event with the complete text.

**Target behavior:** The agent loop should call `client.messages.stream()` during the execution phase, emitting `token` events as they arrive. This gives the web app a real-time typing feel.

The planning phase can remain non-streaming (it's short and the plan is emitted as a single `plan` event). The execution phase response — which can be long — should stream per-token.

This requires changes to `agent.py`:
- Add a `on_token` callback: `Callable[[str], None]`
- In Phase 2, use `client.messages.stream()` instead of `client.messages.create()` for the final response (when no tool_use blocks are expected)
- Accumulate tokens into the response text while emitting each one

And to `routers/chat.py`:
- Add an `on_token` callback that pushes `token` events to the SSE queue
- Keep `text_delta` as a final event with the complete text (for reconciliation on reconnect)

### 6.4 New: Server CLI (`src/server/cli.py`)

The `quant-edge` entry point is declared in `pyproject.toml` but the module doesn't exist. It needs:

```python
# src/server/cli.py
import click
import uvicorn
from server.config import get_settings

@click.group()
def main():
    """Quant-Edge Explorer server and utilities."""
    pass

@main.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8000, type=int)
@click.option("--reload", is_flag=True, default=False)
def serve(host, port, reload):
    """Start the FastAPI server."""
    uvicorn.run("server.app:app", host=host, port=port, reload=reload)

@main.command()
@click.option("--limit", default=20, type=int)
def history(limit):
    """List recent conversations."""
    # Query history DB directly, print with Rich

@main.command()
@click.argument("conversation_id")
def resume(conversation_id):
    """Resume a conversation (opens in CLI or prints URL)."""
    pass
```

### 6.5 CLI dual-mode integration

`src/explorer/main.py` adds:
- `--server` flag: when set, POST to `http://localhost:8000/api/v1/chat` and consume SSE stream via `httpx`
- Default (no flag): run agent loop in-process as today, but also persist to `~/.quant-edge/history.db` via `history/repository.py`
- History persistence in the in-process path is the new work here — currently the CLI is ephemeral

-----

## 7. Web App: Phase 1 (Minimal Chat)

The first usable web build. One route, one page, end-to-end working chat.

### 7.1 Layout

```
+-------------------------------------------------------------+
|  Quant-Edge Explorer                              [+ New]    |
+--------------+----------------------------------------------+
|              |                                               |
|  Today       |  +--------------------------------------+     |
|  > WR target |  | User: show me WRs with high target  |     |
|    share...  |  | share but low CROE                   |     |
|  > DEF vs    |  +--------------------------------------+     |
|    spread    |                                               |
|              |  +--------------------------------------+     |
|  Yesterday   |  | Planning...                          |     |
|  > Rookie WR |  | > Thesis: WRs with high target      |     |
|    rankings  |  |   share and low CROE may be          |     |
|              |  |   regression candidates...           |     |
|  Last week   |  +--------------------------------------+     |
|  > ...       |                                               |
|              |  +--------------------------------------+     |
|              |  | Assistant: These 8 WRs have target   |     |
|              |  | share above the 75th percentile...   |     |
|              |  |                                      |     |
|              |  | > query_sql: 47 rows                 |     |
|              |  |                                      |     |
|              |  | [Table: WR Regression Candidates]    |     |
|              |  | Player    | Tgt Share | CROE | ...   |     |
|              |  | ...                                  |     |
|              |  +--------------------------------------+     |
|              |                                               |
|              |  +--------------------------------------+     |
|              |  | Type a message...                    |     |
|              |  +--------------------------------------+     |
+--------------+----------------------------------------------+
```

Note the **planning phase** is visible as a distinct card between the user message and the assistant response. This reflects the two-phase agent loop architecture.

### 7.2 Component responsibilities

**`ConversationSidebar`** — Lists conversations grouped by date bucket (Today / Yesterday / Last week / Older). Shows title, message count, starred indicator. Click to load. "+ New" button creates a new conversation. No search yet (Phase 2).

**`MessageList`** — Renders the active conversation. Auto-scrolls to bottom on new content. Each turn consists of: user `MessageBubble` → `PlanCard` → assistant block (prose + `ToolCallCard`s + artifacts).

**`MessageBubble`** — Simple styled container. User messages right-aligned, muted background. Assistant prose rendered via `react-markdown` + `remark-gfm`, with code blocks syntax-highlighted via `shiki` or `prism-react-renderer`.

**`PlanCard`** — Renders the planning phase output. Collapsed by default after streaming completes, expanded while the plan is being generated. Header shows "Research Plan" with a toggle. Content is the structured plan text rendered as markdown. Visually distinct from assistant messages — lighter background, italic header, left-aligned.

**`ToolCallCard`** — Collapsed by default. Header shows tool name, status icon, duration, one-line summary. Expanded shows the full input args (JSON, syntax highlighted) and a preview of the raw output. Tool calls sit between the assistant's prose blocks at full width, not inside message bubbles.

**`TableArtifact`** — Full-width below the message text. TanStack Table with sortable columns, sticky header, optional pagination (default 50 rows). Has an export-to-CSV button and a quality flag menu in the corner. Numeric values right-aligned; trust weight columns get a colored badge based on the threshold.

**`ChartArtifact`** — Full-width Plotly chart via `react-plotly.js`, rendered from the `spec.figure` the server sent in the artifact event. Includes the same flag menu as tables. Inherits the existing palette from the chart engine (Okabe-Ito, position colors).

**`InputBox`** — Textarea, autosize, Cmd+Enter to send. Disabled while a stream is in flight. Shows a subtle streaming indicator (pulsing dot) when the assistant is responding.

**`StreamingIndicator`** — Inline status: "Planning..." / "Querying SQL..." / "Searching knowledge base..." / "Generating chart..." based on the most recent `phase` or `tool_call_start` event. Disappears on `done`.

**`ErrorBoundary`** — Catches rendering errors in child components (e.g., malformed chart spec) and displays a fallback with the error message and a "retry" option.

**`ConnectionStatus`** — Polls `/health` on mount and on visibility change. Shows a banner when the server is unreachable. Dismisses automatically when connection is restored.

### 7.3 Error handling

| Scenario | Behavior |
|----------|----------|
| Server unreachable | `ConnectionStatus` banner: "Server unavailable — start with `quant-edge serve`". Input disabled. |
| SSE stream drops mid-response | Detect via `EventSource` `error` event or fetch abort. Show inline error with "Retry" button. On retry, refetch conversation state from `GET /api/v1/conversations/{id}` to reconcile. |
| Tool call fails | `ToolCallCard` shows red status icon + `error_message`. Agent continues (the model handles tool errors). |
| Chart spec malformed | `ChartArtifact` wrapped in `ErrorBoundary` — falls back to showing the raw JSON spec in a code block. |
| Network timeout | `api.ts` wrappers use AbortController with 60s timeout for SSE, 10s for REST calls. |

### 7.4 SSE consumer hook

```typescript
// app/src/hooks/useConversation.ts (sketch)

interface UseConversationResult {
  messages: Message[];
  artifacts: Map<string, Artifact>;
  toolCalls: Map<string, ToolCall>;
  plan: string | null;
  phase: 'idle' | 'planning' | 'execution';
  isStreaming: boolean;
  currentToolName: string | null;
  sendMessage: (content: string) => Promise<void>;
  error: Error | null;
}

export function useConversation(conversationId: string): UseConversationResult {
  // Maintain local state for messages, artifacts, tool calls, plan
  // sendMessage opens a fetch+ReadableStream to POST /api/v1/chat
  // Dispatch on event type:
  //   conversation → store conversation_id
  //   phase → update phase state
  //   plan → set plan text
  //   tool_call_start → add to toolCalls map, set currentToolName
  //   tool_call_end → update toolCalls map, clear currentToolName
  //   artifact → add to artifacts map
  //   token → append to streaming message text
  //   text_delta → set final message text (reconciliation)
  //   done → set isStreaming=false
  //   title_updated → update conversation title
  //   error → set error state
  // On done, refetch conversation from REST API to reconcile any drift
}
```

The hook returns three separate maps (messages, artifacts, tool calls) keyed by id. Components compose them at render time. This avoids deeply nested message objects and makes it easy to flag/update an artifact without re-rendering the whole conversation.

### 7.5 Visual taste guardrails

shadcn nudges toward rounded SaaS aesthetics. We want this to feel like a tool, not a marketing site.

- **Density:** tighter than shadcn defaults. Reduce default padding by 20-30%
- **Typography:** Inter for UI, JetBrains Mono for SQL/code/numeric tables
- **Color:** muted, mostly grayscale with sparing accent colors. The accent palette mirrors the chart engine: Okabe-Ito orange for highlights, semantic green/red for trust/regression flags
- **Borders over shadows:** flat 1px borders, not drop shadows
- **No animation theatrics:** transitions are 100-150ms, easing-out, on hover/focus only. No bouncy springs, no slide-ins
- **Reference apps:** Linear, Hex, Observable Notebook, Retool. Not Stripe, not Vercel marketing pages

### 7.6 Plotly bundle size

`plotly.js` is ~3.5MB minified. Since this is a local tool, acceptable — but use `plotly.js-basic-dist-min` to cut to ~1MB. Lazy-load `ChartArtifact` via `React.lazy()` so the initial page load isn't blocked by Plotly.

### 7.7 Phase 1 exit criteria

1. User can start the server with `quant-edge serve`
2. User can open `http://localhost:5173` (Vite dev server) and see an empty chat
3. User can create a new conversation, send a message, and watch the response stream in
4. Planning phase output appears as a collapsible card before the assistant response
5. SQL queries, KB searches, and chart generation all work end-to-end
6. Tables render as TanStack Tables, charts render as native Plotly figures (no iframes)
7. The conversation persists — refreshing the page loads it from history
8. Sidebar shows all past conversations grouped by date
9. Server unavailability shows a clear error state, not a blank screen

-----

## 8. Phase 2: History, Search, and Annotations

### 8.1 What ships

- **FTS5 search in the sidebar.** A search input above the conversation list. Searches titles + message content via the existing `GET /api/v1/conversations?q=...` endpoint. Hits show snippet with the matched term highlighted.
- **Editable titles.** Click-to-edit inline in both the sidebar and the conversation header.
- **Starring.** Star button in the conversation header. Starred conversations get a section at the top of the sidebar.
- **Archive.** "Archive" button in conversation header. Archived conversations move to a collapsed "Archived" section at the bottom of the sidebar (opt-in expand).
- **Date grouping refinement.** Today / Yesterday / This week / Last week / This month / Older.
- **Annotations panel.** A collapsible right sidebar where the user writes free-text markdown notes. Multiple annotations per conversation, each with its own timestamp. Uses the existing annotation CRUD endpoints.

### 8.2 Server changes

None — all endpoints already exist:
- `GET /conversations?q=...` runs FTS search
- `PATCH /conversations/{id}` accepts title, starred, archived_at
- `POST /conversations/{id}/annotations`, `PATCH /annotations/{id}`, `DELETE /annotations/{id}`
- Title generation already runs after first exchange

### 8.3 Phase 2 exit criteria

1. User can search across all conversations and find them by content, not just title
2. New conversations get meaningful titles within ~2 seconds of the first response
3. Titles are editable; archive and star work; archived conversations stay out of the default view
4. User can write persistent notes alongside any conversation without disrupting the chat flow

-----

## 9. Phase 3: Artifact Browser

The feature that justifies the web app over the CLI.

### 9.1 What ships

- **New route: `/artifacts`**
- **Filterable list of every artifact ever generated.** Filters: kind (table/chart/citation), date range, conversation, quality flag (default: unflagged + trusted). Uses the existing `GET /api/v1/artifacts` endpoint.
- **Full-text search across artifact content** via `artifacts_fts`. Searches titles, column names, and flattened cell values
- **Click-through to source conversation.** Each artifact links back to the conversation and message that produced it, with the relevant message scrolled into view
- **Quality flag controls.** Mark an artifact trusted/untrusted from the browser via `PATCH /api/v1/artifacts/{id}`
- **Inline preview.** Hover or click expands the artifact in place — table rows, chart thumbnail

### 9.2 Server changes

None — all endpoints already exist. The `searchable_text` field is populated when the artifact is created (for tables: column names + first 100 rows of values; for charts: title; for citations: analyst + title + text excerpt).

### 9.3 Phase 3 exit criteria

1. User can find any past artifact in under 10 seconds via filter or search
2. Untrusted artifacts are excluded from default search but recoverable via the filter
3. The artifact browser feels like a standalone tool, not an afterthought

-----

## 10. Phase 4: Exports

### 10.1 What ships

- **Export conversation as Markdown.** Includes prose, tool calls (collapsed by default in the markdown via `<details>` tags), tables (as markdown tables), and chart references (as image links or embedded SVG)
- **Export conversation as PDF.** Same content, formatted for sharing
- **Bulk artifact export.** From the artifact browser: select N artifacts, export as a single document or zip

### 10.2 Phase 4 exit criteria

1. A conversation can be exported and shared as a self-contained markdown or PDF file
2. Bulk artifact selection and export works for assembling research summaries

-----

## 11. Out of Scope (v1)

| Out of scope | Why |
|--------------|-----|
| User authentication | Single user, localhost. Tailscale handles access when collaborators arrive. |
| Multi-tenant / workspaces | Not multi-tenant. |
| Real-time collaboration | Not enough users to matter. |
| Mobile responsive design | Desktop research tool. |
| Message editing / regeneration | Adds complexity; "start a new conversation" is fine. |
| Cross-conversation agent memory | Tempting, deep rabbit hole. Let the user manage context manually for now. |
| Hard delete | Soft delete + quality flags cover the real need. |
| Server-side prompt customization UI | Edit `priors.yaml` directly. |
| Streaming over WebSockets | SSE is sufficient and simpler. |
| Deployment / hosting infra | `localhost` only. |

-----

## 12. Implementation Sequence

| Phase | Work | Depends on | New code |
|-------|------|------------|----------|
| 0 | Server CLI (`cli.py`), per-token streaming in agent loop, CLI history persistence, CLI `--server` mode | — | ~200 lines Python |
| 1 | React app: chat route, sidebar, message + plan rendering, tool call cards, table + chart artifacts, error states | Phase 0 | ~2000 lines TypeScript |
| 2 | Sidebar search, edit/star/archive UI, annotations panel | Phase 1 | ~800 lines TypeScript |
| 3 | Artifact browser route, artifact search, quality flag UI | Phase 1 (independent of Phase 2) | ~600 lines TypeScript |
| 4 | Markdown/PDF export | Phase 2 | ~400 lines TypeScript + Python |

**Phase 0 is small but critical.** The server and data model are already built. Phase 0 fills the remaining gaps so the web app has a complete backend to talk to. The main risk is per-token streaming — it touches the agent loop, which is the most important code in the system.

**Phase 1 is where most of the work is.** Building the React app from scratch. The good news: the API surface it consumes is fully defined and already tested.

-----

## 13. Dependencies

### Python (already in `pyproject.toml`)

All server-side dependencies are already declared. The only addition needed is `click` if it's not already a transitive dependency (it is, via `fantasy-data`).

### Node (new `app/package.json`)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-table": "^8.20.0",
    "react-plotly.js": "^2.6.0",
    "plotly.js-basic-dist-min": "^2.35.0",
    "react-markdown": "^9.0.0",
    "remark-gfm": "^4.0.0",
    "shiki": "^1.22.0",
    "lucide-react": "^0.460.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

shadcn components added via CLI as needed (button, input, dialog, dropdown-menu, scroll-area, tabs, badge, separator). Don't pre-install all of them.

Note: `plotly.js-basic-dist-min` instead of full `plotly.js` to cut bundle size from ~3.5MB to ~1MB.

-----

## 14. Open Decisions

| # | Decision | Recommendation | Status |
|---|----------|---------------|--------|
| 1 | Server port | 8000 (current default in `config.py`) | Confirmed |
| 2 | History DB location | `~/.quant-edge/history.db` (current default in `config.py`) | Confirmed |
| 3 | SSE consumer: Vercel `ai` SDK or hand-rolled | Hand-rolled — richer event model (planning phase, artifacts) than the SDK assumes | Confirmed |
| 4 | Title generation: sync or async | Currently sync in the SSE stream (after response). Fine for v1; can move to background task later. | Confirmed |
| 5 | Artifact `searchable_text` for tables: how many rows | First 100 rows (already implemented in `chat.py`). | Confirmed |
| 6 | Date library | `date-fns` (lighter than moment, more ergonomic than native) | Tentative |
| 7 | Code highlighting | `shiki` (best looking, build-time themes) | Tentative |
| 8 | CLI in-process history or server-only history | Dual-mode: in-process writes to same DB; `--server` flag for HTTP mode | Confirmed |

-----

## 15. Success Criteria

The web app is working when:

1. You can spend a research session entirely in the browser without missing the CLI
2. You can find a past artifact from three weeks ago in under 10 seconds
3. Marking analysis as untrusted feels safe — you trust that it's hidden but recoverable
4. You start using the artifact browser as a launching point for new questions ("here's the table I made last week, let me dig deeper into row 7")
5. The CLI and web app feel like two views on the same thing, not two separate tools
6. After two weeks of use, opening a fresh CLI session feels like a downgrade
