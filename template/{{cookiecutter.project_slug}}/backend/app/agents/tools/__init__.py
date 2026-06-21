"""Agent tools module.

This module contains utility functions that can be used as agent tools.
Tools are registered in the agent definition using @agent.tool decorator.
"""

{%- if cookiecutter.enable_web_search %}
from app.agents.tools.web_search import web_search
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.agents.tools.rag_tool import search_knowledge_base
{%- endif %}
{%- if cookiecutter.enable_charts %}
from app.agents.tools.chart_tool import create_chart
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
from app.agents.tools.fetch_url import fetch_url
{%- endif %}

__all__: list[str] = []
{%- if cookiecutter.enable_web_search %}
__all__ += ["web_search"]
{%- endif %}
{%- if cookiecutter.enable_rag %}
__all__ += ["search_knowledge_base"]
{%- endif %}
{%- if cookiecutter.enable_charts %}
__all__ += ["create_chart"]
{%- endif %}
{%- if cookiecutter.web_fetch_tool %}
__all__ += ["fetch_url"]
{%- endif %}
