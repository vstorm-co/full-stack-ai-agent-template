{%- if cookiecutter.use_pydantic_ai %}
"""AI Agents module using PydanticAI.

This module contains agents that handle AI-powered interactions.
Tools are defined in the tools/ subdirectory.
"""

from app.agents.assistant import AssistantAgent, Deps

__all__ = ["AssistantAgent", "Deps"]
{%- elif cookiecutter.use_langchain %}
"""AI Agents module using LangChain.

This module contains agents that handle AI-powered interactions.
Tools are defined in the tools/ subdirectory.
"""

from app.agents.langchain_assistant import AgentContext, LangChainAssistant

__all__ = ["LangChainAssistant", "AgentContext"]
{%- elif cookiecutter.use_langgraph %}
"""AI Agents module using LangGraph.

This module contains a ReAct agent built with LangGraph.
Tools are defined in the tools/ subdirectory.
"""

from app.agents.langgraph_assistant import AgentContext, AgentState, LangGraphAssistant

__all__ = ["LangGraphAssistant", "AgentContext", "AgentState"]
{%- elif cookiecutter.use_deepagents %}
"""AI Agents module using DeepAgents.

This module contains an agentic coding assistant built with DeepAgents.
DeepAgents provides built-in tools for filesystem operations, task management,
and code execution.
"""

from app.agents.deepagents_assistant import AgentContext, DeepAgentsAssistant, InterruptData

__all__ = ["DeepAgentsAssistant", "AgentContext", "InterruptData"]
{%- elif cookiecutter.use_pydantic_deep %}
"""AI Agents module using PydanticDeep.

This module contains a deep agentic coding assistant built with pydantic-deep.
PydanticDeep is built on PydanticAI and provides filesystem operations,
task management, subagent delegation, skills, memory, and Docker sandbox support.
"""

from app.agents.pydantic_deep_assistant import PydanticDeepAssistant, PydanticDeepContext

__all__ = ["PydanticDeepAssistant", "PydanticDeepContext"]
{%- else %}
"""AI Agents - not configured."""
{%- endif %}
