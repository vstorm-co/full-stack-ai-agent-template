---
name: agent-tool
description: Add a new tool/function the AI agent can call (e.g. look something up, hit an external API, perform an action). Use when extending the assistant's capabilities, wiring a new function into the agent, or when the model needs a new action. This project uses {{ cookiecutter.ai_framework }}.
---

# Add an Agent Tool ({{ cookiecutter.ai_framework }})

Agent tools live in `backend/app/agents/tools/` and are surfaced to the model so it can call them mid-conversation. The assistant is defined in `backend/app/agents/`.

## Steps

1. **Write the tool function** in `backend/app/agents/tools/<tool_name>.py`:
   - Async, fully type-hinted, with a clear docstring — **the docstring and signature are what the model sees**, so make them precise.
   - Pure logic: take typed args, return a JSON-serializable result. Raise on hard errors; return a structured `{"error": ...}` for soft failures the model should reason about.
   - Keep secrets/IO behind `settings` and the service layer; don't inline credentials.

2. **Export it** from `backend/app/agents/tools/__init__.py` (add the import and append to `__all__`, matching the existing feature-gated blocks).

3. **Register it on the agent** in the assistant for the active framework:
{%- if cookiecutter.use_pydantic_ai %}
   - `app/agents/assistant.py` — decorate with `@agent.tool` (needs `RunContext[Deps]`) or `@agent.tool_plain` (no context):
     ```python
     @agent.tool
     async def my_tool(ctx: RunContext[Deps], query: str) -> dict:
         """One-line description the model reads to decide when to call this."""
         ...
     ```
{%- elif cookiecutter.use_pydantic_deep %}
   - `app/agents/pydantic_deep_assistant.py` — add the function to the agent's tool list.
{%- elif cookiecutter.use_langchain %}
   - `app/agents/langchain_assistant.py` — wrap with `@tool` and add it to the `tools=[...]` passed to the agent.
{%- elif cookiecutter.use_langgraph %}
   - `app/agents/langgraph_assistant.py` — wrap with `@tool` and include it in the tools list bound to the graph.
{%- elif cookiecutter.use_deepagents %}
   - `app/agents/deepagents_assistant.py` — add the function to the agent's tool list.
{%- endif %}

4. **Prompt guidance (optional but recommended):** if the tool should only be used in specific situations, add a sentence to the system prompt in `app/agents/prompts.py` so the model knows *when* to reach for it.

5. **Frontend rendering (optional):** tool calls render as cards in the chat UI. For a bespoke card, add a renderer under `frontend/src/components/chat/tool-results/`; otherwise the generic card handles it.

6. **Test it:** add `backend/tests/test_<tool_name>.py` (see existing `test_web_search.py` / `test_chart_tool.py`). Tools are plain async functions — test them directly, no agent needed.

## Rules

- The docstring is the contract with the model — keep it accurate and action-oriented.
- Return small, structured payloads; don't dump huge blobs into the context.
- Long-running or side-effecting work belongs in a service (and possibly a background task), not inline in the tool.
- See `docs/howto/add-agent-tool.md` for a fuller walkthrough.
