"""Agent tools module.

This module contains utility functions that can be used as agent tools.
Tools are registered in the agent definition using @agent.tool decorator.
"""

from app.agents.tools.datetime_tool import get_current_datetime
{%- if cookiecutter.enable_web_search %}
from app.agents.tools.web_search import parse_web_search, web_search, web_search_sync
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import search_knowledge_base, search_knowledge_base_sync
{%- endif %}
{%- if cookiecutter.enable_charts %}
from app.agents.tools.chart_tool import create_chart, parse_chart_spec
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
from app.agents.tools.map_tool import create_map
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
from app.agents.tools.fetch_url import fetch_url, fetch_url_sync
{%- endif %}

__all__ = ["get_current_datetime"]
{%- if cookiecutter.enable_web_search %}
__all__ += ["parse_web_search", "web_search", "web_search_sync"]
{%- endif %}
{%- if cookiecutter.enable_rag %}
__all__ += ["search_knowledge_base", "search_knowledge_base_sync"]
{%- endif %}
{%- if cookiecutter.enable_charts %}
__all__ += ["create_chart", "parse_chart_spec"]
{%- endif %}
{%- if cookiecutter.enable_antv_charts %}
__all__ += ["create_map"]
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
__all__ += ["fetch_url", "fetch_url_sync"]
{%- endif %}
