{%- if cookiecutter.enable_charts %}
"""Tests for the agent chart-generation tool."""
# ruff: noqa: I001 - Imports structured for Jinja2 template conditionals

import json

import pytest

from app.agents.tools.chart_tool import (
    ChartSpec,
    create_chart,
    parse_chart_spec,
)
{%- if cookiecutter.charts_channel_png %}
from app.services.channels.chart_render import chart_to_markdown, render_chart_png
{%- endif %}


class TestCreateChart:
    """create_chart returns a valid JSON ChartSpec or a helpful error string."""

    @pytest.mark.parametrize("chart_type", ["line", "bar", "pie", "area", "scatter"])
    def test_create_chart_each_type_returns_valid_spec(self, chart_type: str):
        result = create_chart(
            chart_type=chart_type,
            title="Demo",
            data=[{"x": "A", "y": 1}, {"x": "B", "y": 2}],
        )
        payload = json.loads(result)
        assert payload["kind"] == "chart"
        assert payload["chart_type"] == chart_type
        assert payload["title"] == "Demo"

    def test_series_inferred_from_numeric_fields(self):
        result = create_chart(
            chart_type="line",
            title="Auto series",
            data=[{"x": "Jan", "revenue": 10, "cost": 5}],
        )
        payload = json.loads(result)
        keys = {s["key"] for s in payload["series"]}
        assert keys == {"revenue", "cost"}

    def test_explicit_series_and_style_preserved(self):
        result = create_chart(
            chart_type="bar",
            title="Styled",
            data=[{"x": "A", "v": 3}],
            series=[{"key": "v", "label": "Value", "color": "#123456"}],
            style={"grid": False, "legend": False, "stacked": True, "palette": ["#abcdef"]},
        )
        payload = json.loads(result)
        assert payload["series"][0]["label"] == "Value"
        assert payload["series"][0]["color"] == "#123456"
        assert payload["style"]["grid"] is False
        assert payload["style"]["stacked"] is True
        assert payload["style"]["palette"] == ["#abcdef"]

    def test_invalid_chart_type_returns_error_string(self):
        result = create_chart(
            chart_type="donut",  # not a supported type
            title="Bad",
            data=[{"x": "A", "y": 1}],
        )
        assert "Could not build chart" in result
        assert parse_chart_spec(result) is None

    def test_empty_data_returns_error_string(self):
        result = create_chart(chart_type="line", title="Empty", data=[])
        assert "Could not build chart" in result

    def test_no_numeric_series_returns_error_string(self):
        result = create_chart(
            chart_type="line",
            title="No numbers",
            data=[{"x": "A", "label": "only text"}],
        )
        assert "no numeric series" in result


class TestParseChartSpec:
    """parse_chart_spec round-trips valid specs and rejects junk."""

    def test_round_trip(self):
        result = create_chart(
            chart_type="pie",
            title="Round trip",
            data=[{"x": "Chrome", "value": 64}, {"x": "Safari", "value": 36}],
            series=[{"key": "value"}],
        )
        spec = parse_chart_spec(result)
        assert isinstance(spec, ChartSpec)
        assert spec.chart_type == "pie"
        assert spec.title == "Round trip"

    def test_non_chart_json_returns_none(self):
        assert parse_chart_spec('{"kind": "something_else"}') is None

    def test_invalid_json_returns_none(self):
        assert parse_chart_spec("not json at all") is None

{%- if cookiecutter.charts_channel_png %}


class TestChartRender:
    """Server-side PNG rendering for messaging channels."""

    @pytest.mark.parametrize("chart_type", ["line", "bar", "pie", "area", "scatter"])
    def test_render_chart_png_returns_png_bytes(self, chart_type: str):
        spec = parse_chart_spec(
            create_chart(
                chart_type=chart_type,
                title="Render",
                data=[{"x": "A", "y": 1}, {"x": "B", "y": 4}],
                series=[{"key": "y"}],
            )
        )
        assert spec is not None
        png = render_chart_png(spec)
        assert isinstance(png, bytes)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic header

    def test_chart_to_markdown_fallback(self):
        spec = parse_chart_spec(
            create_chart(
                chart_type="bar",
                title="Fallback",
                data=[{"x": "A", "y": 1}],
                series=[{"key": "y"}],
            )
        )
        assert spec is not None
        text = chart_to_markdown(spec)
        assert "Fallback" in text
        assert "A" in text
{%- endif %}
{%- endif %}
