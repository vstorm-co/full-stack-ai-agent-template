"""Integration tests for RAG-enabled project generation.

These tests generate projects with RAG configuration and verify
the correct files and settings are created.
"""

import re
from pathlib import Path

import pytest

from fastapi_gen.config import (
    AIFrameworkType,
    BackgroundTaskType,
    DatabaseType,
    EmbeddingProviderType,
    LLMProviderType,
    PdfParserType,
    ProjectConfig,
    RAGFeatures,
    RerankerType,
)
from fastapi_gen.generator import generate_project


class TestRAGProjectGeneration:
    """Integration tests for RAG project generation."""

    @pytest.fixture
    def rag_project_celery(self, tmp_path: Path) -> Path:
        """Generate a RAG project with Celery."""
        config = ProjectConfig(
            project_name="rag_celery",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    @pytest.fixture
    def rag_project_taskiq(self, tmp_path: Path) -> Path:
        """Generate a RAG project with TaskIQ."""
        config = ProjectConfig(
            project_name="rag_taskiq",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.TASKIQ,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    @pytest.fixture
    def rag_project_arq(self, tmp_path: Path) -> Path:
        """Generate a RAG project with ARQ."""
        config = ProjectConfig(
            project_name="rag_arq",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.ARQ,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)


class TestRAGFilesExist:
    """Tests that RAG files are created when RAG is enabled."""

    @pytest.fixture
    def rag_project(self, tmp_path: Path) -> Path:
        """Generate a RAG project with Celery."""
        config = ProjectConfig(
            project_name="rag_files_test",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    def test_rag_config_exists(self, rag_project) -> None:
        """Test that rag/config.py exists."""
        rag_config = rag_project / "backend" / "app" / "services" / "rag" / "config.py"
        assert rag_config.exists(), "rag/config.py should exist when RAG is enabled"

    def test_rag_documents_exists(self, rag_project) -> None:
        """Test that rag/documents.py exists."""
        rag_docs = rag_project / "backend" / "app" / "services" / "rag" / "documents.py"
        assert rag_docs.exists(), "rag/documents.py should exist when RAG is enabled"

    def test_rag_embeddings_exists(self, rag_project) -> None:
        """Test that rag/embeddings.py exists."""
        rag_embeddings = rag_project / "backend" / "app" / "services" / "rag" / "embeddings.py"
        assert rag_embeddings.exists(), "rag/embeddings.py should exist when RAG is enabled"

    def test_rag_ingestion_exists(self, rag_project) -> None:
        """Test that rag/ingestion.py exists."""
        rag_ingestion = rag_project / "backend" / "app" / "services" / "rag" / "ingestion.py"
        assert rag_ingestion.exists(), "rag/ingestion.py should exist when RAG is enabled"

    def test_rag_retrieval_exists(self, rag_project) -> None:
        """Test that rag/retrieval.py exists."""
        rag_retrieval = rag_project / "backend" / "app" / "services" / "rag" / "retrieval.py"
        assert rag_retrieval.exists(), "rag/retrieval.py should exist when RAG is enabled"

    def test_rag_vectorstore_exists(self, rag_project) -> None:
        """Test that rag/vectorstore.py exists."""
        rag_vectorstore = rag_project / "backend" / "app" / "services" / "rag" / "vectorstore.py"
        assert rag_vectorstore.exists(), "rag/vectorstore.py should exist when RAG is enabled"

    def test_rag_api_route_exists(self, rag_project) -> None:
        """Test that rag API route exists."""
        rag_api = rag_project / "backend" / "app" / "api" / "routes" / "v1" / "rag.py"
        assert rag_api.exists(), "rag.py API route should exist when RAG is enabled"

    def test_rag_tool_exists(self, rag_project) -> None:
        """Test that rag_tool.py exists in agents."""
        rag_tool = rag_project / "backend" / "app" / "agents" / "tools" / "rag_tool.py"
        assert rag_tool.exists(), "rag_tool.py should exist when RAG is enabled"

    def test_docker_compose_has_milvus(self, rag_project) -> None:
        """Test that docker-compose.yml has Milvus service."""
        docker_compose = rag_project / "docker-compose.yml"
        content = docker_compose.read_text()
        # Use regex to match YAML service definition (with possible leading whitespace)
        assert re.search(r"^\s*milvus:", content, re.MULTILINE), (
            "docker-compose.yml should have milvus service"
        )


class TestNonRAGProjectNoRAGFiles:
    """Tests that RAG files are NOT created when RAG is disabled."""

    @pytest.fixture
    def non_rag_project(self, tmp_path: Path) -> Path:
        """Generate a non-RAG project."""
        config = ProjectConfig(
            project_name="no_rag_project",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=False),
            enable_docker=True,
        )
        return generate_project(config, tmp_path)

    def test_rag_folder_not_exists(self, non_rag_project) -> None:
        """Test that rag/ folder does not exist."""
        rag_dir = non_rag_project / "backend" / "app" / "services" / "rag"
        assert not rag_dir.exists(), "rag/ folder should not exist when RAG is disabled"

    def test_rag_api_not_exists(self, non_rag_project) -> None:
        """Test that rag API route does not exist."""
        rag_api = non_rag_project / "backend" / "app" / "api" / "routes" / "v1" / "rag.py"
        assert not rag_api.exists(), "rag.py should not exist when RAG is disabled"


class TestRAGWithAIFrameworks:
    """Tests for RAG with different AI frameworks."""

    @pytest.mark.parametrize(
        "framework",
        [
            AIFrameworkType.PYDANTIC_AI,
            AIFrameworkType.LANGCHAIN,
            AIFrameworkType.LANGGRAPH,
            AIFrameworkType.DEEPAGENTS,
            AIFrameworkType.PYDANTIC_DEEP,
        ],
    )
    def test_rag_with_ai_framework(self, tmp_path, framework) -> None:
        """Test that RAG works with all AI frameworks."""
        # LangChain/LangGraph/DeepAgents don't support OpenRouter
        llm_provider = LLMProviderType.OPENAI
        if framework in (
            AIFrameworkType.LANGCHAIN,
            AIFrameworkType.LANGGRAPH,
            AIFrameworkType.DEEPAGENTS,
        ):
            llm_provider = LLMProviderType.OPENAI

        config = ProjectConfig(
            project_name=f"rag_{framework.value}",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            ai_framework=framework,
            llm_provider=llm_provider,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        # Verify RAG files exist
        rag_dir = project / "backend" / "app" / "services" / "rag"
        assert rag_dir.exists(), f"RAG should be enabled with {framework.value}"


class TestRAGWithEmbeddingProviders:
    """Tests for RAG with different embedding providers."""

    def test_rag_with_openai_embeddings(self, tmp_path) -> None:
        """Test RAG with OpenAI embeddings."""
        config = ProjectConfig(
            project_name="rag_openai_emb",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            llm_provider=LLMProviderType.OPENAI,
            rag_features=RAGFeatures(enable_rag=True),
            embedding_provider=EmbeddingProviderType.OPENAI,
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        # Verify config has correct embedding settings
        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "text-embedding-3-small" in content or "embedding-3" in content

    def test_rag_with_voyage_embeddings(self, tmp_path) -> None:
        """Test RAG with Voyage embeddings (auto-derived from Anthropic)."""
        config = ProjectConfig(
            project_name="rag_voyage_emb",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            llm_provider=LLMProviderType.ANTHROPIC,  # Derives Voyage
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        # Verify config has Voyage settings
        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "voyage" in content.lower()

    def test_rag_with_sentence_transformers(self, tmp_path) -> None:
        """Test RAG with SentenceTransformers (auto-derived from OpenRouter)."""
        config = ProjectConfig(
            project_name="rag_st_emb",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            llm_provider=LLMProviderType.OPENROUTER,  # Derives SentenceTransformers
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        # Verify config has SentenceTransformers settings
        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "sentence" in content.lower() or "all-MiniLM" in content


class TestRAGWithRerankers:
    """Tests for RAG with different reranker options."""

    def test_rag_no_reranker(self, tmp_path) -> None:
        """Test RAG without reranker."""
        config = ProjectConfig(
            project_name="rag_no_rerank",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        # Should not have reranker config
        assert "RerankerConfig" not in content

        # When reranker is disabled, main.py should NOT have reranker warmup
        main_file = project / "backend" / "app" / "main.py"
        main_content = main_file.read_text()
        assert "rerank_service.warmup()" not in main_content

        # The reranker is optional, so RerankService might not be imported
        # but the warmup shouldn't be there
        assert "rerank_service.warmup()" not in main_content

    def test_rag_with_cohere_reranker(self, tmp_path) -> None:
        """Test RAG with Cohere reranker."""
        config = ProjectConfig(
            project_name="rag_cohere_rerank",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True, reranker_type=RerankerType.COHERE),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "cohere" in content.lower() or "reranker" in content.lower()

        # reranker.py should exist
        reranker_file = project / "backend" / "app" / "services" / "rag" / "reranker.py"
        assert reranker_file.exists(), "reranker.py should exist when reranker is enabled"
        reranker_content = reranker_file.read_text()
        assert "CohereReranker" in reranker_content

        # retrieval.py should have reranking logic
        retrieval_file = project / "backend" / "app" / "services" / "rag" / "retrieval.py"
        retrieval_content = retrieval_file.read_text()
        assert "use_reranker" in retrieval_content
        assert "rerank_service" in retrieval_content

        # deps.py should have reranker service
        deps_file = project / "backend" / "app" / "api" / "deps.py"
        deps_content = deps_file.read_text()
        assert "RerankService" in deps_content

        # main.py should have reranker warmup
        main_file = project / "backend" / "app" / "main.py"
        main_content = main_file.read_text()
        assert "rerank_service.warmup()" in main_content

        # rag.py API should have use_reranker parameter
        rag_api_file = project / "backend" / "app" / "api" / "routes" / "v1" / "rag.py"
        rag_api_content = rag_api_file.read_text()
        assert "use_reranker" in rag_api_content

    def test_rag_with_cross_encoder_reranker(self, tmp_path) -> None:
        """Test RAG with CrossEncoder reranker."""
        config = ProjectConfig(
            project_name="rag_ce_rerank",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            llm_provider=LLMProviderType.OPENROUTER,
            rag_features=RAGFeatures(enable_rag=True, reranker_type=RerankerType.CROSS_ENCODER),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "cross" in content.lower() or "reranker" in content.lower()

        # reranker.py should exist
        reranker_file = project / "backend" / "app" / "services" / "rag" / "reranker.py"
        assert reranker_file.exists(), "reranker.py should exist when reranker is enabled"
        reranker_content = reranker_file.read_text()
        assert "CrossEncoderReranker" in reranker_content
        assert "CROSS_ENCODER_MODEL" in reranker_content

        # retrieval.py should have reranking logic
        retrieval_file = project / "backend" / "app" / "services" / "rag" / "retrieval.py"
        retrieval_content = retrieval_file.read_text()
        assert "use_reranker" in retrieval_content

        # main.py should have reranker warmup
        main_file = project / "backend" / "app" / "main.py"
        main_content = main_file.read_text()
        assert "rerank_service.warmup()" in main_content


class TestRAGWithPDFParsers:
    """Tests for RAG with different PDF parsers."""

    def test_rag_with_pymupdf(self, tmp_path) -> None:
        """Test RAG with PyMuPDF parser."""
        config = ProjectConfig(
            project_name="rag_pymupdf",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            pdf_parser=PdfParserType.PYMUPDF,
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "pymupdf" in content.lower()

    def test_rag_with_llamaparse(self, tmp_path) -> None:
        """Test RAG with LlamaParse parser."""
        config = ProjectConfig(
            project_name="rag_llamaparse",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True, pdf_parser=PdfParserType.LLAMAPARSE),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_config = project / "backend" / "app" / "services" / "rag" / "config.py"
        content = rag_config.read_text()
        assert "llamaparse" in content.lower()


class TestRAGCodePatterns:
    """Tests for verifying code patterns in generated RAG files."""

    def test_rag_api_uses_list_collections_method(self, tmp_path: Path) -> None:
        """Test that rag API uses list_collections() method instead of client.list_collections()."""
        import re

        config = ProjectConfig(
            project_name="test_rag_patterns",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_api = project / "backend" / "app" / "api" / "routes" / "v1" / "rag.py"
        content = rag_api.read_text()

        # Should use list_collections() method on vector_store
        assert re.search(r"await\s+vector_store\.list_collections\(\)", content), (
            "rag.py should use vector_store.list_collections() method"
        )

        # Should NOT directly access client.list_collections()
        assert not re.search(r"vector_store\.client\.list_collections\(\)", content), (
            "rag.py should NOT directly access vector_store.client.list_collections()"
        )

    def test_rag_tool_uses_singleton(self, tmp_path: Path) -> None:
        """Test that rag_tool.py uses singleton pattern for retrieval service."""
        import re

        config = ProjectConfig(
            project_name="test_rag_cache",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        rag_tool = project / "backend" / "app" / "agents" / "tools" / "rag_tool.py"
        content = rag_tool.read_text()

        # Should use singleton pattern (global variable)
        assert re.search(r"_retrieval_service", content), "rag_tool.py should use singleton pattern"

        # Should have get_retrieval_service function
        assert re.search(r"def get_retrieval_service", content), "rag_tool.py should have get_retrieval_service function"

    def test_rag_vectorstore_has_list_collections_method(self, tmp_path: Path) -> None:
        """Test that vectorstore.py has list_collections method in both base and milvus classes."""
        import re

        config = ProjectConfig(
            project_name="test_rag_vec",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.CELERY,
            enable_redis=True,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        project = generate_project(config, tmp_path)

        vectorstore = project / "backend" / "app" / "services" / "rag" / "vectorstore.py"
        content = vectorstore.read_text()

        # BaseVectorStore should have abstract list_collections
        assert re.search(r"async def list_collections\(self\)", content), (
            "BaseVectorStore should have list_collections method"
        )

        # MilvusVectorStore should implement list_collections
        assert re.search(r"class MilvusVectorStore.*list_collections", content, re.DOTALL), (
            "MilvusVectorStore should implement list_collections method"
        )

    def test_rag_works_without_background_tasks(self) -> None:
        """Test that RAG works without background tasks (uses FastAPI BackgroundTasks)."""
        config = ProjectConfig(
            project_name="rag_no_bg",
            database=DatabaseType.POSTGRESQL,
            background_tasks=BackgroundTaskType.NONE,
            enable_redis=False,
            rag_features=RAGFeatures(enable_rag=True),
            enable_docker=True,
        )
        assert config.rag_features.enable_rag is True
        assert config.background_tasks == BackgroundTaskType.NONE

    def test_rag_requires_docker(self) -> None:
        """Test that RAG requires Docker."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="requires Docker"):
            ProjectConfig(
                project_name="rag_no_docker",
                database=DatabaseType.POSTGRESQL,
                background_tasks=BackgroundTaskType.CELERY,
                enable_redis=True,
                rag_features=RAGFeatures(enable_rag=True),
                enable_docker=False,
            )
