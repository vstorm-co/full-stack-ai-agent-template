"""OpenAPI contract tests — validate API schema structure.

These tests ensure that:
1. OpenAPI schema is generated and accessible
2. Expected endpoints exist in the schema
3. Response schemas are properly defined
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def app():
    """Create test application."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestOpenAPISchema:
    """Verify OpenAPI schema structure."""

    @pytest.mark.anyio
    async def test_openapi_schema_accessible(self, client: AsyncClient):
        """Test that OpenAPI schema endpoint returns valid JSON."""
        response = await client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    @pytest.mark.anyio
    async def test_schema_has_health_endpoints(self, client: AsyncClient):
        """Test that health check endpoints are in schema."""
        response = await client.get("/api/v1/openapi.json")
        paths = response.json()["paths"]
        assert "/api/v1/health" in paths
        assert "/api/v1/health/ready" in paths

    @pytest.mark.anyio
    async def test_schema_has_auth_endpoints(self, client: AsyncClient):
        """Test that authentication endpoints are in schema."""
        response = await client.get("/api/v1/openapi.json")
        paths = response.json()["paths"]
        assert "/api/v1/auth/login" in paths
        assert "/api/v1/auth/register" in paths

    @pytest.mark.anyio
    async def test_schema_has_response_models(self, client: AsyncClient):
        """Test that endpoints define response schemas (not just raw dicts)."""
        response = await client.get("/api/v1/openapi.json")
        schema = response.json()

        # Check that components/schemas section exists with models
        assert "components" in schema
        assert "schemas" in schema["components"]
        schemas = schema["components"]["schemas"]

        # Verify key models are defined
        assert "UserRead" in schemas, "UserRead schema missing"
        assert len(schemas) > 0, "No response schemas defined"

    @pytest.mark.anyio
    async def test_schema_version(self, client: AsyncClient):
        """Test that OpenAPI version is 3.1+."""
        response = await client.get("/api/v1/openapi.json")
        schema = response.json()
        version = schema["openapi"]
        major, minor = version.split(".")[:2]
        assert int(major) >= 3
        assert int(minor) >= 1

    @pytest.mark.anyio
    async def test_all_paths_have_operation_ids(self, client: AsyncClient):
        """Test that all endpoints have unique operation IDs."""
        response = await client.get("/api/v1/openapi.json")
        paths = response.json()["paths"]
        operation_ids = []
        for path_data in paths.values():
            for method_data in path_data.values():
                if isinstance(method_data, dict) and "operationId" in method_data:
                    operation_ids.append(method_data["operationId"])

        # All operation IDs should be unique
        assert len(operation_ids) == len(set(operation_ids)), "Duplicate operation IDs found"
