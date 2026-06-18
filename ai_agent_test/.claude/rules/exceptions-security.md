---
description: Exception handling patterns and security conventions
globs: ["backend/app/core/**/*.py", "backend/app/services/**/*.py"]
---

# Exceptions & Security

## Domain Exceptions (`app/core/exceptions.py`)

All extend `AppException`. Always pass `message` and `details`:

```python
raise NotFoundError(message="User not found", details={"user_id": str(user_id)})
raise AlreadyExistsError(message="Email already registered", details={"email": email})
raise AuthenticationError(message="Invalid or expired token")
raise AuthorizationError(message="Role 'admin' required for this action")
```

Exception handlers in `api/exception_handlers.py` automatically:
- Map to HTTP status codes
- Log with structured context (path, method, error code)
- Return consistent JSON error format
- Add `WWW-Authenticate: Bearer` header on 401

## Security Patterns

JWT auth (`core/security.py`):
- `create_access_token(subject)` / `create_refresh_token(subject)` — encode with `jwt.encode()`
- `verify_token(token)` → `dict | None` — decode with `jwt.decode()`
- Token payload: `{"exp": ..., "sub": user_id, "type": "access"|"refresh"}`

Password hashing:
- `get_password_hash(password)` — bcrypt
- `verify_password(plain, hashed)` — bcrypt `checkpw`
- NEVER store plain passwords

API keys:
- `secrets.compare_digest()` for constant-time comparison
- `APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)`

## Role-Based Access Control

```python
class RoleChecker:
    def __init__(self, required_role: UserRole) -> None:
        self.required_role = required_role

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if not user.has_role(self.required_role):
            raise AuthorizationError(message=f"Role '{self.required_role.value}' required")
        return user

CurrentAdmin = Annotated[User, Depends(RoleChecker(UserRole.ADMIN))]
```
