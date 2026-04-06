"""Tool execution — dispatch and implement query_sql, search_kb, generate_chart."""

import json
import re
import sqlite3
from pathlib import Path

from knowledge_base.embedder import get_or_create_collection
from knowledge_base.vector_store import build_where_filter, search

from explorer.canonical_charts import CanonicalChart
from explorer.chart_engine import render_chart
from explorer.connections import Connections

ROW_LIMIT = 500
QUERY_TIMEOUT_SECONDS = 5

# Statements that are not allowed in SQL queries
_WRITE_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|REINDEX|VACUUM|PRAGMA)\b",
    re.IGNORECASE,
)


def dispatch_tool(
    tool_name: str,
    tool_input: dict,
    connections: Connections,
    charts_dir: Path,
    chart_registry: dict[str, CanonicalChart] | None = None,
) -> str:
    """Route a tool call to the appropriate handler. Returns JSON string."""
    if tool_name == "query_sql":
        return handle_query_sql(
            sql=tool_input["sql"],
            description=tool_input.get("description", ""),
            connections=connections,
        )
    elif tool_name == "search_knowledge_base":
        return handle_search_knowledge_base(
            query=tool_input["query"],
            domain=tool_input.get("domain", "fantasy_football"),
            top_k=tool_input.get("top_k", 5),
            filters=tool_input.get("filters", {}),
            connections=connections,
        )
    elif tool_name == "generate_chart":
        return handle_generate_chart(
            spec=tool_input,
            charts_dir=charts_dir,
            registry=chart_registry,
        )
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


def handle_query_sql(
    sql: str,
    description: str,
    connections: Connections,
) -> str:
    """Execute a read-only SQL query against the fantasy-data database."""
    # Reject write operations
    if _WRITE_PATTERN.search(sql):
        return json.dumps({
            "error": "Only SELECT queries are allowed. Write operations are blocked.",
        })

    conn = connections.get_sqlite_connection()
    try:
        conn.execute(f"PRAGMA busy_timeout = {QUERY_TIMEOUT_SECONDS * 1000}")

        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(ROW_LIMIT + 1)

        truncated = len(rows) > ROW_LIMIT
        if truncated:
            rows = rows[:ROW_LIMIT]

        result_rows = [dict(zip(columns, row)) for row in rows]

        result = {
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "description": description,
        }
        if truncated:
            result["warning"] = f"Results truncated to {ROW_LIMIT} rows."

        return json.dumps(result, default=str)

    except sqlite3.OperationalError as e:
        return json.dumps({"error": f"SQL error: {e}"})
    except Exception as e:
        return json.dumps({"error": f"Query failed: {e}"})
    finally:
        conn.close()


def handle_search_knowledge_base(
    query: str,
    domain: str,
    top_k: int,
    filters: dict,
    connections: Connections,
) -> str:
    """Semantic search across the ChromaDB knowledge base."""
    try:
        where = build_where_filter(
            analyst=filters.get("analyst"),
            trust_tier=filters.get("trust_tier"),
            source_type=filters.get("source_type"),
            date_from=filters.get("date_from"),
            date_to=filters.get("date_to"),
            season=filters.get("season"),
            content_tag=filters.get("content_tag"),
        )

        collection = connections.get_collection(domain)

        results = search(
            query=query,
            collection=collection,
            client=connections.openai_client,
            top_k=top_k,
            where=where,
        )

        output = []
        for r in results:
            output.append({
                "text": r.text,
                "distance": round(r.distance, 4),
                "analyst": r.metadata.get("analyst", ""),
                "title": r.metadata.get("title", ""),
                "source_type": r.metadata.get("source_type", ""),
                "trust_tier": r.metadata.get("trust_tier", ""),
                "published_at": r.metadata.get("published_at", ""),
                "content_tag": r.metadata.get("content_tag", ""),
            })

        return json.dumps({
            "results": output,
            "result_count": len(output),
            "query": query,
            "domain": domain,
        })

    except Exception as e:
        return json.dumps({"error": f"Knowledge base search failed: {e}"})


def handle_generate_chart(
    spec: dict,
    charts_dir: Path,
    registry: dict[str, CanonicalChart] | None = None,
) -> str:
    """Generate a chart from a structured specification."""
    try:
        charts_dir.mkdir(parents=True, exist_ok=True)
        result = render_chart(spec, charts_dir, registry=registry)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Chart generation failed: {e}"})
