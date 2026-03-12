"""Tests for RAG configuration in fastapi_gen.config module."""

import pytest
from pydantic import ValidationError

from fastapi_gen.config import (
    BackgroundTaskType,
    EmbeddingProviderType,
    LLMProviderType,
    OAuthProvider,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    VectorStoreType,
)


class TestRAGValidation:
    """Tests for RAG-related validation rules."""

    def test_rag_requires_ai_agent(self) -> None:
        """Test that RAG requires AI agent to be enabled."""
        with pytest.raises(ValidationError, match="RAG requires AI agent"):
            ProjectConfig(
                project_name="test_rag",
                enable_ai_agent=False,
                rag_features=RAGFeatures(enable_rag=True),
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=True,
                enable_docker=True,
            )

    def test_rag_requires_background_tasks(self) -> None:
        """Test that RAG requires a background task system."""
        with pytest.raises(ValidationError, match="RAG requires a background task system"):
            ProjectConfig(
                project_name="test_rag",
                enable_ai_agent=True,
                rag_features=RAGFeatures(enable_rag=True),
                background_tasks=BackgroundTaskType.NONE,
                enable_docker=True,
            )

    def test_rag_requires_docker(self) -> None:
        """Test that RAG with Milvus requires Docker."""
        with pytest.raises(ValidationError, match="RAG.*requires Docker"):
            ProjectConfig(
                project_name="test_rag",
                enable_ai_agent=True,
                rag_features=RAGFeatures(enable_rag=True),
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=True,
                enable_docker=False,
            )

    def test_rag_with_google_drive_requires_oauth_google(self) -> None:
        """Test that Google Drive ingestion requires OAuth Provider to be Google."""
        with pytest.raises(ValidationError, match="Google Drive ingestion requires OAuth Provider"):
            ProjectConfig(
                project_name="test_rag",
                rag_features=RAGFeatures(
                    enable_rag=True,
                    enable_google_drive_ingestion=True,
                ),
                oauth_provider=OAuthProvider.NONE,
                enable_ai_agent=True,
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=True,
                enable_docker=True,
            )

    def test_rag_valid_with_all_requirements(self) -> None:
        """Test that RAG is valid when all requirements are met."""
        config = ProjectConfig(
            project_name="test_rag",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert config.rag_features.enable_rag is True


class TestEmbeddingProviderAutoDerivation:
    """Tests for automatic embedding provider derivation based on LLM provider."""

    def test_anthropic_derives_voyage_embeddings(self) -> None:
        """Test that Anthropic LLM provider derives Voyage embeddings."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.ANTHROPIC,
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert (
            config.to_cookiecutter_context()["embedding_provider"] == EmbeddingProviderType.VOYAGE
        )
        # assert config.embedd. == EmbeddingProviderType.VOYAGE

    def test_openrouter_derives_sentence_transformers(self) -> None:
        """Test that OpenRouter LLM provider derives Sentence Transformers embeddings."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert (
            config.to_cookiecutter_context()["embedding_provider"]
            == EmbeddingProviderType.SENTENCE_TRANSFORMERS
        )

    def test_openai_derives_openai_embeddings(self) -> None:
        """Test that OpenAI LLM provider derives OpenAI embeddings."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENAI,
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert (
            config.to_cookiecutter_context()["embedding_provider"] == EmbeddingProviderType.OPENAI
        )


class TestRerankerAutoDerivation:
    """Tests for automatic reranker type derivation based on LLM provider."""

    def test_openrouter_derives_cross_encoder_reranker(self) -> None:
        """Test that OpenRouter LLM provider derives Cross Encoder reranker."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert config.to_cookiecutter_context()["use_cross_encoder_reranker"]

    def test_openai_derives_cohere_reranker(self) -> None:
        """Test that OpenAI LLM provider derives Cohere reranker."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENAI,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert config.to_cookiecutter_context()["use_cohere_reranker"]

    def test_anthropic_derives_cohere_reranker(self) -> None:
        """Test that Anthropic LLM provider derives Cohere reranker."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.ANTHROPIC,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        assert config.to_cookiecutter_context()["use_cohere_reranker"]


class TestRAGCookiecutterContext:
    """Tests for RAG-related cookiecutter context generation."""

    def test_rag_enabled_context_flags(self) -> None:
        """Test RAG enabled sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["enable_rag"] is True
        assert context["use_milvus"] is True
        assert context["embedding_provider"] == "openai"
        assert context["use_openai_embeddings"] is True
        assert context["use_voyage_embeddings"] is False
        assert context["use_sentence_transformers"] is False

    def test_rag_disabled_context_flags(self) -> None:
        """Test RAG disabled sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            rag_features=RAGFeatures(enable_rag=False),
        )
        context = config.to_cookiecutter_context()

        assert context["enable_rag"] is False
        assert context["use_milvus"] is False
        assert context["embedding_provider"] == "openai"
        assert context["use_openai_embeddings"] is False
        assert context["use_voyage_embeddings"] is False
        assert context["use_sentence_transformers"] is False

    def test_voyage_embeddings_context_flags(self) -> None:
        """Test Voyage embeddings sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.ANTHROPIC,  # Derives Voyage embeddings
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["use_voyage_embeddings"] is True
        assert context["use_openai_embeddings"] is False
        assert context["use_sentence_transformers"] is False

    def test_sentence_transformers_context_flags(self) -> None:
        """Test Sentence Transformers embeddings sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,  # Derives Sentence Transformers
            rag_features=RAGFeatures(enable_rag=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["use_sentence_transformers"] is True
        assert context["use_openai_embeddings"] is False
        assert context["use_voyage_embeddings"] is False

    def test_reranker_enabled_context_flags(self) -> None:
        """Test reranker enabled sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["enable_reranker"] is True
        assert context["use_cohere_reranker"] is True
        assert context["use_cross_encoder_reranker"] is False

    def test_reranker_disabled_context_flags(self) -> None:
        """Test reranker disabled sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=False),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["enable_reranker"] is False
        assert context["use_cohere_reranker"] is False
        assert context["use_cross_encoder_reranker"] is False

    def test_cross_encoder_reranker_context_flags(self) -> None:
        """Test Cross Encoder reranker sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            llm_provider=LLMProviderType.OPENROUTER,  # Derives Cross Encoder
            rag_features=RAGFeatures(enable_rag=True, enable_reranker=True),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["use_cross_encoder_reranker"] is True
        assert context["use_cohere_reranker"] is False

    def test_llamaparse_document_parser_context_flags(self) -> None:
        """Test LlamaParse document parser sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, pdf_parser=PdfParserType.LLAMAPARSE),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["pdf_parser"] == "llamaparse"
        assert context["use_llamaparse"] is True
        assert context["use_pdfplumber"] is False
        assert context["use_python_parser"] is True  # Always True for non-PDF

    def test_pdfplumber_document_parser_context_flags(self) -> None:
        """Test pdfplumber document parser sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True),
            pdf_parser=PdfParserType.PDFPLUMBER,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["pdf_parser"] == "pdfplumber"
        assert context["use_llamaparse"] is False
        assert context["use_pdfplumber"] is True
        assert context["use_python_parser"] is True  # Always True for non-PDF

    def test_google_drive_ingestion_context_flags(self) -> None:
        """Test Google Drive ingestion sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, enable_google_drive_ingestion=True),
            oauth_provider=OAuthProvider.GOOGLE,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["enable_google_drive_ingestion"] is True

    def test_google_drive_ingestion_disabled_context_flags(self) -> None:
        """Test Google Drive ingestion disabled sets correct context flags."""
        config = ProjectConfig(
            project_name="test",
            enable_ai_agent=True,
            rag_features=RAGFeatures(enable_rag=True, enable_google_drive_ingestion=False),
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            enable_docker=True,
        )
        context = config.to_cookiecutter_context()

        assert context["enable_google_drive_ingestion"] is False


class TestRAGFeaturesModel:
    """Tests for RAGFeatures model."""

    def test_rag_features_default_values(self) -> None:
        """Test RAGFeatures default values."""
        features = RAGFeatures()
        assert features.enable_rag is False
        assert features.enable_google_drive_ingestion is False
        assert features.enable_reranker is False
        assert features.vector_store == VectorStoreType.MILVUS

    def test_rag_features_custom_values(self) -> None:
        """Test RAGFeatures with custom values."""
        features = RAGFeatures(
            enable_rag=True,
            enable_google_drive_ingestion=True,
            enable_reranker=True,
            vector_store=VectorStoreType.MILVUS,
        )
        assert features.enable_rag is True
        assert features.enable_google_drive_ingestion is True
        assert features.enable_reranker is True
        assert features.vector_store == VectorStoreType.MILVUS
