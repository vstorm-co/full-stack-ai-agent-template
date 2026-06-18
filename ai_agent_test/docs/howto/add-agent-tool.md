# How to: Add a New Agent Tool

## Overview

Agent tools let your AI agent perform actions — search the web, query databases, send emails, etc. Each tool is a Python function that the agent can call.

## Step-by-Step

### 1. Create the tool file

```python
# app/agents/tools/weather.py
# PydanticAI tools are async functions decorated at registration time
async def get_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: Name of the city to get weather for.

    Returns:
        Weather description string.
    """
    # Your implementation here (API call, etc.)
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://wttr.in/{city}?format=3")
        return resp.text
```

### 2. Export from `app/agents/tools/__init__.py`

```python
from app.agents.tools.weather import get_weather
```

### 3. Register in your agent

In `app/agents/assistant.py`, add the tool to the agent:

```python
@agent.tool
async def weather_tool(ctx: RunContext[Deps], city: str) -> str:
    """Get current weather for a city."""
    from app.agents.tools.weather import get_weather
    return await get_weather(city)
```

### 4. Test it

Start the server and ask the agent: "What's the weather in Warsaw?"

## Tips

- Keep tools focused — one tool, one job
- Write clear docstrings — the agent uses them to decide when to call your tool
- Handle errors gracefully — return error messages as strings, don't raise exceptions
- For expensive operations, consider adding caching
