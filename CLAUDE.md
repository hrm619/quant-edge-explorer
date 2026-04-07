# CLAUDE.md

## Project Overview

**quant-edge-explorer** is a conversational research agent for the quant-edge platform. It provides an interactive CLI where you can query the fantasy-data SQLite database, search the knowledge-base ChromaDB vector store, and generate charts — all through natural language conversation using the Anthropic tool-use API.

## Development Setup

Uses **uv** for package management. Python 3.13.

```bash
uv sync                # install dependencies
uv run explore         # launch the interactive agent
```

Requires `.env` with `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`.

## Testing

```bash
uv run pytest tests/ -v
```

All API calls (Anthropic, OpenAI) are mocked in tests. 62 tests across 4 files.

## Architecture

### Two-Phase Agent Loop

The agent uses a **plan-then-execute** architecture:

1. **Planning phase** — On each user message, the model is called with no tools available, forcing it to output a structured research plan (thesis, key questions, priors to test, argument structure). The plan is printed to the console and injected into the conversation.
2. **Execution phase** — Normal tool-use loop. The model sees its own plan in context, so tool calls follow the plan's structure and the final response delivers the argument.

This is implemented in `_run_agent_loop()` in `main.py`.

### System Prompt Structure

The system prompt has 6 sections (built by `build_system_prompt()` in `system_prompt.py`):

1. **Schema Awareness** — full SQLite schema (tables, columns, data coverage notes)
2. **KB Awareness** — ChromaDB collections, metadata filters, analyst roster
3. **Analytical Priors** — loaded from `config/priors.yaml` (market structure, player evaluation, signal hierarchy, red flags, thresholds)
4. **Chart Conventions** — when to chart, type selection, color modes, context requirements, takeaways
5. **Analysis Framework** — narrative arc (verdict → evidence → charts as arguments → confront priors → recommendation), depth calibration, triangulation protocol
6. **Editorial Voice** — tone guidelines (opinionated, precise, efficient)

### Three Tools

- `query_sql` — Read-only SQLite queries against fantasy_data.db (500-row limit, 5s timeout, write-op blocking)
- `search_knowledge_base` — Semantic search in ChromaDB with metadata filters (analyst, trust tier, season, etc.)
- `generate_chart` — Plotly chart generation with NYT-inspired theme. Supports canonical (named charts from fantasy-data) and adhoc modes. Features: reference lines, annotations, takeaways panel, subtitle/source, 4 color modes, auto-legend.

### Canonical Chart Registry

`config/chart_registry.yaml` declares hand-crafted chart functions in `fantasy-data` that the agent can invoke by name. Currently empty — charts are promoted to canonical status after validation in research sessions. The registry is loaded at startup and the `generate_chart` tool schema is generated dynamically from it.

## Dependencies

- `fantasy-data` (editable local dep at `../fantasy-data`) — SQLite database, NYT viz theme
- `knowledge-base` (editable local dep at `../knowledge-base`) — ChromaDB vector store, semantic search
- `scipy` — KDE computation for opportunity distribution charts (transitive via fantasy-data viz)

## Key Files

| File | Purpose |
|------|---------|
| `src/explorer/main.py` | Entry point — two-phase agent loop (plan → execute) |
| `src/explorer/system_prompt.py` | System prompt builder (schema + KB + priors + charts + framework + voice) |
| `src/explorer/tools.py` | Tool definitions — dynamic schema generation from chart registry |
| `src/explorer/tool_handlers.py` | Tool execution (SQL, KB search, chart dispatch) |
| `src/explorer/chart_engine.py` | Adhoc chart builders + canonical chart dispatch, NYT theme |
| `src/explorer/canonical_charts.py` | Chart registry YAML loader + CanonicalChart dataclass |
| `src/explorer/connections.py` | SQLite + ChromaDB + OpenAI connection management |
| `config/priors.yaml` | Analytical priors (externalized for iteration) |
| `config/chart_registry.yaml` | Canonical chart registry (empty, ready for promotion) |
