"""Rich CLI rendering for the explorer agent."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# Trust tier colors
_TIER_STYLE = {
    "core": "bold blue",
    "supplementary": "bold yellow",
    "exploratory": "dim",
}

MAX_TABLE_ROWS = 8
MAX_KB_TEXT_LEN = 150


def print_banner(sqlite_stats: str = "", chroma_stats: str = "") -> None:
    """Startup banner with database stats."""
    lines = []
    if sqlite_stats:
        lines.append(f"  {sqlite_stats}")
    if chroma_stats:
        lines.append(f"  {chroma_stats}")
    lines.append("")
    lines.append("  [dim]Type 'quit' to exit, 'reset' to clear history[/dim]")

    content = "\n".join(lines)
    panel = Panel(
        content,
        title="[bold]Quant-Edge Research Agent[/bold]",
        border_style="dim",
        padding=(1, 2),
    )
    console.print(panel)


def print_plan(plan_text: str) -> None:
    """Research plan in a bordered panel."""
    md = Markdown(plan_text)
    panel = Panel(
        md,
        title="[bold blue]Research Plan[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def print_tool_call(tool_name: str, description: str) -> None:
    """Styled tool call log line."""
    console.print(
        f"  [blue]●[/blue] [bold]{tool_name}[/bold]  [dim]{description}[/dim]"
    )


def print_sql_result(result: dict) -> None:
    """Compact Rich table from SQL query result."""
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    row_count = result.get("row_count", len(rows))

    if not rows or not columns:
        console.print("  [dim]No rows returned[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        padding=(0, 1),
        pad_edge=True,
    )

    # Detect numeric columns from first row
    numeric_cols = set()
    for col in columns:
        val = rows[0].get(col)
        if isinstance(val, (int, float)):
            numeric_cols.add(col)

    for col in columns:
        justify = "right" if col in numeric_cols else "left"
        table.add_column(
            col.replace("_", " ").title(),
            justify=justify,
            no_wrap=True,
        )

    display_rows = rows[:MAX_TABLE_ROWS]
    for row in display_rows:
        cells = []
        for col in columns:
            val = row.get(col)
            if val is None:
                cells.append("[dim]—[/dim]")
            elif isinstance(val, float):
                cells.append(f"{val:.2f}")
            else:
                cells.append(str(val))
        table.add_row(*cells)

    console.print()
    console.print(table)

    footer_parts = [f"{row_count} row{'s' if row_count != 1 else ''}"]
    if row_count > MAX_TABLE_ROWS:
        footer_parts.append(f"showing first {MAX_TABLE_ROWS}")
    if result.get("warning"):
        footer_parts.append(result["warning"])
    console.print(f"  [dim]{'  ·  '.join(footer_parts)}[/dim]")


def print_kb_result(result: dict) -> None:
    """KB search excerpts with analyst styling."""
    results = result.get("results", [])
    query = result.get("query", "")

    if not results:
        console.print("  [dim]No knowledge base results[/dim]")
        return

    console.print()
    for r in results:
        analyst = r.get("analyst", "unknown")
        tier = r.get("trust_tier", "")
        date = r.get("published_at", "")
        source_type = r.get("source_type", "")
        text = r.get("text", "")

        # Truncate text
        if len(text) > MAX_KB_TEXT_LEN:
            text = text[:MAX_KB_TEXT_LEN].rsplit(" ", 1)[0] + "..."

        style = _TIER_STYLE.get(tier, "")
        meta_parts = [f"[{style}]{analyst}[/{style}]" if style else analyst]
        if tier:
            meta_parts[0] += f" ({tier})"
        if date:
            meta_parts.append(f"[dim]{date}[/dim]")
        if source_type:
            meta_parts.append(f"[dim]{source_type}[/dim]")

        console.print(f"  [dim]┃[/dim] {' · '.join(meta_parts)}")
        # Indent and dim the text
        for line in _wrap_text(text, 70):
            console.print(f"  [dim]┃[/dim] [italic]{line}[/italic]")
        console.print(f"  [dim]┃[/dim]")

    console.print(f"  [dim]{len(results)} results · query: \"{query}\"[/dim]")


def print_chart_result(result: dict) -> None:
    """Chart save confirmation with file path."""
    path = result.get("path", "")
    title = result.get("title", "")
    console.print(f"\n  [blue]📊[/blue] Chart saved → [link=file://{path}][blue underline]{path}[/blue underline][/link]")


def print_response(text: str) -> None:
    """Render model response as Rich Markdown."""
    console.print()
    console.rule(style="dim")
    console.print()
    md = Markdown(text)
    console.print(md)
    console.print()
    console.rule(style="dim")
    console.print()


def print_error(message: str) -> None:
    """Red-styled error message."""
    console.print(f"  [red bold]Error:[/red bold] [red]{message}[/red]")


def print_reset() -> None:
    """Conversation reset confirmation."""
    console.print("  [dim]Conversation history cleared.[/dim]\n")


def _wrap_text(text: str, width: int) -> list[str]:
    """Simple word-wrap for KB text display."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines or [""]
