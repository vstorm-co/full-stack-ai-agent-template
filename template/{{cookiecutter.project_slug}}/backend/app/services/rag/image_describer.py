{%- if cookiecutter.enable_rag and cookiecutter.enable_rag_image_description %}
"""LLM-based image description for RAG document processing."""

import asyncio
import base64
import logging
from abc import ABC, abstractmethod

from app.core.config import settings

{%- if cookiecutter.use_langchain or cookiecutter.use_langgraph %}
{%- if cookiecutter.use_openai %}
from langchain_openai import ChatOpenAI
{%- elif cookiecutter.use_anthropic %}
from langchain_anthropic import ChatAnthropic
{%- elif cookiecutter.use_google %}
from langchain_google_genai import ChatGoogleGenerativeAI
{%- endif %}
{%- endif %}

logger = logging.getLogger(__name__)

IMAGE_DESCRIPTION_PROMPT = (
    "Describe this image in detail. Focus on any text, data, charts, diagrams, "
    "or visual information that would be useful for document search and retrieval. "
    "Be concise but comprehensive."
)


class BaseImageDescriber(ABC):
    """Abstract base for LLM-based image description."""

    @abstractmethod
    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Generate a text description of an image."""


def _b64_encode(image_bytes: bytes) -> str:
    """Base64-encode raw image bytes."""
    return base64.b64encode(image_bytes).decode("utf-8")


{%- if cookiecutter.use_pydantic_ai %}


class PydanticAIImageDescriber(BaseImageDescriber):
    """Image description using PydanticAI (supports all providers)."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
            from pydantic_ai import Agent
            from pydantic_ai.messages import BinaryContent

            agent = Agent(self.model_name)
            result = await agent.run(
                [
                    BinaryContent(data=image_bytes, media_type=mime_type),
                    IMAGE_DESCRIPTION_PROMPT,
                ]
            )
            return result.output if hasattr(result, "output") else str(result.data)
        except Exception as e:
            logger.error("PydanticAI image description failed: %s", e)
            return ""


{%- elif cookiecutter.use_langchain or cookiecutter.use_langgraph %}


class LangChainImageDescriber(BaseImageDescriber):
    """Image description using LangChain ChatModel with vision."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
{%- if cookiecutter.use_openai %}
            self._llm = ChatOpenAI(model=self.model_name)
{%- elif cookiecutter.use_anthropic %}
            self._llm = ChatAnthropic(model=self.model_name)
{%- elif cookiecutter.use_google %}
            self._llm = ChatGoogleGenerativeAI(model=self.model_name)
{%- endif %}
        return self._llm

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
            from langchain_core.messages import HumanMessage

            b64 = _b64_encode(image_bytes)
            llm = self._get_llm()
            message = HumanMessage(
                content=[
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                ]
            )
            response = await llm.ainvoke([message])
            return response.content if isinstance(response.content, str) else str(response.content)
        except Exception as e:
            logger.error("LangChain image description failed: %s", e)
            return ""


{%- elif cookiecutter.use_deepagents %}


class DeepAgentsImageDescriber(BaseImageDescriber):
    """Image description using DeepAgents (delegates to LLM provider directly)."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
{%- if cookiecutter.use_openai %}
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            b64 = _b64_encode(image_bytes)
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ]}],
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
{%- elif cookiecutter.use_anthropic %}
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            b64 = _b64_encode(image_bytes)
            response = await client.messages.create(
                model=self.model_name, max_tokens=500,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                ]}],
            )
            return response.content[0].text if response.content else ""
{%- endif %}
        except Exception as e:
            logger.error("DeepAgents image description failed: %s", e)
            return ""
{%- endif %}
{%- endif %}
