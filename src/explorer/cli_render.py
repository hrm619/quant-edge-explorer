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
MAX_TABLE_COLS = 6
MAX_KB_TEXT_LEN = 150
RESPONSE_WIDTH = 100

# Column name abbreviations for fantasy-data fields
_COLUMN_ABBREV = {
    "full_name": "Player",
    "player": "Player",
    "position": "Pos",
    "team": "Team",
    "season": "Season",
    "adp_positional_rank": "ADP Rank",
    "adp_consensus": "ADP",
    "sharp_consensus_rank": "Sharp Rank",
    "sharp_pos_rank": "Sharp Pos",
    "data_trust_weight": "Trust Wt",
    "target_share": "Tgt Share",
    "snap_share": "Snap %",
    "air_yards_share": "AY Share",
    "yards_per_route_run": "YPRR",
    "catch_rate_over_expected": "CROE",
    "yards_per_carry": "YPC",
    "expected_yards_per_carry": "xYPC",
    "rush_yards_over_expected": "RYOE",
    "total_touches_per_game": "Touches/G",
    "carries_per_game": "Carries/G",
    "fpts_per_game_ppr": "FPTS/G",
    "fpts_per_game_std": "FPTS/G Std",
    "fantasy_pts_ppr": "FPTS PPR",
    "fantasy_pts_std": "FPTS Std",
    "pff_receiving_grade": "PFF Recv",
    "pff_offense_grade": "PFF Off",
    "pff_rush_grade": "PFF Rush",
    "pff_passing_grade": "PFF Pass",
    "hc_continuity": "HC Cont",
    "oc_continuity": "OC Cont",
    "seasons_in_system": "Sys Years",
    "adp_divergence_pos": "ADP Div",
    "adp_divergence_rank": "Div Rank",
    "adp_divergence_flag": "Div Flag",
    "projection_uncertain_flag": "Uncertain",
    "rz_target_share": "RZ Tgt %",
    "wopr": "WOPR",
    "consistency_score": "Consistency",
    "boom_rate": "Boom %",
    "bust_rate": "Bust %",
    "td_rate": "TD Rate",
    "racr": "RACR",
    "route_participation_rate": "Route Part",
    "avg_depth_of_target": "aDOT",
    "avg_separation": "Separation",
    "avg_cushion": "Cushion",
    "broken_tackle_rate": "Broken Tkl",
    "drop_rate": "Drop %",
    "rb_role": "RB Role",
    "baseline_id": "ID",
    "player_id": "Player ID",
}


def _col_label(col: str) -> str:
    """Get display label for a column name."""
    return _COLUMN_ABBREV.get(col, col.replace("_", " ").title())


def _select_columns(columns: list[str], max_cols: int = MAX_TABLE_COLS) -> list[str]:
    """Select the most useful columns when there are too many.

    Always keeps the first column (player name) and prioritizes
    columns with short abbreviated names.
    """
    if len(columns) <= max_cols:
        return columns

    # Always keep first column
    selected = [columns[0]]
    remaining = columns[1:]

    # Score remaining by abbreviated name length (shorter = more likely useful)
    # and prefer columns that appear in _COLUMN_ABBREV (domain-relevant)
    scored = []
    for col in remaining:
        abbrev = _COLUMN_ABBREV.get(col)
        if abbrev:
            score = 0  # known columns get priority
        else:
            score = 1  # unknown columns ranked lower
        scored.append((score, col))

    scored.sort(key=lambda x: x[0])
    selected.extend(col for _, col in scored[: max_cols - 1])

    # Preserve original column order
    return [c for c in columns if c in selected]


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
    total_cols = len(columns)

    if not rows or not columns:
        console.print("  [dim]No rows returned[/dim]")
        return

    # Select columns to display
    visible_cols = _select_columns(columns)

    # Detect numeric columns from first row
    numeric_cols = set()
    for col in visible_cols:
        val = rows[0].get(col)
        if isinstance(val, (int, float)):
            numeric_cols.add(col)

    table = Table(
        show_header=True,
        header_style="bold",
        border_style="dim",
        padding=(0, 1),
        pad_edge=True,
    )

    for col in visible_cols:
        justify = "right" if col in numeric_cols else "left"
        table.add_column(
            _col_label(col),
            justify=justify,
            min_width=6,
            overflow="fold",
        )

    display_rows = rows[:MAX_TABLE_ROWS]
    for row in display_rows:
        cells = []
        for col in visible_cols:
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
    if total_cols > len(visible_cols):
        footer_parts.append(f"{len(visible_cols)} of {total_cols} columns")
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
        for line in _wrap_text(text, 70):
            console.print(f"  [dim]┃[/dim] [italic]{line}[/italic]")
        console.print(f"  [dim]┃[/dim]")

    console.print(f"  [dim]{len(results)} results · query: \"{query}\"[/dim]")


def print_chart_result(result: dict) -> None:
    """Chart save confirmation with file path."""
    path = result.get("path", "")
    console.print(
        f"\n  [blue]📊[/blue] Chart saved → "
        f"[link=file://{path}][blue underline]{path}[/blue underline][/link]"
    )


def print_response(text: str) -> None:
    """Render model response as Rich Markdown in a padded panel."""
    console.print()
    console.rule(style="dim")
    console.print()

    width = min(console.width, RESPONSE_WIDTH)
    md = Markdown(text)
    panel = Panel(
        md,
        border_style="dim",
        padding=(1, 3),
        width=width,
    )
    console.print(panel)

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
