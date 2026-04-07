"""Reusable two-phase agent loop — plan first, then execute with tools.

This module extracts the core agent logic from main.py so that both
the CLI and the server can import and drive it with different rendering
backends (Rich for CLI, SSE events for the web app).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from explorer.connections import Connections
from explorer.system_prompt import build_planning_prompt
from explorer.tool_handlers import dispatch_tool


@dataclass
class AgentConfig:
    """Tuning knobs for the agent loop."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    planning_max_tokens: int = 1024


@dataclass
class ToolCallRecord:
    """One tool invocation and its result."""

    id: str
    name: str
    input: dict
    result: str  # JSON string from dispatch_tool
    duration_ms: int = 0


@dataclass
class AgentTurn:
    """Result of one complete user-to-response cycle."""

    plan_text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    response_text: str = ""
    raw_response: anthropic.types.Message | None = None


def run_agent_turn(
    client: anthropic.Anthropic,
    system_prompt: str,
    messages: list[dict],
    connections: Connections,
    tools: list[dict],
    config: AgentConfig | None = None,
    chart_registry: dict | None = None,
    charts_dir: Path | None = None,
    on_plan: Callable[[str], None] | None = None,
    on_tool_start: Callable[[str, str, dict], None] | None = None,
    on_tool_end: Callable[[str, str, str, int], None] | None = None,
) -> AgentTurn:
    """Run the two-phase agent loop: plan (no tools) then execute (with tools).

    Callbacks:
        on_plan(plan_text) — called after the planning phase completes.
        on_tool_start(tool_id, tool_name, tool_input) — called before each tool executes.
        on_tool_end(tool_id, tool_name, result_json, duration_ms) — called after each tool.

    The *messages* list is mutated in place (appended to) so the caller
    retains the full conversation history.
    """
    cfg = config or AgentConfig()
    turn = AgentTurn(plan_text="")

    # --- Phase 1: Planning (no tools — forces structured reasoning) ---
    planning_prompt = build_planning_prompt(system_prompt)

    plan_response = client.messages.create(
        model=cfg.model,
        max_tokens=cfg.planning_max_tokens,
        system=planning_prompt,
        messages=messages,
    )

    plan_text = ""
    for block in plan_response.content:
        if hasattr(block, "text"):
            plan_text += block.text

    turn.plan_text = plan_text

    if on_plan:
        on_plan(plan_text)

    messages.append({"role": "assistant", "content": plan_response.content})
    messages.append({
        "role": "user",
        "content": "Proceed with the research plan. Execute your queries and analysis now.",
    })

    # --- Phase 2: Execution (with tools) ---
    while True:
        response = client.messages.create(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            messages.append({"role": "assistant", "content": response.content})
            turn.raw_response = response
            turn.response_text = "".join(
                b.text for b in response.content if hasattr(b, "text")
            )
            return turn

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_use_blocks:
            if on_tool_start:
                on_tool_start(block.id, block.name, block.input)

            t0 = time.monotonic()
            result = dispatch_tool(
                tool_name=block.name,
                tool_input=block.input,
                connections=connections,
                charts_dir=charts_dir or Path("charts"),
                chart_registry=chart_registry,
            )
            duration_ms = int((time.monotonic() - t0) * 1000)

            record = ToolCallRecord(
                id=block.id,
                name=block.name,
                input=block.input,
                result=result,
                duration_ms=duration_ms,
            )
            turn.tool_calls.append(record)

            if on_tool_end:
                on_tool_end(block.id, block.name, result, duration_ms)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})
