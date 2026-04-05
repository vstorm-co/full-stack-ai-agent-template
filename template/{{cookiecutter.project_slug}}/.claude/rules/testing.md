---
description: Testing standards, fixtures, async test patterns
globs: ["backend/tests/**/*.py", "tests/**/*.py", "**/test_*.py", "**/conftest.py"]
---

# Testing

## Running Tests

```bash
cd backend
uv run pytest                              # all tests
uv run pytest tests/test_file.py -v        # single file
uv run pytest -k "test_name" -v            # by name
uv run pytest --cov=app                    # with coverage
```

## Structure

- Mirror source layout: `app/services/user.py` → `tests/services/test_user.py`
- Shared fixtures in `tests/conftest.py`

## Naming

```python
# test_<action>_<scenario>_<expected_result>
def test_create_user_with_duplicate_email_raises_already_exists_error
def test_get_conversation_not_found_raises_not_found_error
def test_list_conversations_returns_only_user_owned
```

## Fixtures

```python
@pytest.fixture
def user_service(db: AsyncSession) -> UserService:
    return UserService(db)

@pytest.fixture
async def test_user(db: AsyncSession) -> User:
    return await user_repo.create(db, email="test@example.com", hashed_password="hashed")
```

## Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_get_user_by_id(user_service: UserService, test_user: User):
    result = await user_service.get_by_id(test_user.id)
    assert result.email == test_user.email
```

## API Tests

Use `httpx.AsyncClient`, not `TestClient`:

```python
@pytest.mark.asyncio
async def test_create_user(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/users",
        json={"email": "new@example.com", "password": "securepass123"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
```

## Exception Testing

```python
@pytest.mark.asyncio
async def test_get_user_not_found(user_service: UserService):
    with pytest.raises(NotFoundError):
        await user_service.get_by_id(UUID("00000000-0000-0000-0000-000000000000"))
```

## Rules

- Each test is independent — no shared mutable state
- Use plain `assert` (pytest rewrites for detailed output)
- One logical assertion per test (multiple asserts are fine if testing one behavior)
- Use factory fixtures for test data, not raw dicts
