{%- if cookiecutter.use_openai_compatible %}
"""Models served by an OpenAI-compatible endpoint.

One provider covers every server and gateway that speaks the OpenAI Chat
Completions API: a model router or LLM gateway (LiteLLM, Requesty, OrcaRouter,
Portkey, ...) or a self-hosted server (vLLM, llama.cpp, LM Studio, Ollama's
``/v1``). The endpoint is set at deploy time with ``OPENAI_COMPATIBLE_BASE_URL``,
and ``AI_MODEL`` names the model the way that endpoint does.
"""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import settings

# OpenAIProvider requires some key, and would otherwise fall back to
# OPENAI_API_KEY - which must never be sent to an arbitrary endpoint. Servers
# that check no key accept any value.
_NO_KEY = "not-needed"


def build_openai_compatible_model(model_name: str) -> OpenAIChatModel:
    """The model ``model_name`` (or ``AI_MODEL``) at ``OPENAI_COMPATIBLE_BASE_URL``.

    Raises:
        ValueError: No base URL or no model name is configured.
    """
    name = model_name or settings.AI_MODEL
    if not settings.OPENAI_COMPATIBLE_BASE_URL:
        raise ValueError(
            "OPENAI_COMPATIBLE_BASE_URL is not set - point it at your gateway or "
            "server, e.g. https://gateway.example.com/v1"
        )
    if not name:
        raise ValueError("AI_MODEL is not set - name the model as your endpoint serves it")
    provider = OpenAIProvider(
        base_url=settings.OPENAI_COMPATIBLE_BASE_URL,
        api_key=settings.OPENAI_COMPATIBLE_API_KEY or _NO_KEY,
    )
    return OpenAIChatModel(name, provider=provider)
{%- endif %}
