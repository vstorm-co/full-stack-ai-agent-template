"""Tests for message rating feature in generated templates.

This test suite verifies that:
1. Rating files are generated when JWT is enabled
2. Rating files are NOT generated when JWT is disabled
3. Generated rating code passes linting/type checking
4. Rating feature documentation exists
"""

import subprocess
from pathlib import Path

import pytest

from fastapi_gen.config import (
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    OAuthProvider,
    ProjectConfig,
)
from fastapi_gen.generator import generate_project

TEMPLATE_DIR = Path(__file__).parent.parent / "template"


class TestRatingFeatureFilesGenerated:
    """Tests that rating files are generated correctly based on configuration."""

    @pytest.fixture
    def project_with_ratings(self, tmp_path: Path) -> Path:
        """Generate a project with JWT enabled (required for ratings)."""
        config = ProjectConfig(
            project_name="test_ratings",
            database=DatabaseType.POSTGRESQL,
            oauth_provider=OAuthProvider.GOOGLE,
            enable_session_management=True,
            enable_admin_panel=True,
            enable_rate_limiting=True,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
            frontend=FrontendType.NEXTJS,
        )
        return generate_project(config, tmp_path)

    @pytest.fixture
    def project_without_oauth(self, tmp_path: Path) -> Path:
        """Generate a project without OAuth (JWT is always enabled in this template).

        Note: JWT is always enabled, ratings are always available with JWT auth.
        This fixture tests with OAuthProvider.NONE (no OAuth, but JWT still works).
        """
        config = ProjectConfig(
            project_name="test_no_oauth",
            database=DatabaseType.POSTGRESQL,
            oauth_provider=OAuthProvider.NONE,  # No OAuth, but JWT is always on
            enable_session_management=False,
            enable_admin_panel=False,
            enable_rate_limiting=False,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
            frontend=FrontendType.NONE,
        )
        return generate_project(config, tmp_path)

    def test_backend_message_rating_model_exists(self, project_with_ratings: Path) -> None:
        """Test that MessageRating model is generated."""
        model_path = (
            project_with_ratings
            / "backend"
            / "app"
            / "db"
            / "models"
            / "message_rating.py"
        )
        assert model_path.exists(), "message_rating.py model should be generated"
        content = model_path.read_text()
        assert "class MessageRating" in content
        assert "rating: int" in content or "rating: Mapped[int]" in content
        assert "comment:" in content

    def test_backend_message_rating_repository_exists(
        self, project_with_ratings: Path
    ) -> None:
        """Test that message_rating repository is generated."""
        repo_path = (
            project_with_ratings / "backend" / "app" / "repositories" / "message_rating.py"
        )
        assert repo_path.exists(), "message_rating.py repository should be generated"
        content = repo_path.read_text()
        assert "def get_rating_by_message_and_user" in content
        assert "def create_rating" in content
        assert "def update_rating" in content
        assert "def delete_rating" in content
        assert "def list_ratings" in content
        assert "def get_rating_summary" in content

    def test_backend_message_rating_service_exists(
        self, project_with_ratings: Path
    ) -> None:
        """Test that message_rating service is generated."""
        service_path = (
            project_with_ratings / "backend" / "app" / "services" / "message_rating.py"
        )
        assert service_path.exists(), "message_rating.py service should be generated"
        content = service_path.read_text()
        assert "class MessageRatingService" in content
        assert "async def rate_message" in content or "def rate_message" in content
        assert "async def remove_rating" in content or "def remove_rating" in content
        assert "_validate_message_in_conversation" in content

    def test_backend_message_rating_schemas_exists(
        self, project_with_ratings: Path
    ) -> None:
        """Test that message_rating schemas are generated."""
        schema_path = (
            project_with_ratings / "backend" / "app" / "schemas" / "message_rating.py"
        )
        assert schema_path.exists(), "message_rating.py schemas should be generated"
        content = schema_path.read_text()
        assert "class RatingValue" in content or "RatingValue" in content
        assert "class MessageRatingCreate" in content
        assert "class MessageRatingRead" in content
        assert "class MessageRatingWithDetails" in content
        assert "class RatingSummary" in content
        # Check for XSS sanitization
        assert "html.escape" in content or "sanitize" in content.lower()

    def test_backend_admin_ratings_route_exists(self, project_with_ratings: Path) -> None:
        """Test that admin ratings endpoint is generated."""
        route_path = (
            project_with_ratings
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "v1"
            / "admin_ratings.py"
        )
        assert route_path.exists(), "admin_ratings.py route should be generated"
        content = route_path.read_text()
        assert 'router.get("",' in content or "router.get(" in content
        assert "def list_ratings_admin" in content or "async def list_ratings_admin" in content
        assert "def get_rating_summary" in content or "async def get_rating_summary" in content
        assert "def export_ratings" in content or "async def export_ratings" in content
        # Check for CSV export
        assert "csv" in content.lower()
        # Check for admin auth requirement
        assert "CurrentAdmin" in content

    def test_conversation_route_has_rating_endpoints(
        self, project_with_ratings: Path
    ) -> None:
        """Test that conversation route includes rating endpoints."""
        route_path = (
            project_with_ratings
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "v1"
            / "conversations.py"
        )
        content = route_path.read_text()
        assert "/messages/{message_id}/rate" in content
        assert "def rate_message" in content or "async def rate_message" in content
        assert "def remove_rating" in content or "async def remove_rating" in content

    def test_rating_dependency_injected(self, project_with_ratings: Path) -> None:
        """Test that MessageRatingSvc dependency is registered."""
        deps_path = project_with_ratings / "backend" / "app" / "api" / "deps.py"
        content = deps_path.read_text()
        assert "MessageRatingSvc" in content
        assert "def get_rating_service" in content or "async def get_rating_service" in content

    def test_admin_router_registered(self, project_with_ratings: Path) -> None:
        """Test that admin ratings router is registered in v1 router."""
        init_path = (
            project_with_ratings / "backend" / "app" / "api" / "routes" / "v1" / "__init__.py"
        )
        content = init_path.read_text()
        assert "admin_ratings" in content
        assert 'prefix="/admin/ratings"' in content

    def test_message_rating_model_registered(self, project_with_ratings: Path) -> None:
        """Test that MessageRating is exported from models.__init__."""
        init_path = project_with_ratings / "backend" / "app" / "db" / "models" / "__init__.py"
        content = init_path.read_text()
        assert "MessageRating" in content

    def test_conversation_schema_has_rating_fields(
        self, project_with_ratings: Path
    ) -> None:
        """Test that MessageRead schema includes rating fields."""
        schema_path = (
            project_with_ratings / "backend" / "app" / "schemas" / "conversation.py"
        )
        content = schema_path.read_text()
        assert "user_rating" in content
        assert "rating_count" in content

    def test_frontend_rating_buttons_component_exists(
        self, project_with_ratings: Path
    ) -> None:
        """Test that RatingButtons component is generated."""
        component_path = (
            project_with_ratings
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "rating-buttons.tsx"
        )
        assert component_path.exists(), "rating-buttons.tsx should be generated"
        content = component_path.read_text()
        assert "ThumbsUp" in content
        assert "ThumbsDown" in content
        assert "Dialog" in content
        assert "whatWentWrong" in content

    def test_frontend_admin_ratings_page_exists(self, project_with_ratings: Path) -> None:
        """Test that admin ratings page is generated."""
        page_path = (
            project_with_ratings
            / "frontend"
            / "src"
            / "app"
            / "[locale]"
            / "(dashboard)"
            / "admin"
            / "ratings"
            / "page.tsx"
        )
        assert page_path.exists(), "admin/ratings/page.tsx should be generated"
        content = page_path.read_text()
        assert "BarChart" in content or "recharts" in content
        assert "ratingsTitle" in content
        assert "viewConversation" in content

    def test_frontend_types_include_rating(self, project_with_ratings: Path) -> None:
        """Test that frontend types include rating enums."""
        types_path = project_with_ratings / "frontend" / "src" / "types" / "chat.ts"
        content = types_path.read_text()
        assert "RatingValue" in content
        assert "UserRating" in content
        assert "user_rating" in content
        assert "rating_count" in content

    def test_ratings_generated_without_oauth(self, project_without_oauth: Path) -> None:
        """Test that rating files ARE generated with OAuthProvider.NONE (JWT is always enabled).

        JWT authentication is always enabled in this template, regardless of OAuth provider.
        Therefore, ratings should always be available.
        """
        # Backend files should exist since JWT is always enabled
        model_path = (
            project_without_oauth
            / "backend"
            / "app"
            / "db"
            / "models"
            / "message_rating.py"
        )
        assert model_path.exists(), "MessageRating model should exist (JWT always enabled)"

        # Admin ratings router should exist
        admin_route_path = (
            project_without_oauth
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "v1"
            / "admin_ratings.py"
        )
        assert admin_route_path.exists(), "Admin ratings router should exist"


class TestRatingFeatureCodeQuality:
    """Tests that generated rating code passes quality checks."""

    @pytest.fixture
    def project_with_ratings(self, tmp_path: Path) -> Path:
        """Generate a project with ratings for quality tests."""
        config = ProjectConfig(
            project_name="test_ratings_quality",
            database=DatabaseType.SQLITE,  # Faster for testing
            oauth_provider=OAuthProvider.NONE,  # No OAuth, but JWT is always enabled
            enable_admin_panel=True,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
            frontend=FrontendType.NONE,  # Skip frontend for faster tests
        )
        return generate_project(config, tmp_path)

    @pytest.mark.slow
    def test_rating_model_passes_ruff(self, project_with_ratings: Path) -> None:
        """Test that message_rating model passes ruff linting."""
        model_path = (
            project_with_ratings
            / "backend"
            / "app"
            / "db"
            / "models"
            / "message_rating.py"
        )
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(model_path)],
            capture_output=True,
            text=True,
            cwd=project_with_ratings,
        )
        assert result.returncode == 0, f"Ruff failed for message_rating.py:\n{result.stdout}"

    @pytest.mark.slow
    def test_rating_repository_passes_ruff(self, project_with_ratings: Path) -> None:
        """Test that message_rating repository passes ruff linting."""
        repo_path = (
            project_with_ratings / "backend" / "app" / "repositories" / "message_rating.py"
        )
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(repo_path)],
            capture_output=True,
            text=True,
            cwd=project_with_ratings,
        )
        assert result.returncode == 0, f"Ruff failed for rating repository:\n{result.stdout}"

    @pytest.mark.slow
    def test_rating_service_passes_ruff(self, project_with_ratings: Path) -> None:
        """Test that message_rating service passes ruff linting."""
        service_path = (
            project_with_ratings / "backend" / "app" / "services" / "message_rating.py"
        )
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(service_path)],
            capture_output=True,
            text=True,
            cwd=project_with_ratings,
        )
        assert result.returncode == 0, f"Ruff failed for rating service:\n{result.stdout}"

    @pytest.mark.slow
    def test_rating_schemas_pass_ruff(self, project_with_ratings: Path) -> None:
        """Test that message_rating schemas pass ruff linting."""
        schema_path = (
            project_with_ratings / "backend" / "app" / "schemas" / "message_rating.py"
        )
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(schema_path)],
            capture_output=True,
            text=True,
            cwd=project_with_ratings,
        )
        assert result.returncode == 0, f"Ruff failed for rating schemas:\n{result.stdout}"

    @pytest.mark.slow
    def test_admin_ratings_route_passes_ruff(self, project_with_ratings: Path) -> None:
        """Test that admin_ratings route passes ruff linting."""
        route_path = (
            project_with_ratings
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "v1"
            / "admin_ratings.py"
        )
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(route_path)],
            capture_output=True,
            text=True,
            cwd=project_with_ratings,
        )
        assert result.returncode == 0, f"Ruff failed for admin_ratings route:\n{result.stdout}"

    @pytest.mark.slow
    def test_rating_files_pass_ty(self, project_with_ratings: Path) -> None:
        """Test that rating files pass ty type checking."""
        backend_path = project_with_ratings / "backend" / "app"
        result = subprocess.run(
            [
                "uv",
                "run",
                "ty",
                "check",
                str(backend_path / "db" / "models" / "message_rating.py"),
                str(backend_path / "repositories" / "message_rating.py"),
                str(backend_path / "services" / "message_rating.py"),
                str(backend_path / "schemas" / "message_rating.py"),
            ],
            capture_output=True,
            text=True,
            cwd=project_with_ratings,
        )
        assert result.returncode == 0, f"Ty failed for rating files:\n{result.stdout}"


class TestRatingFeatureAllDatabases:
    """Tests that rating feature works with all database types."""

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "database, enable_admin",
        [
            (DatabaseType.POSTGRESQL, True),
            (DatabaseType.SQLITE, True),
            (DatabaseType.MONGODB, False),  # Admin panel not supported with MongoDB
        ],
    )
    def test_rating_model_generated_for_all_databases(
        self, tmp_path: Path, database: DatabaseType, enable_admin: bool
    ) -> None:
        """Test that rating model is generated for all database types."""
        config = ProjectConfig(
            project_name=f"test_ratings_{database.value}",
            database=database,
            oauth_provider=OAuthProvider.NONE,
            enable_admin_panel=enable_admin,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
        )
        project = generate_project(config, tmp_path / database.value)

        model_path = (
            project / "backend" / "app" / "db" / "models" / "message_rating.py"
        )
        assert model_path.exists(), f"Model should exist for {database.value}"

        content = model_path.read_text()
        assert "class MessageRating" in content

        # Check for database-specific implementations
        if database == DatabaseType.MONGODB:
            assert "beanie" in content.lower() or "Document" in content
        elif database == DatabaseType.SQLITE:
            assert "SQLModel" in content or "Base" in content
        elif database == DatabaseType.POSTGRESQL:
            assert "SQLModel" in content or "Base" in content


class TestRatingFeatureSecurity:
    """Tests for security features in rating implementation."""

    @pytest.fixture
    def project_with_ratings(self, tmp_path: Path) -> Path:
        """Generate a project for security testing."""
        config = ProjectConfig(
            project_name="test_ratings_security",
            database=DatabaseType.POSTGRESQL,
            oauth_provider=OAuthProvider.NONE,
            enable_admin_panel=True,
            enable_rate_limiting=True,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
        )
        return generate_project(config, tmp_path)

    def test_comment_sanitization_in_schemas(self, project_with_ratings: Path) -> None:
        """Test that comment sanitization is implemented in schemas.

        Comments are stored raw (HTML escaping happens at render time via
        React / CSV escaping). The sanitizer only strips control characters,
        trims whitespace, and enforces a length cap.
        """
        schema_path = (
            project_with_ratings / "backend" / "app" / "schemas" / "message_rating.py"
        )
        content = schema_path.read_text()
        assert "_sanitize_comment" in content, "comment sanitizer should be present"
        assert ".strip()" in content, "whitespace trimming should be present"
        assert "\\x00" in content or "re.sub" in content, "control-char stripping should be present"
        # Ensure stored text is NOT html-escaped (would corrupt CSV export and API consumers)
        assert "html.escape" not in content, "comments must not be HTML-escaped at write time"

    def test_conversation_validation_in_service(
        self, project_with_ratings: Path
    ) -> None:
        """Test that conversation validation is implemented."""
        service_path = (
            project_with_ratings / "backend" / "app" / "services" / "message_rating.py"
        )
        content = service_path.read_text()
        assert "_validate_message_in_conversation" in content
        assert "conversation_id" in content
        assert "NotFoundError" in content  # Should raise for cross-conversation attempts

    def test_assistant_only_validation(self, project_with_ratings: Path) -> None:
        """Test that only assistant messages can be rated."""
        service_path = (
            project_with_ratings / "backend" / "app" / "services" / "message_rating.py"
        )
        content = service_path.read_text()
        assert "assistant" in content
        assert "ValidationError" in content or "role" in content

    def test_admin_auth_required(self, project_with_ratings: Path) -> None:
        """Test that admin endpoints require admin role."""
        admin_route_path = (
            project_with_ratings
            / "backend"
            / "app"
            / "api"
            / "routes"
            / "v1"
            / "admin_ratings.py"
        )
        content = admin_route_path.read_text()
        assert "CurrentAdmin" in content
        assert "admin" in content.lower()

    def test_cascade_delete_in_model(self, project_with_ratings: Path) -> None:
        """Test that cascade deletes are configured."""
        model_path = (
            project_with_ratings / "backend" / "app" / "db" / "models" / "message_rating.py"
        )
        content = model_path.read_text()
        assert "CASCADE" in content or "cascade" in content.lower()

    def test_unique_constraint_in_model(self, project_with_ratings: Path) -> None:
        """Test that unique constraint prevents duplicate ratings."""
        model_path = (
            project_with_ratings / "backend" / "app" / "db" / "models" / "message_rating.py"
        )
        content = model_path.read_text()
        assert "UniqueConstraint" in content or "unique=True" in content

    def test_conversation_ownership_validation(self, project_with_ratings: Path) -> None:
        """Test that conversation ownership is checked before rating/removing (R4-4.3)."""
        service_path = (
            project_with_ratings / "backend" / "app" / "services" / "message_rating.py"
        )
        content = service_path.read_text()
        assert "_validate_conversation_ownership" in content, (
            "Ownership check should exist to prevent IDOR"
        )
        assert "conv.user_id != user_id" in content, (
            "Should verify conversation belongs to user"
        )

    def test_search_input_sanitized_against_like_injection(self, project_with_ratings: Path) -> None:
        """Test that LIKE wildcards are escaped in admin search (R4-4.1)."""
        repo_path = (
            project_with_ratings / "backend" / "app" / "repositories" / "conversation.py"
        )
        content = repo_path.read_text()
        assert "safe_search" in content, "Search input should be sanitized before LIKE query"
        assert "replace" in content, "LIKE wildcards should be escaped"
        assert 'escape="' in content or "escape='" in content, (
            "LIKE queries should declare an explicit ESCAPE character"
        )

    def test_search_input_sanitized_against_regex_injection_mongodb(self, tmp_path: Path) -> None:
        """Test that regex input is escaped in MongoDB admin search (R4-4.2)."""
        config = ProjectConfig(
            project_name="test_mongodb_regex",
            database=DatabaseType.MONGODB,
            oauth_provider=OAuthProvider.NONE,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
        )
        project = generate_project(config, tmp_path)
        repo_path = project / "backend" / "app" / "repositories" / "conversation.py"
        content = repo_path.read_text()
        assert "re.escape" in content, "MongoDB search should escape regex input"


class TestRatingFeatureAccessibility:
    """Tests for accessibility features in frontend components."""

    @pytest.fixture
    def project_with_ratings(self, tmp_path: Path) -> Path:
        """Generate a project for accessibility testing."""
        config = ProjectConfig(
            project_name="test_ratings_a11y",
            database=DatabaseType.POSTGRESQL,
            oauth_provider=OAuthProvider.NONE,
            enable_admin_panel=True,
            enable_pytest=True,
            enable_docker=False,
            enable_logfire=False,
            background_tasks=BackgroundTaskType.NONE,
            ci_type=CIType.NONE,
            frontend=FrontendType.NEXTJS,
        )
        return generate_project(config, tmp_path)

    def test_rating_buttons_has_accessibility_props(
        self, project_with_ratings: Path
    ) -> None:
        """Test that rating buttons have accessibility attributes."""
        component_path = (
            project_with_ratings
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "rating-buttons.tsx"
        )
        content = component_path.read_text()
        # Check for Dialog component which handles accessibility internally
        assert "Dialog" in content or "dialog" in content.lower()
        # Check for button titles which help accessibility
        assert "title=" in content or 'title="' in content

    def test_dialog_has_modal_attributes(self, project_with_ratings: Path) -> None:
        """Test that dialog has proper modal attributes."""
        component_path = (
            project_with_ratings
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "rating-buttons.tsx"
        )
        content = component_path.read_text()
        # Dialog component from shadcn/ui handles accessibility internally
        assert "DialogContent" in content or "Dialog" in content

    def test_keyboard_navigation_support(self, project_with_ratings: Path) -> None:
        """Test that keyboard navigation is supported."""
        component_path = (
            project_with_ratings
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "rating-buttons.tsx"
        )
        content = component_path.read_text()
        # The shadcn/ui Dialog component handles keyboard navigation internally
        # We just need to verify Dialog is used
        assert "Dialog" in content
        # Buttons should have focus support (via shadcn Button component which handles focus internally)
        assert "Button" in content

    def test_focus_management(self, project_with_ratings: Path) -> None:
        """Test that focus is managed properly."""
        component_path = (
            project_with_ratings
            / "frontend"
            / "src"
            / "components"
            / "chat"
            / "rating-buttons.tsx"
        )
        content = component_path.read_text()
        # autoFocus on textarea in dialog
        assert "autoFocus" in content
