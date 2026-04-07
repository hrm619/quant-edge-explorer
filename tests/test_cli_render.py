"""Tests for CLI rendering — verify Rich output doesn't crash on real data shapes."""

import re
from io import StringIO

from rich.console import Console

from explorer import cli_render

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _capture(fn, *args, **kwargs) -> str:
    """Run a render function with captured output and return plain text (ANSI stripped)."""
    buf = StringIO()
    original = cli_render.console
    cli_render.console = Console(file=buf, force_terminal=True, width=100)
    try:
        fn(*args, **kwargs)
    finally:
        cli_render.console = original
    return _ANSI_RE.sub("", buf.getvalue())


class TestBanner:
    def test_renders_with_stats(self):
        output = _capture(
            cli_render.print_banner,
            sqlite_stats="SQLite: 2,248 players | 8,536 baselines",
            chroma_stats="ChromaDB: fantasy_football — 14,297 chunks",
        )
        assert "Quant-Edge" in output
        assert "2,248" in output
        assert "14,297" in output

    def test_renders_without_stats(self):
        output = _capture(cli_render.print_banner)
        assert "Quant-Edge" in output


class TestPlan:
    def test_renders_plan_text(self):
        plan = "**Thesis:** Adams is a sell.\n\n**Key Questions:**\n1. Volume trend\n2. Trust weight"
        output = _capture(cli_render.print_plan, plan)
        assert "Research Plan" in output
        assert "Adams" in output


class TestToolCall:
    def test_renders_tool_name(self):
        output = _capture(cli_render.print_tool_call, "query_sql", "Top WRs by target share")
        assert "query_sql" in output
        assert "Top WRs" in output


class TestSqlResult:
    def test_renders_table(self):
        result = {
            "columns": ["full_name", "team", "target_share"],
            "rows": [
                {"full_name": "Ja'Marr Chase", "team": "CIN", "target_share": 0.283},
                {"full_name": "CeeDee Lamb", "team": "DAL", "target_share": 0.271},
            ],
            "row_count": 2,
        }
        output = _capture(cli_render.print_sql_result, result)
        assert "Chase" in output
        assert "Player" in output  # full_name → "Player" abbreviation
        assert "2 rows" in output

    def test_abbreviates_column_names(self):
        result = {
            "columns": ["full_name", "yards_per_route_run", "data_trust_weight"],
            "rows": [{"full_name": "Test", "yards_per_route_run": 2.1, "data_trust_weight": 0.75}],
            "row_count": 1,
        }
        output = _capture(cli_render.print_sql_result, result)
        assert "YPRR" in output
        assert "Trust Wt" in output

    def test_caps_columns_when_too_many(self):
        cols = [f"col_{i}" for i in range(12)]
        rows = [{c: i for i, c in enumerate(cols)}]
        result = {"columns": cols, "rows": rows, "row_count": 1}
        output = _capture(cli_render.print_sql_result, result)
        assert "6 of 12 columns" in output

    def test_truncates_large_result(self):
        rows = [{"name": f"Player {i}", "value": i} for i in range(20)]
        result = {"columns": ["name", "value"], "rows": rows, "row_count": 20}
        output = _capture(cli_render.print_sql_result, result)
        assert "showing first 8" in output

    def test_handles_empty_rows(self):
        result = {"columns": ["name"], "rows": [], "row_count": 0}
        output = _capture(cli_render.print_sql_result, result)
        assert "No rows" in output

    def test_handles_none_values(self):
        result = {
            "columns": ["name", "score"],
            "rows": [{"name": "Test", "score": None}],
            "row_count": 1,
        }
        output = _capture(cli_render.print_sql_result, result)
        assert "Test" in output


class TestKbResult:
    def test_renders_excerpts(self):
        result = {
            "results": [
                {
                    "text": "Adams is in a tough spot with the Jets.",
                    "distance": 0.12,
                    "analyst": "barrett",
                    "title": "Jets Preview",
                    "source_type": "youtube",
                    "trust_tier": "core",
                    "published_at": "2025-03-15",
                    "content_tag": "preview",
                },
            ],
            "result_count": 1,
            "query": "Adams Jets",
            "domain": "fantasy_football",
        }
        output = _capture(cli_render.print_kb_result, result)
        assert "barrett" in output
        assert "Adams" in output
        assert "1 result" in output

    def test_handles_empty_results(self):
        result = {"results": [], "result_count": 0, "query": "nothing", "domain": "test"}
        output = _capture(cli_render.print_kb_result, result)
        assert "No knowledge base" in output


class TestChartResult:
    def test_renders_path(self):
        result = {"path": "charts/test_chart.html", "title": "Test Chart"}
        output = _capture(cli_render.print_chart_result, result)
        assert "charts/test_chart.html" in output


class TestResponse:
    def test_renders_markdown(self):
        text = "**Adams is a sell at WR15.**\n\n- YPRR: 1.98\n- Trust weight: 0.40\n\n> Prior confirmed."
        output = _capture(cli_render.print_response, text)
        assert "Adams" in output

    def test_renders_plain_text(self):
        output = _capture(cli_render.print_response, "Simple answer.")
        assert "Simple answer" in output


class TestError:
    def test_renders_error(self):
        output = _capture(cli_render.print_error, "Something went wrong")
        assert "Something went wrong" in output
