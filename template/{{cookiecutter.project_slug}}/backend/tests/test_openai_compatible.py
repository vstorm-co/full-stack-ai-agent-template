{%- if cookiecutter.use_openai_compatible %}
"""The model at an OpenAI-compatible endpoint, configured at deploy time."""

import pytest
from pydantic_ai.models.openai import OpenAIChatModel

from app.agents.openai_compatible import build_openai_compatible_model
from app.core.config import settings


@pytest.fixture
def endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OPENAI_COMPATIBLE_BASE_URL", "http://gateway.test/v1")
    monkeypatch.setattr(settings, "OPENAI_COMPATIBLE_API_KEY", "gw-key")
    monkeypatch.setattr(settings, "AI_MODEL", "qwen2.5")


def test_the_configured_model_is_served_by_the_endpoint(endpoint: None) -> None:
    model = build_openai_compatible_model("")

    assert isinstance(model, OpenAIChatModel)
    assert model.model_name == "qwen2.5"
    assert str(model.base_url) == "http://gateway.test/v1/"


def test_a_requested_model_overrides_the_default(endpoint: None) -> None:
    assert build_openai_compatible_model("llama-3.3").model_name == "llama-3.3"


def test_the_openai_key_never_reaches_the_endpoint(
    endpoint: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An endpoint that checks no key still gets a stand-in, never OPENAI_API_KEY."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real-openai-key")
    monkeypatch.setattr(settings, "OPENAI_COMPATIBLE_API_KEY", "")

    model = build_openai_compatible_model("")

    assert model.client.api_key != "sk-real-openai-key"


def test_without_a_base_url_it_says_what_to_set(
    endpoint: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "OPENAI_COMPATIBLE_BASE_URL", "")

    with pytest.raises(ValueError, match="OPENAI_COMPATIBLE_BASE_URL"):
        build_openai_compatible_model("")


def test_without_a_model_it_says_what_to_set(
    endpoint: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "AI_MODEL", "")

    with pytest.raises(ValueError, match="AI_MODEL"):
        build_openai_compatible_model("")
{%- else %}
"""OpenAI-compatible endpoint tests - not configured (another LLM provider)."""
{%- endif %}
