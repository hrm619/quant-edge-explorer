"""Tests for tool handlers — SQL, KB search, chart generation."""

import json

from explorer.tool_handlers import (
    handle_generate_chart,
    handle_query_sql,
    handle_search_knowledge_base,
)


class TestQuerySql:
    def test_select_returns_rows(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="SELECT full_name, position FROM players ORDER BY full_name",
            description="List all players",
            connections=mock_connections,
        ))
        assert "error" not in result
        assert result["row_count"] == 3
        assert result["columns"] == ["full_name", "position"]
        names = [r["full_name"] for r in result["rows"]]
        assert "Davante Adams" in names

    def test_join_query(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="""
                SELECT p.full_name, b.target_share, b.data_trust_weight
                FROM players p
                JOIN player_season_baseline b ON p.player_id = b.player_id
                WHERE b.season = 2025 AND p.position = 'WR'
                ORDER BY b.target_share DESC
            """,
            description="WRs by target share in 2025",
            connections=mock_connections,
        ))
        assert "error" not in result
        assert result["row_count"] == 2
        assert result["rows"][0]["full_name"] == "Tyreek Hill"

    def test_rejects_insert(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="INSERT INTO players VALUES ('test', 'Test', 'QB', NULL, NULL, NULL, NULL, NULL, 0, 0, 0, 1)",
            description="Attempt insert",
            connections=mock_connections,
        ))
        assert "error" in result
        assert "SELECT" in result["error"]

    def test_rejects_delete(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="DELETE FROM players WHERE player_id = 'AdamDa01'",
            description="Attempt delete",
            connections=mock_connections,
        ))
        assert "error" in result

    def test_rejects_drop(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="DROP TABLE players",
            description="Attempt drop",
            connections=mock_connections,
        ))
        assert "error" in result

    def test_rejects_update(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="UPDATE players SET full_name = 'Hacked' WHERE player_id = 'AdamDa01'",
            description="Attempt update",
            connections=mock_connections,
        ))
        assert "error" in result

    def test_rejects_pragma(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="PRAGMA table_info(players)",
            description="Attempt pragma",
            connections=mock_connections,
        ))
        assert "error" in result

    def test_invalid_sql_returns_error(self, mock_connections):
        result = json.loads(handle_query_sql(
            sql="SELECT * FROM nonexistent_table",
            description="Bad table",
            connections=mock_connections,
        ))
        assert "error" in result

    def test_row_limit_truncation(self, mock_connections):
        # Our test data has only 3 rows, so no truncation — just verify no warning
        result = json.loads(handle_query_sql(
            sql="SELECT * FROM players",
            description="All players",
            connections=mock_connections,
        ))
        assert "warning" not in result
        assert result["row_count"] == 3


class TestSearchKnowledgeBase:
    def test_returns_results(self, mock_connections):
        result = json.loads(handle_search_knowledge_base(
            query="Davante Adams Jets",
            domain="fantasy_football",
            top_k=3,
            filters={},
            connections=mock_connections,
        ))
        assert "error" not in result
        assert result["result_count"] > 0
        assert "text" in result["results"][0]
        assert "distance" in result["results"][0]
        assert "analyst" in result["results"][0]

    def test_with_analyst_filter(self, mock_connections):
        result = json.loads(handle_search_knowledge_base(
            query="elite wide receiver",
            domain="fantasy_football",
            top_k=5,
            filters={"analyst": "barrett"},
            connections=mock_connections,
        ))
        assert "error" not in result
        for r in result["results"]:
            assert r["analyst"] == "barrett"

    def test_with_season_filter(self, mock_connections):
        result = json.loads(handle_search_knowledge_base(
            query="injury concern",
            domain="fantasy_football",
            top_k=5,
            filters={"season": 2025},
            connections=mock_connections,
        ))
        assert "error" not in result
        assert result["result_count"] > 0


class TestGenerateChart:
    def test_scatter_chart(self, charts_dir):
        spec = {
            "chart_type": "scatter",
            "data": [
                {"player": "Adams", "target_share": 0.28, "yprr": 2.1, "position": "WR"},
                {"player": "Hill", "target_share": 0.30, "yprr": 2.5, "position": "WR"},
            ],
            "title": "Target Share vs YPRR for WRs",
            "x_field": "target_share",
            "y_field": "yprr",
            "color_field": "position",
            "label_field": "player",
            "filename": "test_scatter",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" not in result
        assert result["path"].endswith(".html")
        assert (charts_dir / "test_scatter.html").exists()

    def test_bar_horizontal_chart(self, charts_dir):
        spec = {
            "chart_type": "bar_horizontal",
            "data": [
                {"player": "Adams", "value": 9, "position": "WR"},
                {"player": "Hill", "value": -2, "position": "WR"},
            ],
            "title": "ADP Divergence",
            "x_field": "value",
            "label_field": "player",
            "filename": "test_bar",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" not in result
        assert (charts_dir / "test_bar.html").exists()

    def test_distribution_chart(self, charts_dir):
        spec = {
            "chart_type": "distribution",
            "data": [
                {"position": "WR", "target_share": 0.20},
                {"position": "WR", "target_share": 0.25},
                {"position": "WR", "target_share": 0.30},
                {"position": "RB", "target_share": 0.08},
                {"position": "RB", "target_share": 0.12},
            ],
            "title": "Target Share Distribution by Position",
            "x_field": "target_share",
            "group_field": "position",
            "filename": "test_dist",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" not in result
        assert (charts_dir / "test_dist.html").exists()

    def test_time_series_chart(self, charts_dir):
        spec = {
            "chart_type": "time_series",
            "data": [
                {"season": 2023, "yprr": 2.0, "player": "Adams"},
                {"season": 2024, "yprr": 2.1, "player": "Adams"},
                {"season": 2023, "yprr": 2.4, "player": "Hill"},
                {"season": 2024, "yprr": 2.5, "player": "Hill"},
            ],
            "title": "YPRR Trend",
            "x_field": "season",
            "y_field": "yprr",
            "group_field": "player",
            "filename": "test_ts",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" not in result
        assert (charts_dir / "test_ts.html").exists()

    def test_table_chart(self, charts_dir):
        spec = {
            "chart_type": "table",
            "data": [
                {"player": "Adams", "target_share": 0.28, "trust": 0.40},
                {"player": "Hill", "target_share": 0.30, "trust": 1.00},
            ],
            "title": "Player Summary",
            "filename": "test_table",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" not in result
        assert (charts_dir / "test_table.html").exists()

    def test_highlight_players(self, charts_dir):
        spec = {
            "chart_type": "scatter",
            "data": [
                {"player": "Adams", "x": 0.28, "y": 2.1},
                {"player": "Hill", "x": 0.30, "y": 2.5},
                {"player": "McCaffrey", "x": 0.12, "y": 1.4},
            ],
            "title": "Test Highlight",
            "x_field": "x",
            "y_field": "y",
            "label_field": "player",
            "highlight_players": ["Adams"],
            "filename": "test_highlight",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" not in result

    def test_unknown_chart_type(self, charts_dir):
        spec = {
            "chart_type": "pie",
            "data": [{"a": 1}],
            "title": "Bad Chart",
        }
        result = json.loads(handle_generate_chart(spec, charts_dir))
        assert "error" in result
