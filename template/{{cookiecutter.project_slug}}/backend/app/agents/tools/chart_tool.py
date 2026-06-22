{%- if cookiecutter.enable_charts %}
"""Chart-generation tool for agents.

The agent calls ``create_chart`` to produce a structured chart specification.
The tool returns the spec as a JSON string — this single representation is:

- captured uniformly by every agent framework as the tool result,
- persisted verbatim in ``tool_calls.result`` (no DB migration needed),
- parsed by the web frontend and rendered interactively with Recharts,
{%- if cookiecutter.charts_channel_png %}
- rendered server-side to a PNG and sent as an image on Slack/Telegram.
{%- else %}
- (Slack/Telegram render as a markdown table fallback.)
{%- endif %}

The agent may override the default styling (palette, grid, legend, axis
labels, stacking) via the ``style`` argument.
"""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

ChartType = Literal["line", "bar", "pie", "area", "scatter"]

# Cap payload size so a runaway model can't emit a multi-megabyte tool result.
MAX_DATA_POINTS = 500
MAX_SERIES = 12


class ChartSeries(BaseModel):
    """One plotted series — maps a key in each data row to a labelled line/bar."""

    key: str = Field(description="Field name in each data row to plot.")
    label: str | None = Field(default=None, description="Legend label (defaults to key).")
    color: str | None = Field(default=None, description="Hex color override, e.g. '#6366f1'.")


class ChartStyle(BaseModel):
    """Agent-controlled styling overrides on top of the frontend defaults."""

    palette: list[str] | None = Field(
        default=None, description="Custom color palette (hex), applied series-by-series."
    )
    grid: bool = Field(default=True, description="Show background grid.")
    legend: bool = Field(default=True, description="Show the legend.")
    x_label: str | None = Field(default=None, description="X-axis title.")
    y_label: str | None = Field(default=None, description="Y-axis title.")
    stacked: bool = Field(default=False, description="Stack bar/area series.")


class ChartSpec(BaseModel):
    """Canonical chart payload produced by the tool and consumed by every surface."""

    kind: Literal["chart"] = "chart"
    chart_type: ChartType
    title: str = Field(max_length=200)
    data: list[dict[str, Any]] = Field(description="Rows, e.g. [{'x': 'Q1', 'revenue': 120}].")
    x_key: str = Field(default="x", description="Row field used for the x-axis / pie label.")
    series: list[ChartSeries] = Field(default_factory=list)
    style: ChartStyle = Field(default_factory=ChartStyle)

    @field_validator("data")
    @classmethod
    def _validate_data(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v:
            raise ValueError("data must contain at least one row")
        if len(v) > MAX_DATA_POINTS:
            raise ValueError(f"data has too many rows (max {MAX_DATA_POINTS})")
        return v

    @field_validator("series")
    @classmethod
    def _validate_series(cls, v: list[ChartSeries]) -> list[ChartSeries]:
        if len(v) > MAX_SERIES:
            raise ValueError(f"too many series (max {MAX_SERIES})")
        return v


def _infer_series(data: list[dict[str, Any]], x_key: str) -> list[ChartSeries]:
    """Derive series from the first row: every numeric field except the x-axis key."""
    if not data:
        return []
    first = data[0]
    inferred: list[ChartSeries] = []
    for key, value in first.items():
        if key == x_key:
            continue
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            inferred.append(ChartSeries(key=key))
    return inferred


def create_chart(
    chart_type: ChartType,
    title: str,
    data: list[dict[str, Any]],
    series: list[dict[str, Any]] | None = None,
    x_key: str = "x",
    style: dict[str, Any] | None = None,
) -> str:
    """Create a chart for the user.

    Use this whenever the user asks to visualize numbers, trends, comparisons,
    or distributions. The chart renders interactively in the web chat and as an
    image on messaging channels.

    Args:
        chart_type: One of "line", "bar", "pie", "area", "scatter".
        title: Short chart title shown above the plot.
        data: List of row dicts, e.g. [{"x": "Jan", "revenue": 120, "cost": 80}].
            For pie charts use [{"x": "Chrome", "value": 64}, ...].
        series: Optional list of {"key", "label"?, "color"?} selecting which row
            fields to plot. If omitted, every numeric field (except x_key) is plotted.
        x_key: The row field used for the x-axis (or pie slice label). Default "x".
        style: Optional overrides — {"palette": ["#6366f1", ...], "grid": true,
            "legend": true, "x_label": "...", "y_label": "...", "stacked": false}.

    Returns:
        A JSON string with the chart specification. Do not repeat this JSON back
        to the user — just briefly describe the chart you created.
    """
    try:
        resolved_series = [ChartSeries(**s) for s in series] if series else _infer_series(data, x_key)
        spec = ChartSpec(
            chart_type=chart_type,
            title=title,
            data=data,
            x_key=x_key,
            series=resolved_series,
            style=ChartStyle(**style) if style else ChartStyle(),
        )
    except ValidationError as e:
        return f"Could not build chart — invalid arguments: {e.errors()}"
    except (TypeError, ValueError) as e:
        return f"Could not build chart: {e}"

    if not spec.series:
        return (
            "Could not build chart: no numeric series found. Provide a `series` "
            "list or ensure data rows contain numeric fields besides x_key."
        )

    return spec.model_dump_json()


def create_chart_tool(
    chart_type: ChartType,
    title: str,
    data: list[dict[str, Any]],
    series: list[dict[str, Any]] | None = None,
    x_key: str = "x",
    style: dict[str, Any] | None = None,
) -> str:
    """Create a chart (line/bar/pie/area/scatter) to visualize data for the user.

    Use whenever the user asks to plot, chart, graph, or visualize numbers,
    trends, comparisons, or distributions. Do not repeat the returned JSON
    back to the user — just briefly describe the chart you created.

    Args:
        chart_type: One of "line", "bar", "pie", "area", "scatter".
        title: Short chart title.
        data: Row dicts, e.g. [{"x": "Jan", "revenue": 120}]. For pie:
            [{"x": "Chrome", "value": 64}, ...].
        series: Optional [{"key", "label"?, "color"?}] selecting fields to plot.
        x_key: Row field for the x-axis / pie label (default "x").
        style: Optional {"palette", "grid", "legend", "x_label", "y_label", "stacked"}.

    Scatter charts: every data point MUST have numeric "x" and "y" fields.
    To show categories with different colors, add a "category" string field to
    each row and define one series per category where series key == category value.
    Example: data=[{"x": 2.0, "y": 4.1, "category": "A"}, {"x": 3.5, "y": 2.8, "category": "B"}],
    series=[{"key": "A", "label": "Group A"}, {"key": "B", "label": "Group B"}], x_key="x".
    """
    return create_chart(
        chart_type=chart_type,
        title=title,
        data=data,
        series=series,
        x_key=x_key,
        style=style,
    )


def parse_chart_spec(result: str) -> ChartSpec | None:
    """Parse a ``create_chart`` tool result back into a ChartSpec.

    Returns None if the result is an error string rather than a valid spec
    (used by the channel/web delivery layers).
    """
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != "chart":
        return None
    try:
        return ChartSpec.model_validate(payload)
    except ValidationError:
        return None
{%- endif %}
