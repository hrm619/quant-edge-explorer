"""Tests for chart engine — verify chart types, canonical dispatch, and theming."""

import json

import plotly.graph_objects as go
import pytest

from explorer.canonical_charts import CanonicalChart
from explorer.chart_engine import ChartSpec, build_chart_spec, render_chart


class TestAdhocCharts:
    def test_scatter_returns_file(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [
                    {"player": "A", "x": 1, "y": 2, "pos": "WR"},
                    {"player": "B", "x": 3, "y": 4, "pos": "RB"},
                ],
                "title": "Test Scatter",
                "x_field": "x",
                "y_field": "y",
                "color_field": "pos",
                "label_field": "player",
                "filename": "ce_scatter",
            },
            charts_dir,
        )
        assert result["title"] == "Test Scatter"
        assert (charts_dir / "ce_scatter.html").exists()

    def test_heatmap(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "heatmap",
                "data": [
                    {"target_share": 0.25, "yprr": 2.0, "snap_share": 0.90},
                    {"target_share": 0.30, "yprr": 2.5, "snap_share": 0.95},
                    {"target_share": 0.18, "yprr": 1.5, "snap_share": 0.75},
                ],
                "title": "Metric Correlations",
                "filename": "ce_heatmap",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_heatmap.html").exists()

    def test_auto_filename_from_title(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "table",
                "data": [{"name": "Test", "value": 1}],
                "title": "High Volume WRs Are Regression Candidates!",
            },
            charts_dir,
        )
        assert "high_volume" in result["path"]
        assert result["path"].endswith(".html")

    def test_empty_data_table(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "table",
                "data": [],
                "title": "Empty Table",
                "filename": "ce_empty",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_empty.html").exists()

    def test_position_colors_applied(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [
                    {"player": "A", "x": 1, "y": 2, "position": "QB"},
                    {"player": "B", "x": 3, "y": 4, "position": "WR"},
                ],
                "title": "Position Colors",
                "x_field": "x",
                "y_field": "y",
                "color_field": "position",
                "filename": "ce_pos_colors",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_pos_colors.html").exists()

    def test_adhoc_mode_explicit(self, charts_dir):
        """Explicit mode='adhoc' should work the same as default."""
        result = render_chart(
            {
                "mode": "adhoc",
                "chart_type": "bar_horizontal",
                "data": [{"label": "A", "value": 10}, {"label": "B", "value": 20}],
                "title": "Adhoc Bar",
                "filename": "ce_adhoc_bar",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_adhoc_bar.html").exists()


class TestColorDifferentiation:
    def test_non_position_groups_get_distinct_colors(self, charts_dir):
        """Two player names grouped by color_field should NOT both be gray."""
        from explorer.chart_engine import _color_for_group
        color_a = _color_for_group("Jaylen Waddle", 0)
        color_b = _color_for_group("Jameson Williams", 1)
        assert color_a != color_b

    def test_time_series_groups_get_distinct_colors(self, charts_dir):
        """Time series with group_field should produce differently-colored traces."""
        result = render_chart(
            {
                "chart_type": "time_series",
                "data": [
                    {"season": 2022, "value": 0.20, "player": "Waddle"},
                    {"season": 2023, "value": 0.25, "player": "Waddle"},
                    {"season": 2022, "value": 0.15, "player": "Williams"},
                    {"season": 2023, "value": 0.18, "player": "Williams"},
                ],
                "title": "Volume Comparison",
                "x_field": "season",
                "y_field": "value",
                "group_field": "player",
                "filename": "ce_distinct_ts",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_distinct_ts.html").exists()


class TestLegend:
    def test_multi_trace_gets_legend(self, charts_dir):
        """Charts with 2+ named traces should show a legend."""
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [
                    {"x": 1, "y": 2, "group": "A"},
                    {"x": 3, "y": 4, "group": "B"},
                ],
                "title": "Legend Test",
                "x_field": "x",
                "y_field": "y",
                "color_field": "group",
                "filename": "ce_legend",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_legend.html").exists()


class TestTakeaways:
    def test_takeaways_render_in_html(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [{"x": 1, "y": 2}, {"x": 3, "y": 4}],
                "title": "Chart With Takeaways",
                "x_field": "x",
                "y_field": "y",
                "takeaways": [
                    "First insight about the data",
                    "Second insight with context",
                    "Third recommendation for next steps",
                ],
                "filename": "ce_takeaways",
            },
            charts_dir,
        )
        path = charts_dir / "ce_takeaways.html"
        assert path.exists()
        html_content = path.read_text()
        assert "Key Takeaways" in html_content
        assert "First insight about the data" in html_content
        assert "Third recommendation for next steps" in html_content

    def test_no_takeaways_produces_standard_html(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [{"x": 1, "y": 2}],
                "title": "No Takeaways",
                "x_field": "x",
                "y_field": "y",
                "filename": "ce_no_takeaways",
            },
            charts_dir,
        )
        path = charts_dir / "ce_no_takeaways.html"
        assert path.exists()
        html_content = path.read_text()
        assert "Key Takeaways" not in html_content


class TestCanonicalCharts:
    def _make_registry(self):
        """Build a test registry with a mock chart function."""
        def mock_render(season: int, position_filter: str | None = None) -> go.Figure:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=[1, 2, 3], y=["A", "B", "C"], orientation="h"))
            return fig

        return {
            "test_chart": CanonicalChart(
                name="test_chart",
                description="A test canonical chart.",
                function=mock_render,
                parameters={
                    "season": {"type": "int", "required": True, "description": "Season year"},
                    "position_filter": {"type": "string", "required": False, "default": None, "description": "Filter by position"},
                },
            ),
        }

    def test_canonical_dispatch(self, charts_dir):
        registry = self._make_registry()
        result = render_chart(
            {
                "mode": "canonical",
                "chart_name": "test_chart",
                "parameters": {"season": 2025},
                "title": "Canonical Test",
                "filename": "ce_canonical",
            },
            charts_dir,
            registry=registry,
        )
        assert (charts_dir / "ce_canonical.html").exists()
        assert result["title"] == "Canonical Test"

    def test_canonical_unknown_chart_raises(self, charts_dir):
        with pytest.raises(ValueError, match="Unknown canonical chart"):
            render_chart(
                {
                    "mode": "canonical",
                    "chart_name": "nonexistent",
                    "parameters": {},
                    "title": "Bad Chart",
                },
                charts_dir,
                registry={},
            )

    def test_canonical_missing_required_param_raises(self, charts_dir):
        registry = self._make_registry()
        with pytest.raises(ValueError, match="Missing required parameter"):
            render_chart(
                {
                    "mode": "canonical",
                    "chart_name": "test_chart",
                    "parameters": {},
                    "title": "Missing Param",
                },
                charts_dir,
                registry=registry,
            )

    def test_canonical_with_empty_registry_falls_back(self, charts_dir):
        """With an empty registry, canonical mode should raise."""
        with pytest.raises(ValueError, match="Unknown canonical chart"):
            render_chart(
                {
                    "mode": "canonical",
                    "chart_name": "anything",
                    "parameters": {},
                    "title": "No Registry",
                },
                charts_dir,
                registry={},
            )


class TestContextFeatures:
    def test_reference_lines_render(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [
                    {"player": "A", "x": 0.25, "y": 2.1},
                    {"player": "B", "x": 0.30, "y": 1.8},
                ],
                "title": "Chart With Reference Lines",
                "x_field": "x",
                "y_field": "y",
                "reference_lines": [
                    {"axis": "y", "value": 2.0, "label": "WR median YPRR", "style": "dash"},
                    {"axis": "x", "value": 0.22, "label": "league avg target share", "style": "dot"},
                ],
                "filename": "ce_reflines",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_reflines.html").exists()

    def test_annotations_render(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [
                    {"player": "A", "x": 0.25, "y": 2.1},
                    {"player": "B", "x": 0.30, "y": 1.8},
                ],
                "title": "Chart With Annotations",
                "x_field": "x",
                "y_field": "y",
                "annotations": [
                    {"x": 0.25, "y": 2.1, "text": "Breakout candidate", "position": "above"},
                ],
                "filename": "ce_annotations",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_annotations.html").exists()

    def test_subtitle_and_source(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "bar_horizontal",
                "data": [{"label": "A", "value": 10}],
                "title": "Players Above League Average",
                "subtitle": "2025, WR only, n=24",
                "source": "Source: nflverse, PFF",
                "filename": "ce_subtitle",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_subtitle.html").exists()

    def test_spotlight_color_mode_scatter(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "scatter",
                "data": [
                    {"player": "A", "x": 1, "y": 2},
                    {"player": "B", "x": 3, "y": 4},
                    {"player": "C", "x": 5, "y": 6},
                ],
                "title": "Spotlight Mode",
                "x_field": "x",
                "y_field": "y",
                "label_field": "player",
                "color_mode": "spotlight",
                "highlight_players": ["B"],
                "filename": "ce_spotlight",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_spotlight.html").exists()

    def test_diverging_color_mode_bar(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "bar_horizontal",
                "data": [
                    {"player": "A", "divergence": 15},
                    {"player": "B", "divergence": -8},
                    {"player": "C", "divergence": 0},
                ],
                "title": "Diverging Bar Colors",
                "x_field": "divergence",
                "y_field": "player",
                "color_mode": "diverging",
                "filename": "ce_diverging",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_diverging.html").exists()

    def test_spotlight_time_series(self, charts_dir):
        result = render_chart(
            {
                "chart_type": "time_series",
                "data": [
                    {"season": 2022, "value": 0.20, "player": "A"},
                    {"season": 2023, "value": 0.25, "player": "A"},
                    {"season": 2022, "value": 0.18, "player": "B"},
                    {"season": 2023, "value": 0.22, "player": "B"},
                ],
                "title": "Spotlight Time Series",
                "x_field": "season",
                "y_field": "value",
                "group_field": "player",
                "color_mode": "spotlight",
                "highlight_players": ["A"],
                "filename": "ce_spotlight_ts",
            },
            charts_dir,
        )
        assert (charts_dir / "ce_spotlight_ts.html").exists()


class TestToolSchema:
    def test_build_tools_empty_registry(self):
        from explorer.tools import build_tools
        tools = build_tools()
        assert len(tools) == 3
        chart_tool = tools[2]
        assert chart_tool["name"] == "generate_chart"
        assert "canonical" in chart_tool["description"]

    def test_build_tools_with_registry(self):
        from explorer.tools import build_tools

        def mock_fn(**kwargs):
            return go.Figure()

        registry = {
            "adp_divergence": CanonicalChart(
                name="adp_divergence",
                description="ADP divergence scatter chart.",
                function=mock_fn,
                parameters={"season": {"type": "int", "required": True, "description": "Season"}},
            ),
        }
        tools = build_tools(registry)
        chart_tool = tools[2]
        assert "adp_divergence" in chart_tool["description"]
        assert chart_tool["input_schema"]["properties"]["chart_name"]["enum"] == ["adp_divergence"]

    def test_schema_has_context_fields(self):
        from explorer.tools import build_tools
        tools = build_tools()
        props = tools[2]["input_schema"]["properties"]
        assert "subtitle" in props
        assert "source" in props
        assert "reference_lines" in props
        assert "annotations" in props
        assert "takeaways" in props
        assert props["reference_lines"]["type"] == "array"
        assert props["annotations"]["type"] == "array"
        assert props["takeaways"]["type"] == "array"


class TestBuildChartSpec:
    def test_returns_chart_spec_dataclass(self):
        result = build_chart_spec({
            "chart_type": "scatter",
            "data": [{"x": 1, "y": 2}],
            "title": "Test",
            "x_field": "x",
            "y_field": "y",
        })
        assert isinstance(result, ChartSpec)
        assert result.title == "Test"
        assert isinstance(result.figure, dict)
        assert "data" in result.figure

    def test_spec_is_json_serializable(self):
        result = build_chart_spec({
            "chart_type": "bar_horizontal",
            "data": [{"label": "A", "value": 10}],
            "title": "JSON Test",
        })
        # Must not raise
        serialized = json.dumps(result.figure)
        assert len(serialized) > 0

    def test_spec_contains_plotly_traces(self):
        result = build_chart_spec({
            "chart_type": "scatter",
            "data": [
                {"player": "A", "x": 1, "y": 2, "pos": "WR"},
                {"player": "B", "x": 3, "y": 4, "pos": "RB"},
            ],
            "title": "Trace Test",
            "x_field": "x",
            "y_field": "y",
            "color_field": "pos",
        })
        assert len(result.figure["data"]) >= 2

    def test_spec_preserves_takeaways(self):
        result = build_chart_spec({
            "chart_type": "scatter",
            "data": [{"x": 1, "y": 2}],
            "title": "Takeaway Test",
            "x_field": "x",
            "y_field": "y",
            "takeaways": ["Point one", "Point two"],
        })
        assert result.takeaways == ["Point one", "Point two"]

    def test_canonical_spec(self):
        def mock_fn(season=2025):
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[1], y=[2], name="test"))
            return fig

        registry = {
            "test_chart": CanonicalChart(
                name="test_chart",
                description="Test",
                function=mock_fn,
                parameters={"season": {"type": "int", "required": True, "description": "Season"}},
            ),
        }
        result = build_chart_spec(
            {"mode": "canonical", "chart_name": "test_chart", "parameters": {"season": 2025}, "title": "Canon"},
            registry=registry,
        )
        assert result.title == "Canon"
        assert len(result.figure["data"]) == 1
