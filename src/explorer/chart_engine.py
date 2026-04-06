"""Chart generation — canonical dispatch + adhoc rendering with NYT theme."""

from __future__ import annotations

import re
from pathlib import Path

import plotly.graph_objects as go

from fantasy_data.viz.theme import (
    COLORS,
    apply_theme,
    annotate_point,
    color_for_mode,
    format_axis,
)
from explorer.canonical_charts import CanonicalChart


def render_chart(
    spec: dict,
    charts_dir: Path,
    registry: dict[str, CanonicalChart] | None = None,
) -> dict:
    """Render a chart from a structured spec and save as HTML.

    If ``mode`` is ``"canonical"`` and the chart is in the registry, the
    registered function is called directly.  Otherwise falls back to
    adhoc chart building.

    Returns dict with 'path' and 'title'.
    """
    mode = spec.get("mode", "adhoc")

    if mode == "canonical":
        return _render_canonical(spec, charts_dir, registry or {})
    return _render_adhoc(spec, charts_dir)


# ---------------------------------------------------------------------------
# Canonical dispatch
# ---------------------------------------------------------------------------


def _render_canonical(
    spec: dict, charts_dir: Path, registry: dict[str, CanonicalChart]
) -> dict:
    chart_name = spec.get("chart_name")
    if not chart_name or chart_name not in registry:
        available = ", ".join(registry.keys()) or "(none)"
        raise ValueError(
            f"Unknown canonical chart: {chart_name!r}. Available: {available}"
        )

    chart = registry[chart_name]
    params = spec.get("parameters", {})

    # Validate required parameters
    for pname, pdef in chart.parameters.items():
        if pdef.get("required") and pname not in params:
            raise ValueError(f"Missing required parameter '{pname}' for chart '{chart_name}'")

    # Fill defaults
    call_params = {}
    for pname, pdef in chart.parameters.items():
        if pname in params:
            call_params[pname] = params[pname]
        elif "default" in pdef:
            call_params[pname] = pdef["default"]

    fig = chart.function(**call_params)
    title = spec.get("title", chart_name.replace("_", " ").title())

    filename = spec.get("filename") or _slugify(title)
    path = charts_dir / f"{filename}.html"
    fig.write_html(str(path), include_plotlyjs="cdn")

    return {"path": str(path), "title": title}


# ---------------------------------------------------------------------------
# Adhoc chart building (themed)
# ---------------------------------------------------------------------------


def _render_adhoc(spec: dict, charts_dir: Path) -> dict:
    chart_type = spec["chart_type"]
    data = spec["data"]
    title = spec["title"]
    subtitle = spec.get("subtitle")
    source = spec.get("source")

    builders = {
        "scatter": _build_scatter,
        "bar_horizontal": _build_bar_horizontal,
        "distribution": _build_distribution,
        "heatmap": _build_heatmap,
        "table": _build_table,
        "time_series": _build_time_series,
    }

    builder = builders.get(chart_type)
    if builder is None:
        raise ValueError(f"Unknown chart type: {chart_type}")

    fig = builder(data, spec)

    # Apply reference lines and annotations before theming
    _apply_reference_lines(fig, spec.get("reference_lines", []))
    _apply_annotations(fig, spec.get("annotations", []))

    # Apply the NYT theme with full title block
    apply_theme(fig, title=title, subtitle=subtitle, source=source)

    filename = spec.get("filename") or _slugify(title)
    path = charts_dir / f"{filename}.html"
    fig.write_html(str(path), include_plotlyjs="cdn")

    return {"path": str(path), "title": title}


# ---------------------------------------------------------------------------
# Context features — reference lines and annotations
# ---------------------------------------------------------------------------


_LINE_STYLES = {"solid": "solid", "dash": "dash", "dot": "dot"}


def _apply_reference_lines(fig: go.Figure, lines: list[dict]) -> None:
    """Add reference lines (hlines/vlines) to a figure."""
    for line in lines:
        axis = line.get("axis", "y")
        value = line.get("value")
        label = line.get("label", "")
        style = _LINE_STYLES.get(line.get("style", "dash"), "dash")

        kwargs = dict(
            line_dash=style,
            line_color=COLORS["spine"],
            line_width=1,
        )
        if label:
            kwargs.update(
                annotation_text=label,
                annotation_position="right" if axis == "y" else "top right",
                annotation_font=dict(
                    size=10,
                    color=COLORS["text_tertiary"],
                    family="Inter, sans-serif",
                ),
            )

        if axis == "y":
            fig.add_hline(y=value, **kwargs)
        else:
            fig.add_vline(x=value, **kwargs)


def _apply_annotations(fig: go.Figure, annotations: list[dict]) -> None:
    """Add point annotations to a figure."""
    for ann in annotations:
        annotate_point(
            fig,
            x=ann["x"],
            y=ann["y"],
            text=ann.get("text", ""),
            position=ann.get("position", "auto"),
        )


# ---------------------------------------------------------------------------
# Position color mapping (adhoc)
# ---------------------------------------------------------------------------

# Map standard position names to categorical colors
_POS_COLORS = dict(zip(
    ["QB", "RB", "WR", "TE"],
    color_for_mode("categorical", n=4),
))


def _resolve_color(row: dict, color_field: str | None, color_mode: str = "default") -> str:
    """Resolve a color for a data point."""
    if color_mode == "diverging" and color_field:
        val = row.get(color_field)
        if val is not None:
            neg, mid, pos = color_for_mode("diverging")
            if isinstance(val, (int, float)):
                if val > 0:
                    return pos
                elif val < 0:
                    return neg
                return mid
    if not color_field:
        return COLORS["data_default"]
    value = str(row.get(color_field, ""))
    if value in _POS_COLORS:
        return _POS_COLORS[value]
    return COLORS["data_default"]


# ---------------------------------------------------------------------------
# Chart type builders
# ---------------------------------------------------------------------------


def _build_scatter(data: list[dict], spec: dict) -> go.Figure:
    x_field = spec.get("x_field", "x")
    y_field = spec.get("y_field", "y")
    color_field = spec.get("color_field")
    label_field = spec.get("label_field")
    color_mode = spec.get("color_mode", "default")
    highlight = set(spec.get("highlight_players", []))

    bg_color, hl_color = color_for_mode("spotlight")
    fig = go.Figure()

    if color_field:
        groups: dict[str, list[dict]] = {}
        for row in data:
            key = str(row.get(color_field, "Other"))
            groups.setdefault(key, []).append(row)

        for group_name, rows in groups.items():
            color = _POS_COLORS.get(group_name, bg_color)
            fig.add_trace(go.Scatter(
                x=[r.get(x_field) for r in rows],
                y=[r.get(y_field) for r in rows],
                mode="markers+text" if label_field else "markers",
                text=[r.get(label_field, "") for r in rows] if label_field else None,
                textposition="top center",
                name=group_name,
                marker=dict(size=10, color=color),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{x_field}: %{{x:.3f}}<br>"
                    f"{y_field}: %{{y:.3f}}"
                    "<extra></extra>"
                ) if label_field else None,
            ))
    elif color_mode == "spotlight" and highlight and label_field:
        # Spotlight mode: gray for background, steel blue for highlighted
        bg_rows = [r for r in data if r.get(label_field) not in highlight]
        hl_rows = [r for r in data if r.get(label_field) in highlight]

        if bg_rows:
            fig.add_trace(go.Scatter(
                x=[r.get(x_field) for r in bg_rows],
                y=[r.get(y_field) for r in bg_rows],
                mode="markers+text" if label_field else "markers",
                text=[r.get(label_field, "") for r in bg_rows] if label_field else None,
                textposition="top center",
                marker=dict(size=8, color=bg_color, opacity=0.5),
                showlegend=False,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{x_field}: %{{x:.3f}}<br>"
                    f"{y_field}: %{{y:.3f}}"
                    "<extra></extra>"
                ) if label_field else None,
            ))
        if hl_rows:
            fig.add_trace(go.Scatter(
                x=[r.get(x_field) for r in hl_rows],
                y=[r.get(y_field) for r in hl_rows],
                mode="markers+text",
                text=[r.get(label_field, "") for r in hl_rows],
                textposition="top center",
                marker=dict(size=12, color=hl_color, line=dict(width=1.5, color=COLORS["text_primary"])),
                showlegend=False,
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    f"{x_field}: %{{x:.3f}}<br>"
                    f"{y_field}: %{{y:.3f}}"
                    "<extra></extra>"
                ),
            ))
    else:
        default_color = bg_color if color_mode == "spotlight" else COLORS["data_default"]
        fig.add_trace(go.Scatter(
            x=[r.get(x_field) for r in data],
            y=[r.get(y_field) for r in data],
            mode="markers+text" if label_field else "markers",
            text=[r.get(label_field, "") for r in data] if label_field else None,
            textposition="top center",
            marker=dict(size=10, color=default_color),
            hovertemplate=(
                "<b>%{text}</b><br>"
                f"{x_field}: %{{x:.3f}}<br>"
                f"{y_field}: %{{y:.3f}}"
                "<extra></extra>"
            ) if label_field else None,
        ))

    # Non-spotlight highlight overlay (for color_field grouping + highlights)
    if highlight and label_field and color_field:
        hl_rows = [r for r in data if r.get(label_field) in highlight]
        if hl_rows:
            fig.add_trace(go.Scatter(
                x=[r.get(x_field) for r in hl_rows],
                y=[r.get(y_field) for r in hl_rows],
                mode="markers+text",
                text=[r.get(label_field, "") for r in hl_rows],
                textposition="top center",
                name="Highlighted",
                marker=dict(size=14, color=hl_color, line=dict(width=2, color=COLORS["text_primary"])),
                showlegend=False,
            ))

    format_axis(fig, "x", x_field.replace("_", " ").title())
    format_axis(fig, "y", y_field.replace("_", " ").title())
    return fig


def _build_bar_horizontal(data: list[dict], spec: dict) -> go.Figure:
    y_field = spec.get("y_field") or spec.get("label_field", "label")
    x_field = spec.get("x_field") or "value"
    color_field = spec.get("color_field")
    color_mode = spec.get("color_mode", "default")

    sorted_data = sorted(data, key=lambda r: r.get(x_field, 0))

    # Diverging mode: color by sign of x-value
    if color_mode == "diverging":
        neg, mid, pos = color_for_mode("diverging")
        colors = []
        for r in sorted_data:
            val = r.get(x_field, 0) or 0
            if val > 0:
                colors.append(pos)
            elif val < 0:
                colors.append(neg)
            else:
                colors.append(mid)
    else:
        colors = [_resolve_color(r, color_field, color_mode) for r in sorted_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[r.get(x_field) for r in sorted_data],
        y=[r.get(y_field) for r in sorted_data],
        orientation="h",
        marker=dict(color=colors),
        hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
    ))

    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        height=max(400, len(data) * 22),
    )
    format_axis(fig, "x", x_field.replace("_", " ").title())
    return fig


def _build_distribution(data: list[dict], spec: dict) -> go.Figure:
    metric_field = spec.get("x_field") or spec.get("y_field", "value")
    group_field = spec.get("group_field")

    fig = go.Figure()

    if group_field:
        groups: dict[str, list] = {}
        for row in data:
            key = str(row.get(group_field, "All"))
            groups.setdefault(key, []).append(row.get(metric_field))

        for group_name, values in groups.items():
            color = _POS_COLORS.get(group_name, COLORS["data_default"])
            fig.add_trace(go.Box(
                y=values,
                name=group_name,
                marker_color=color,
                boxmean=True,
            ))
    else:
        values = [r.get(metric_field) for r in data]
        fig.add_trace(go.Histogram(
            x=values,
            marker_color=COLORS["data_default"],
        ))

    format_axis(fig, "y", metric_field.replace("_", " ").title() if group_field else "Count")
    return fig


def _build_heatmap(data: list[dict], spec: dict) -> go.Figure:
    import pandas as pd

    df = pd.DataFrame(data)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    corr = df[numeric_cols].corr()

    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=10, color=COLORS["text_secondary"]),
    ))

    fig.update_layout(
        height=max(500, len(numeric_cols) * 40),
        width=max(600, len(numeric_cols) * 40),
    )
    return fig


def _build_table(data: list[dict], spec: dict) -> go.Figure:
    if not data:
        return go.Figure()

    columns = list(data[0].keys())
    header_values = [c.replace("_", " ").title() for c in columns]
    cell_values = [[str(row.get(c, "")) for row in data] for c in columns]

    fig = go.Figure(data=go.Table(
        header=dict(
            values=header_values,
            fill_color=COLORS["gridline"],
            font=dict(size=12, color=COLORS["text_primary"], family="Inter, sans-serif"),
            align="left",
        ),
        cells=dict(
            values=cell_values,
            fill_color=COLORS["background"],
            font=dict(size=11, color=COLORS["text_secondary"], family="Inter, sans-serif"),
            align="left",
        ),
    ))

    fig.update_layout(height=max(400, len(data) * 30 + 100))
    return fig


def _build_time_series(data: list[dict], spec: dict) -> go.Figure:
    x_field = spec.get("x_field", "season")
    y_field = spec.get("y_field", "value")
    group_field = spec.get("group_field")
    color_mode = spec.get("color_mode", "default")
    highlight = set(spec.get("highlight_players", []))

    bg_color, hl_color = color_for_mode("spotlight")
    fig = go.Figure()

    if group_field:
        groups: dict[str, list[dict]] = {}
        for row in data:
            key = str(row.get(group_field, "All"))
            groups.setdefault(key, []).append(row)

        for group_name, rows in groups.items():
            sorted_rows = sorted(rows, key=lambda r: r.get(x_field, 0))

            # Spotlight mode: highlighted series are bold, others are faded gray
            if color_mode == "spotlight" and highlight:
                is_hl = group_name in highlight
                color = hl_color if is_hl else bg_color
                width = 3 if is_hl else 1.5
                opacity = 1.0 if is_hl else 0.4
            else:
                color = _POS_COLORS.get(group_name, bg_color)
                width = 3 if group_name in highlight else 2
                opacity = 1.0

            fig.add_trace(go.Scatter(
                x=[r.get(x_field) for r in sorted_rows],
                y=[r.get(y_field) for r in sorted_rows],
                mode="lines+markers",
                name=group_name,
                line=dict(color=color, width=width),
                marker=dict(size=8),
                opacity=opacity,
            ))
    else:
        sorted_data = sorted(data, key=lambda r: r.get(x_field, 0))
        fig.add_trace(go.Scatter(
            x=[r.get(x_field) for r in sorted_data],
            y=[r.get(y_field) for r in sorted_data],
            mode="lines+markers",
            marker=dict(size=8, color=bg_color),
        ))

    format_axis(fig, "x", x_field.replace("_", " ").title())
    format_axis(fig, "y", y_field.replace("_", " ").title())
    return fig


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert a title to a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    text = text.strip("_")
    return text[:80]
