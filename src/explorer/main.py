"""Entry point — interactive conversation loop with Anthropic tool-use API."""

import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from explorer.canonical_charts import load_registry
from explorer.connections import init_connections
from explorer.system_prompt import build_system_prompt
from explorer.tool_handlers import dispatch_tool
from explorer.tools import build_tools

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
CHARTS_DIR = Path(__file__).resolve().parent.parent.parent / "charts"
REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "chart_registry.yaml"


def main():
    load_dotenv()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in environment or .env")
        sys.exit(1)

    print("\n\U0001f50d Quant-Edge Research Agent")
    print("   Initializing connections...")

    try:
        connections = init_connections()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        sys.exit(1)

    chart_registry = load_registry(REGISTRY_PATH) if REGISTRY_PATH.exists() else {}
    tools = build_tools(chart_registry)

    system_prompt = build_system_prompt()
    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = []

    print("   Type 'quit' to exit, 'reset' to clear history\n")

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
            print("Conversation history cleared.\n")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = _run_agent_loop(
                client=client,
                system_prompt=system_prompt,
                messages=messages,
                connections=connections,
                tools=tools,
                chart_registry=chart_registry,
            )
            _print_response(response)
        except anthropic.APIError as e:
            print(f"\nAPI error: {e}\n")
            messages.pop()


def _run_agent_loop(
    client: anthropic.Anthropic,
    system_prompt: str,
    messages: list[dict],
    connections,
    tools: list[dict],
    chart_registry: dict | None = None,
) -> anthropic.types.Message:
    """Run the tool-use loop until the model produces a final text response."""
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        # Check if response contains any tool use
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Final response — add to history and return
            messages.append({"role": "assistant", "content": response.content})
            return response

        # Process tool calls
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_use_blocks:
            print(f"   \U0001f527 {block.name}: {block.input.get('description', block.input.get('query', block.input.get('title', '')))}")

            result = dispatch_tool(
                tool_name=block.name,
                tool_input=block.input,
                connections=connections,
                charts_dir=CHARTS_DIR,
                chart_registry=chart_registry,
            )

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})


def _print_response(response: anthropic.types.Message) -> None:
    """Print text blocks from the response."""
    for block in response.content:
        if hasattr(block, "text"):
            print(f"\n{block.text}\n")


if __name__ == "__main__":
    main()
