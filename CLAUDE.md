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

All API calls (Anthropic, OpenAI) are mocked in tests.

## Architecture

- **Single-agent tool-use loop** — no framework, ~200 lines of orchestration
- **Three tools**: `query_sql` (SQLite), `search_knowledge_base` (ChromaDB), `generate_chart` (Plotly)
- **System prompt** contains schema awareness, KB awareness, analytical priors, and chart conventions
- **Priors** live in `config/priors.yaml` for easy iteration

## Dependencies

- `fantasy-data` (editable local dep at `../fantasy-data`) — SQLite database, viz theme
- `knowledge-base` (editable local dep at `../knowledge-base`) — ChromaDB vector store, search

## Key Files

| File | Purpose |
|------|---------|
| `src/explorer/main.py` | Entry point — conversation loop |
| `src/explorer/system_prompt.py` | Builds system prompt from schema + priors |
| `src/explorer/tools.py` | Tool definitions (JSON schemas for Anthropic API) |
| `src/explorer/tool_handlers.py` | Tool execution (SQL, KB search, charts) |
| `src/explorer/chart_engine.py` | Chart generation using fantasy-data viz theme |
| `src/explorer/connections.py` | SQLite + ChromaDB connection management |
| `config/priors.yaml` | Analytical priors (externalized for iteration) |
