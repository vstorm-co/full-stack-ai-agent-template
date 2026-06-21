{%- if cookiecutter.charts_channel_png %}
"""Server-side PNG rendering of chart specs for messaging channels.

The web frontend renders charts interactively with Recharts. Slack and
Telegram can't, so the channel router renders the same ``ChartSpec`` to a
PNG with matplotlib and sends it as an image. A markdown-table fallback is
used if rendering fails (see ``chart_to_markdown``).

matplotlib is an optional dependency, installed only when the chart tool and
a messaging channel are both enabled.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING

from app.agents.tools.chart_tool import ChartSpec

if TYPE_CHECKING:
    from matplotlib.axes import Axes

DEFAULT_PALETTE = [
    "#6366f1",
    "#10b981",
    "#f59e0b",
    "#ef4444",
    "#8b5cf6",
    "#06b6d4",
    "#ec4899",
    "#84cc16",
]


def _palette(spec: ChartSpec) -> list[str]:
    return spec.style.palette or DEFAULT_PALETTE


def _color(palette: list[str], index: int, override: str | None) -> str:
    return override or palette[index % len(palette)]


def _x_values(spec: ChartSpec) -> list[str]:
    return [str(row.get(spec.x_key, "")) for row in spec.data]


def _render_pie(ax: Axes, spec: ChartSpec, palette: list[str]) -> None:
    value_key = spec.series[0].key if spec.series else "value"
    values = [float(row.get(value_key, 0) or 0) for row in spec.data]
    ax.pie(
        values,
        labels=_x_values(spec),
        autopct="%1.1f%%",
        colors=[_color(palette, i, None) for i in range(len(values))],
    )
    ax.axis("equal")


def _render_cartesian(ax: Axes, spec: ChartSpec, palette: list[str]) -> None:
    import numpy as np

    x_values = _x_values(spec)
    bar_width = 0.8 / max(len(spec.series), 1)
    indices = np.arange(len(x_values))
    bottom = np.zeros(len(x_values))

    for i, series in enumerate(spec.series):
        y_values = [float(row.get(series.key, 0) or 0) for row in spec.data]
        color = _color(palette, i, series.color)
        label = series.label or series.key

        if spec.chart_type == "bar" and spec.style.stacked:
            ax.bar(indices, y_values, 0.6, bottom=bottom, label=label, color=color)
            bottom += np.array(y_values)
        elif spec.chart_type == "bar":
            ax.bar(indices + i * bar_width, y_values, bar_width, label=label, color=color)
        elif spec.chart_type == "area":
            ax.fill_between(indices, y_values, alpha=0.25, color=color)
            ax.plot(indices, y_values, label=label, color=color)
        elif spec.chart_type == "scatter":
            ax.scatter(indices, y_values, label=label, color=color)
        else:  # line (default)
            ax.plot(indices, y_values, label=label, color=color, linewidth=2)

    ax.set_xticks(indices)
    ax.set_xticklabels(x_values, rotation=45 if len(x_values) > 6 else 0, ha="right")
    if spec.style.grid:
        ax.grid(True, alpha=0.3)
    if spec.style.x_label:
        ax.set_xlabel(spec.style.x_label)
    if spec.style.y_label:
        ax.set_ylabel(spec.style.y_label)
    if spec.style.legend and spec.series:
        ax.legend()


def render_chart_png(spec: ChartSpec) -> bytes:
    """Render a ChartSpec to PNG bytes. Raises if matplotlib is unavailable."""
    import matplotlib

    matplotlib.use("Agg")  # headless — no display backend
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=130)
    if spec.chart_type == "pie":
        _render_pie(ax, spec, _palette(spec))
    else:
        _render_cartesian(ax, spec, _palette(spec))
    ax.set_title(spec.title, fontsize=13, fontweight="bold")
    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def chart_to_markdown(spec: ChartSpec) -> str:
    """Text-table fallback when PNG rendering is unavailable."""
    lines = [f"*{spec.title}* ({spec.chart_type} chart)", ""]
    keys = [s.key for s in spec.series] or ["value"]
    labels = [s.label or s.key for s in spec.series] or ["value"]
    header = " | ".join([spec.x_key, *labels])
    lines.append(header)
    lines.append("-" * len(header))
    for row in spec.data[:25]:
        cells = [str(row.get(spec.x_key, "")), *(str(row.get(k, "")) for k in keys)]
        lines.append(" | ".join(cells))
    if len(spec.data) > 25:
        lines.append(f"... (+{len(spec.data) - 25} more rows)")
    return "\n".join(lines)
{%- endif %}
