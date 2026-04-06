"""Tool definitions (JSON schemas for the Anthropic tool-use API)."""

from __future__ import annotations

from explorer.canonical_charts import CanonicalChart

# Type mapping from registry YAML to JSON Schema
_TYPE_MAP = {
    "int": "integer",
    "float": "number",
    "string": "string",
    "bool": "boolean",
    "list[string]": "array",
}


def _build_generate_chart_tool(registry: dict[str, CanonicalChart] | None = None) -> dict:
    """Build the generate_chart tool schema dynamically from the registry.

    When the registry has entries, the schema includes a canonical mode
    with chart_name enum and per-chart parameter docs.  The adhoc mode
    is always available.
    """
    registry = registry or {}
    chart_names = list(registry.keys())

    # Build canonical chart descriptions for the tool description
    canonical_desc = ""
    if chart_names:
        lines = []
        for name, chart in registry.items():
            lines.append(f"  - {name}: {chart.description.strip()}")
        canonical_desc = (
            "\n\nCanonical charts (use mode='canonical'):\n"
            + "\n".join(lines)
        )

    # Build parameter schemas for each canonical chart
    canonical_params = {}
    for name, chart in registry.items():
        params_schema: dict = {"type": "object", "properties": {}, "required": []}
        for pname, pdef in chart.parameters.items():
            prop: dict = {"description": pdef.get("description", "")}
            ptype = pdef.get("type", "string")
            if ptype in _TYPE_MAP:
                prop["type"] = _TYPE_MAP[ptype]
                if ptype == "list[string]":
                    prop["items"] = {"type": "string"}
            else:
                prop["type"] = "string"
            if "enum" in pdef:
                prop["enum"] = pdef["enum"]
            if "default" in pdef:
                prop["default"] = pdef["default"]
            params_schema["properties"][pname] = prop
            if pdef.get("required"):
                params_schema["required"].append(pname)
        canonical_params[name] = params_schema

    tool: dict = {
        "name": "generate_chart",
        "description": (
            "Generate an interactive Plotly chart and save as HTML. "
            "Two modes: 'canonical' invokes a hand-crafted chart function by name, "
            "'adhoc' builds a generic chart from a data + type spec. "
            "All charts use the NYT-inspired quant-edge visual theme."
            + canonical_desc
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["canonical", "adhoc"],
                    "description": "Chart mode. 'canonical' for named charts, 'adhoc' for custom.",
                    "default": "adhoc",
                },
                "chart_name": {
                    "type": "string",
                    "description": "Name of the canonical chart to render (required if mode='canonical').",
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameters for the canonical chart function.",
                },
                "chart_type": {
                    "type": "string",
                    "enum": [
                        "scatter",
                        "bar_horizontal",
                        "distribution",
                        "heatmap",
                        "table",
                        "time_series",
                    ],
                    "description": "Type of adhoc chart to generate (required if mode='adhoc').",
                },
                "data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of data points for adhoc charts.",
                },
                "title": {
                    "type": "string",
                    "description": "Chart title — should state an insight, not just a label.",
                },
                "x_field": {
                    "type": "string",
                    "description": "Field name for x-axis (scatter, time_series).",
                },
                "y_field": {
                    "type": "string",
                    "description": "Field name for y-axis (scatter, time_series, bar value).",
                },
                "color_field": {
                    "type": "string",
                    "description": "Field name for color grouping (e.g. 'position').",
                },
                "label_field": {
                    "type": "string",
                    "description": "Field name for point/bar labels (e.g. 'player').",
                },
                "group_field": {
                    "type": "string",
                    "description": "Field for grouping (distribution, time_series).",
                },
                "subtitle": {
                    "type": "string",
                    "description": (
                        "Context line below title. Include season range, position filter, "
                        "and sample size (e.g. '2022–2025, WR target share vs YPRR, n=7 seasons')."
                    ),
                },
                "source": {
                    "type": "string",
                    "description": "Data attribution shown at bottom of chart (e.g. 'Source: nflverse, PFF').",
                },
                "color_mode": {
                    "type": "string",
                    "enum": ["default", "spotlight", "diverging", "categorical"],
                    "description": (
                        "Color mode. 'default'=all gray, 'spotlight'=gray background + blue highlight "
                        "(use with highlight_players), 'diverging'=blue positive / brick negative "
                        "(use for ADP divergence, value vs replacement), 'categorical'=up to 4 distinct colors "
                        "(use with color_field for position groups)."
                    ),
                    "default": "default",
                },
                "highlight_players": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Player names to highlight. Best used with color_mode='spotlight'.",
                },
                "reference_lines": {
                    "type": "array",
                    "description": (
                        "Reference lines for context (league average, thresholds, positional median). "
                        "Key thresholds: trust_weight=0.70, adp_divergence=±12, variance=8.0."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "axis": {
                                "type": "string",
                                "enum": ["x", "y"],
                                "description": "Which axis the line is on.",
                            },
                            "value": {
                                "type": "number",
                                "description": "Position of the reference line.",
                            },
                            "label": {
                                "type": "string",
                                "description": "Label for the reference line (e.g. 'WR median', 'league avg').",
                            },
                            "style": {
                                "type": "string",
                                "enum": ["solid", "dash", "dot"],
                                "default": "dash",
                            },
                        },
                        "required": ["axis", "value"],
                    },
                },
                "annotations": {
                    "type": "array",
                    "description": "Point annotations — short text labels pointing to specific data points.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number", "description": "X coordinate of the data point."},
                            "y": {"type": "number", "description": "Y coordinate of the data point."},
                            "text": {"type": "string", "description": "Short label text."},
                            "position": {
                                "type": "string",
                                "enum": ["above", "below", "left", "right", "auto"],
                                "default": "auto",
                            },
                        },
                        "required": ["x", "y", "text"],
                    },
                },
                "filename": {
                    "type": "string",
                    "description": "Output filename (without extension). Defaults to auto-generated.",
                },
            },
            "required": ["title"],
        },
    }

    # If registry has entries, add chart_name enum
    if chart_names:
        tool["input_schema"]["properties"]["chart_name"]["enum"] = chart_names

    return tool


def build_tools(registry: dict[str, CanonicalChart] | None = None) -> list[dict]:
    """Build the full tool list, with generate_chart reflecting the registry."""
    return [
        {
            "name": "query_sql",
            "description": (
                "Query the fantasy-data SQLite database. Write SELECT queries only. "
                "The database contains player identity, season baselines (90+ metrics), "
                "coaching staff, and WR reception perception data across 12 NFL seasons (2014–2025)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A SQL SELECT query to execute against the fantasy_data.db database.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this query is looking for (for audit trail).",
                    },
                },
                "required": ["sql", "description"],
            },
        },
        {
            "name": "search_knowledge_base",
            "description": (
                "Semantic search across expert fantasy football content in ChromaDB. "
                "Returns relevant text chunks with source attribution. "
                "Use filters to narrow by analyst, trust tier, season, source type, content tag, or date range."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query.",
                    },
                    "domain": {
                        "type": "string",
                        "description": "ChromaDB collection name.",
                        "default": "fantasy_football",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 5,
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional metadata filters. All fields are optional.",
                        "properties": {
                            "analyst": {
                                "type": "string",
                                "description": "Filter by analyst name (e.g. 'barrett', 'jj').",
                            },
                            "trust_tier": {
                                "type": "string",
                                "enum": ["core", "supplementary", "exploratory"],
                                "description": "Filter by trust tier.",
                            },
                            "season": {
                                "type": "integer",
                                "description": "Filter by season year.",
                            },
                            "source_type": {
                                "type": "string",
                                "description": "Filter by source type (youtube, web, pdf, html, article).",
                            },
                            "content_tag": {
                                "type": "string",
                                "description": "Filter by content tag (preview, evergreen, retrospective, draft_strategy).",
                            },
                            "date_from": {
                                "type": "string",
                                "description": "Published after this date (YYYY-MM-DD).",
                            },
                            "date_to": {
                                "type": "string",
                                "description": "Published before this date (YYYY-MM-DD).",
                            },
                        },
                    },
                },
                "required": ["query"],
            },
        },
        _build_generate_chart_tool(registry),
    ]


# Backwards compat: TOOLS is the static list (empty registry)
TOOLS = build_tools()
