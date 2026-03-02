{%- if cookiecutter.enable_ai_agent %}
"""System prompts for AI agents.

Centralized location for all agent prompts to make them easy to find and modify.
"""

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant."""


def get_system_prompt_with_rag() -> str:
    """Get system prompt with RAG tool usage instruction.

    Returns:
        System prompt that instructs the agent to use search_documents
        tool to find information from uploaded documents before answering.
    """
    return f"""{DEFAULT_SYSTEM_PROMPT}

You have access to a knowledge base of uploaded documents. Use the search_documents
tool to find relevant information before responding to user queries.

Guidelines:
- Always use search_documents to look up information in your knowledge base
  before providing answers
- Cite sources by referring to the document filename from the search results
- If search returns no results, inform the user and provide a general response
- Combine information from multiple documents when relevant."""


{%- else %}
"""AI Agent prompts - not configured."""
{%- endif %}
