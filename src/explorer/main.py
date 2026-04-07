"""Entry point — interactive conversation loop with Anthropic tool-use API."""

import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from explorer import cli_render
from explorer.agent import AgentConfig, run_agent_turn
from explorer.canonical_charts import load_registry
from explorer.connections import init_connections
from explorer.system_prompt import build_system_prompt
from explorer.tools import build_tools

CHARTS_DIR = Path(__file__).resolve().parent.parent.parent / "charts"
REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "chart_registry.yaml"


def main():
    load_dotenv()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        cli_render.print_error("ANTHROPIC_API_KEY not set in environment or .env")
        sys.exit(1)

    try:
        connections = init_connections()
    except (FileNotFoundError, ValueError) as e:
        cli_render.print_error(str(e))
        sys.exit(1)

    chart_registry = load_registry(REGISTRY_PATH) if REGISTRY_PATH.exists() else {}
    tools = build_tools(chart_registry)

    cli_render.print_banner(
        sqlite_stats=connections.sqlite_stats,
        chroma_stats=connections.chroma_stats,
    )

    system_prompt = build_system_prompt()
    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = []

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye.")
            break
        if user_input.lower() == "reset":
            messages.clear()
            cli_render.print_reset()
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            turn = run_agent_turn(
                client=client,
                system_prompt=system_prompt,
                messages=messages,
                connections=connections,
                tools=tools,
                chart_registry=chart_registry,
                charts_dir=CHARTS_DIR,
                on_plan=cli_render.print_plan,
                on_tool_start=_on_tool_start,
                on_tool_end=_on_tool_end,
            )
            _print_response(turn.response_text)
        except anthropic.APIError as e:
            cli_render.print_error(f"API error: {e}")
            messages.pop()


def _on_tool_start(tool_id: str, tool_name: str, tool_input: dict) -> None:
    """Display a compact tool call header."""
    description = tool_input.get(
        "description",
        tool_input.get("query", tool_input.get("title", "")),
    )
    cli_render.print_tool_call(tool_name, description)


def _on_tool_end(tool_id: str, tool_name: str, result_json: str, duration_ms: int) -> None:
    """Display a compact tool result summary."""
    try:
        result = json.loads(result_json)
    except (json.JSONDecodeError, TypeError):
        return

    if "error" in result:
        cli_render.print_error(result["error"])
        return

    if tool_name == "query_sql" and "rows" in result:
        cli_render.print_sql_result(result)
    elif tool_name == "search_knowledge_base" and "results" in result:
        cli_render.print_kb_result(result)
    elif tool_name == "generate_chart" and "path" in result:
        cli_render.print_chart_result(result)


def _print_response(text: str) -> None:
    """Render the final response as Rich Markdown."""
    if text:
        cli_render.print_response(text)


if __name__ == "__main__":
    main()
