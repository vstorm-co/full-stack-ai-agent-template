{%- if cookiecutter.enable_code_execution %}
"""Code-execution tool backed by the Monty sandbox.

Runs model-written Python inside the Monty sandboxed interpreter, exposing a
curated set of our own tools as plain in-sandbox functions. In one tool turn
the model can compute, loop, transform data, and call those tools — including
several ``create_chart`` calls in a single ``asyncio.gather(...)`` block.

Visualizations produced from *inside* the executed code are surfaced to the
live session through an ``emit_tool_event`` callback, so each one renders as
an interactive chart/map card (and is persisted) exactly like a direct tool
call — rather than being buried inside the ``run_python`` result.

This is a thin local stand-in for PydanticAI's forthcoming
``CodeExecutionToolset``; swap to the official class once it ships.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_monty import CollectString, Monty, MontyError, ResourceLimits

{%- if cookiecutter.enable_charts or cookiecutter.enable_antv_charts %}
from app.agents.tools.chart_tool import create_chart
{%- endif %}
from app.agents.tools.datetime_tool import get_current_datetime
{%- if cookiecutter.enable_antv_charts %}
from app.agents.tools.map_tool import create_map
{%- endif %}
from app.core.config import settings

logger = logging.getLogger(__name__)

EmitToolEvent = Callable[[str, dict[str, Any], str], Awaitable[None]]

MAX_OUTPUT_CHARS = 8000
{%- if cookiecutter.enable_antv_charts %}


async def _call_antv(tool_name: str, args: dict[str, Any]) -> str:
    """Call an AntV ``mcp-server-chart`` tool over MCP and return the image URL.

    The sidecar renders server-side and returns a bare URL string. We open a
    short-lived streamable-HTTP session per call — fine for the handful of
    charts a single run produces.
    """
    if not settings.ENABLE_ANTV_CHARTS:
        return (
            "AntV charts are disabled (ENABLE_ANTV_CHARTS=false). "
            "Skip the generate_* chart and rely on create_chart instead."
        )
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with (
            streamablehttp_client(settings.ANTV_MCP_URL) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            result = await session.call_tool(tool_name, args)
        if result.isError:
            detail = result.content[0].text if result.content else "unknown error"  # type: ignore[union-attr]
            return f"Chart generation failed ({tool_name}): {detail}"
        for item in result.content:
            text = getattr(item, "text", None)
            if text:
                return text.strip()
        return f"Chart generation returned no image ({tool_name})."
    except Exception as exc:  # noqa: BLE001 — surface a readable message to the model
        logger.warning("AntV call %s failed: %s", tool_name, exc)
        return f"Chart generation failed ({tool_name}): {exc}"
{%- endif %}


def _build_external_functions(emit: EmitToolEvent | None) -> dict[str, Callable[..., Any]]:
    """Build the callables exposed to sandboxed code, wired to emit live events."""

    functions: dict[str, Callable[..., Any]] = {}

{%- if cookiecutter.enable_charts or cookiecutter.enable_antv_charts %}

    async def _create_chart(
        chart_type: str,
        title: str,
        data: list[dict[str, Any]],
        series: list[dict[str, Any]] | None = None,
        x_key: str = "x",
        style: dict[str, Any] | None = None,
    ) -> str:
        spec = create_chart(
            chart_type=chart_type,  # type: ignore[arg-type]
            title=title,
            data=data,
            series=series,
            x_key=x_key,
            style=style,
        )
        if emit is not None:
            await emit(
                "create_chart_tool",
                {
                    "chart_type": chart_type,
                    "title": title,
                    "data": data,
                    "series": series,
                    "x_key": x_key,
                    "style": style,
                },
                spec,
            )
        return spec

    functions["create_chart"] = _create_chart
{%- endif %}

{%- if cookiecutter.enable_antv_charts %}

    async def _create_map(
        title: str,
        markers: list[dict[str, Any]],
        center: list[float] | None = None,
        zoom: int | None = None,
    ) -> str:
        spec = create_map(title=title, markers=markers, center=center, zoom=zoom)
        if emit is not None:
            await emit(
                "create_map_tool",
                {"title": title, "markers": markers, "center": center, "zoom": zoom},
                spec,
            )
        return spec

    functions["create_map"] = _create_map
{%- endif %}

    def _current_datetime() -> dict[str, str]:
        return get_current_datetime()

    functions["current_datetime"] = _current_datetime

{%- if cookiecutter.enable_antv_charts %}

    async def _emit_antv(tool_name: str, args: dict[str, Any]) -> str:
        """Run an AntV chart tool and stream it to the live session like a real
        tool call, so it renders as a chart card and gets persisted."""
        # Drop None values so the sidecar applies its own defaults.
        clean = {k: v for k, v in args.items() if v is not None and v != ""}
        url = await _call_antv(tool_name, clean)
        if emit is not None and url.startswith("http"):
            await emit(tool_name, clean, url)
        return url

    async def _gen_waterfall(
        title: str,
        data: list[dict[str, Any]],
        axisXTitle: str = "",
        axisYTitle: str = "",
    ) -> str:
        return await _emit_antv(
            "generate_waterfall_chart",
            {"title": title, "data": data, "axisXTitle": axisXTitle, "axisYTitle": axisYTitle},
        )

    async def _gen_sankey(
        title: str,
        data: list[dict[str, Any]],
        nodeAlign: str = "center",
    ) -> str:
        return await _emit_antv(
            "generate_sankey_chart",
            {"title": title, "data": data, "nodeAlign": nodeAlign},
        )

    async def _gen_funnel(title: str, data: list[dict[str, Any]]) -> str:
        return await _emit_antv("generate_funnel_chart", {"title": title, "data": data})

    async def _gen_treemap(title: str, data: list[dict[str, Any]]) -> str:
        return await _emit_antv("generate_treemap_chart", {"title": title, "data": data})

    async def _gen_radar(title: str, data: list[dict[str, Any]]) -> str:
        return await _emit_antv("generate_radar_chart", {"title": title, "data": data})

    async def _gen_histogram(
        title: str,
        data: list[Any],
        binNumber: int | None = None,
        axisXTitle: str = "",
        axisYTitle: str = "",
    ) -> str:
        return await _emit_antv(
            "generate_histogram_chart",
            {
                "title": title,
                "data": data,
                "binNumber": binNumber,
                "axisXTitle": axisXTitle,
                "axisYTitle": axisYTitle,
            },
        )

    async def _gen_boxplot(
        title: str,
        data: list[dict[str, Any]],
        axisXTitle: str = "",
        axisYTitle: str = "",
    ) -> str:
        return await _emit_antv(
            "generate_boxplot_chart",
            {"title": title, "data": data, "axisXTitle": axisXTitle, "axisYTitle": axisYTitle},
        )

    async def _gen_dual_axes(
        title: str,
        categories: list[Any],
        series: list[dict[str, Any]],
        axisXTitle: str = "",
    ) -> str:
        return await _emit_antv(
            "generate_dual_axes_chart",
            {"title": title, "categories": categories, "series": series, "axisXTitle": axisXTitle},
        )

    functions["generate_waterfall_chart"] = _gen_waterfall
    functions["generate_sankey_chart"] = _gen_sankey
    functions["generate_funnel_chart"] = _gen_funnel
    functions["generate_treemap_chart"] = _gen_treemap
    functions["generate_radar_chart"] = _gen_radar
    functions["generate_histogram_chart"] = _gen_histogram
    functions["generate_boxplot_chart"] = _gen_boxplot
    functions["generate_dual_axes_chart"] = _gen_dual_axes
{%- endif %}

    return functions


def _clip(text: str) -> str:
    """Cap text handed back to the model so a huge result/error can't blow up the turn."""
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n…(output truncated)"
    return text


def _format_result(stdout: str, output: Any) -> str:
    """Combine captured stdout and the final expression value for the model."""
    parts: list[str] = []
    if stdout.strip():
        parts.append(f"stdout:\n{stdout.rstrip()}")
    if output is not None:
        try:
            rendered = json.dumps(output, default=str)
        except (TypeError, ValueError):
            rendered = str(output)
        parts.append(f"result: {rendered}")
    text = "\n\n".join(parts) if parts else "(code ran successfully with no output)"
    return _clip(text)


async def run_python(code: str, *, emit: EmitToolEvent | None = None) -> str:
    """Execute model-written Python in the Monty sandbox and return its output.

    Args:
        code: The Python source to run. A restricted stdlib subset (``math``,
            ``asyncio``, ``json``, ``datetime``, ``re``) works, but modules like
            ``statistics``/``random``/``itertools`` are unavailable.
        emit: Optional callback used to stream visualizations created inside the
            code to the live session.

    Returns:
        The captured stdout plus the value of the final expression, or an error
        message the model can read and recover from.
    """
    limits: ResourceLimits = {
        "max_duration_secs": settings.CODE_EXECUTION_TIMEOUT_SECS,
        "max_allocations": settings.CODE_EXECUTION_MAX_ALLOCATIONS,
    }
    collector = CollectString()
    try:
        monty = await Monty.acreate(code)
        output = await monty.run_async(
            external_functions=_build_external_functions(emit),
            print_callback=collector,
            limits=limits,
        )
    except MontyError as e:
        return _clip(f"Execution failed: {e}")
    except Exception as e:
        logger.exception("run_python execution failed")
        return _clip(f"Execution failed: {e}")

    return _format_result(collector.output, output)
{%- endif %}
