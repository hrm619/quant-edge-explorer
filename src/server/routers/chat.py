"""SSE streaming chat endpoint — bridges the sync agent loop to async SSE."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

import anthropic
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from explorer.agent import AgentConfig, AgentTurn, run_agent_turn
from explorer.canonical_charts import load_registry
from explorer.chart_engine import build_chart_spec
from explorer.connections import Connections
from explorer.history import repository as repo
from explorer.system_prompt import build_system_prompt
from explorer.tools import build_tools
from server.config import Settings, get_settings
from server.dependencies import get_connections, get_history_conn
from server.schemas import ChatRequest
from server.titles import generate_title

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

CHARTS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "charts"
REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "chart_registry.yaml"


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _build_artifact_from_tool(
    tool_name: str,
    tool_input: dict,
    tool_result_json: str,
    tool_id: str,
    conversation_id: str,
    conn: sqlite3.Connection,
    registry: dict | None = None,
) -> dict | None:
    """Extract an artifact from a tool call result, if applicable."""
    try:
        result = json.loads(tool_result_json)
    except (json.JSONDecodeError, TypeError):
        return None

    if "error" in result:
        return None

    if tool_name == "query_sql" and "rows" in result:
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        searchable = " ".join(columns)
        if rows:
            # Flatten first 100 rows for search
            for row in rows[:100]:
                searchable += " " + " ".join(str(v) for v in row.values())
        title = tool_input.get("description", "SQL query result")
        return repo.add_artifact(
            conn, conversation_id, tool_id, "table",
            title, {"columns": columns, "rows": rows, "row_count": result.get("row_count", 0)},
            searchable,
        )

    if tool_name == "generate_chart" and "path" in result:
        # Build the Plotly spec for the artifact
        try:
            chart_spec = build_chart_spec(tool_input, registry)
            spec_data = chart_spec.figure
            title = chart_spec.title
            searchable = title
        except Exception:
            spec_data = {"path": result["path"]}
            title = result.get("title", "Chart")
            searchable = title
        return repo.add_artifact(
            conn, conversation_id, tool_id, "chart",
            title, spec_data, searchable,
        )

    if tool_name == "search_knowledge_base" and "results" in result:
        results = result.get("results", [])
        searchable = " ".join(
            f"{r.get('analyst', '')} {r.get('title', '')} {r.get('text', '')[:200]}"
            for r in results
        )
        return repo.add_artifact(
            conn, conversation_id, tool_id, "citation_set",
            f"KB search: {result.get('query', '')[:80]}",
            {"results": results, "query": result.get("query", "")},
            searchable,
        )

    return None


async def _stream_agent_turn(
    request: ChatRequest,
    connections: Connections,
    history_conn: sqlite3.Connection,
    settings: Settings,
) -> asyncio.AsyncIterator[str]:
    """Run the agent loop in a thread pool and yield SSE events."""
    loop = asyncio.get_event_loop()
    queue: asyncio.Queue[tuple[str, dict] | None] = asyncio.Queue()

    # Create or resume conversation
    if request.conversation_id:
        conv = repo.get_conversation(history_conn, request.conversation_id)
        if not conv:
            yield _sse_event("error", {"message": "Conversation not found"})
            return
        conversation_id = conv["id"]
    else:
        conv = repo.create_conversation(history_conn)
        conversation_id = conv["id"]

    yield _sse_event("conversation", {"conversation_id": conversation_id})

    # Store user message
    user_msg = repo.add_message(history_conn, conversation_id, "user", request.message)
    is_first_exchange = conv.get("message_count", 0) == 0

    # Load conversation history for the Anthropic API
    history_messages = repo.get_messages(history_conn, conversation_id)
    api_messages = [{"role": m["role"], "content": m["content"]} for m in history_messages]

    # Build tools and system prompt
    chart_registry = load_registry(REGISTRY_PATH) if REGISTRY_PATH.exists() else {}
    tools = build_tools(chart_registry)
    system_prompt = build_system_prompt()
    config = AgentConfig(model=settings.model)

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Callbacks push events to the async queue from the sync thread
    def on_plan(text: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ("phase", {"phase": "planning"}))
        loop.call_soon_threadsafe(queue.put_nowait, ("plan", {"text": text}))
        loop.call_soon_threadsafe(queue.put_nowait, ("phase", {"phase": "execution"}))

    def on_tool_start(tool_id: str, tool_name: str, tool_input: dict) -> None:
        loop.call_soon_threadsafe(
            queue.put_nowait,
            ("tool_call_start", {"id": tool_id, "name": tool_name, "input": tool_input}),
        )

    def on_tool_end(tool_id: str, tool_name: str, result_json: str, duration_ms: int) -> None:
        # Determine row count for table results
        extra = {"id": tool_id, "name": tool_name, "status": "success", "duration_ms": duration_ms}
        try:
            parsed = json.loads(result_json)
            if "error" in parsed:
                extra["status"] = "error"
            if "row_count" in parsed:
                extra["row_count"] = parsed["row_count"]
        except (json.JSONDecodeError, TypeError):
            pass
        loop.call_soon_threadsafe(queue.put_nowait, ("tool_call_end", extra))

    # Run the synchronous agent loop in a thread pool
    def run_sync() -> AgentTurn:
        return run_agent_turn(
            client=client,
            system_prompt=system_prompt,
            messages=api_messages,
            connections=connections,
            tools=tools,
            config=config,
            chart_registry=chart_registry,
            charts_dir=CHARTS_DIR,
            on_plan=on_plan,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        )

    task = loop.run_in_executor(None, run_sync)

    # Yield SSE events as they arrive from the thread
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=0.1)
            if item is None:
                break
            event_type, data = item
            yield _sse_event(event_type, data)
        except asyncio.TimeoutError:
            if task.done():
                # Drain remaining events
                while not queue.empty():
                    item = queue.get_nowait()
                    if item is not None:
                        yield _sse_event(item[0], item[1])
                break

    # Get the result (may raise if the agent errored)
    try:
        turn: AgentTurn = await task
    except Exception as e:
        logger.exception("Agent loop failed")
        yield _sse_event("error", {"message": str(e)})
        return

    # Persist plan as a message
    if turn.plan_text:
        repo.add_message(history_conn, conversation_id, "assistant", turn.plan_text, phase="planning")
        repo.add_message(
            history_conn, conversation_id, "user",
            "Proceed with the research plan. Execute your queries and analysis now.",
        )

    # Persist assistant message and tool calls
    assistant_msg = repo.add_message(
        history_conn, conversation_id, "assistant", turn.response_text, phase="execution",
    )

    artifacts = []
    for tc in turn.tool_calls:
        status = "success"
        error_msg = None
        try:
            parsed = json.loads(tc.result)
            if "error" in parsed:
                status = "error"
                error_msg = parsed["error"]
        except (json.JSONDecodeError, TypeError):
            pass

        repo.add_tool_call(
            history_conn, assistant_msg["id"], tc.id, tc.name,
            tc.input, tc.result, duration_ms=tc.duration_ms,
            status=status, error_message=error_msg,
        )

        # Create artifact from tool result
        artifact = _build_artifact_from_tool(
            tc.name, tc.input, tc.result, tc.id,
            conversation_id, history_conn, chart_registry,
        )
        if artifact:
            artifacts.append(artifact)
            yield _sse_event("artifact", {
                "id": artifact["id"],
                "kind": artifact["kind"],
                "title": artifact.get("title"),
                "spec": artifact.get("spec", {}),
            })

    # Emit the response text
    if turn.response_text:
        yield _sse_event("text_delta", {"text": turn.response_text})

    yield _sse_event("done", {
        "conversation_id": conversation_id,
        "message_id": assistant_msg["id"],
    })

    # Generate title for new conversations (fire and forget)
    if is_first_exchange and turn.response_text:
        try:
            title = generate_title(client, request.message, turn.response_text[:500])
            repo.update_conversation(history_conn, conversation_id, title=title)
            yield _sse_event("title_updated", {
                "conversation_id": conversation_id,
                "title": title,
            })
        except Exception:
            logger.exception("Title generation failed")


@router.post("/api/v1/chat")
async def chat(
    request: ChatRequest,
    connections: Connections = Depends(get_connections),
    history_conn: sqlite3.Connection = Depends(get_history_conn),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """SSE endpoint for the two-phase agent loop."""
    return StreamingResponse(
        _stream_agent_turn(request, connections, history_conn, settings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
