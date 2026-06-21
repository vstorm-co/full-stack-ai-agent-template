---
description: API design, REST conventions, auth, pagination, response format
globs: ["backend/app/api/**/*.py"]
---

# API Conventions

## Route Structure

- All routes under `/api/v1/` prefix
- One file per domain entity in `api/routes/v1/`
- Use `APIRouter()` with tags

## HTTP Methods & Status Codes

```python
# GET — read
@router.get("/{id}", response_model=EntityRead)

# GET list — paginated
@router.get("", response_model=EntityList)

# POST — create (201)
@router.post("", response_model=EntityRead, status_code=status.HTTP_201_CREATED)

# PATCH — partial update
@router.patch("/{id}", response_model=EntityRead)

# DELETE — no content (204)
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
```

## Pagination

```python
@router.get("", response_model=ConversationList)
async def list_items(
    service: ConversationSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
    items, total = await service.list(user_id=user.id, skip=skip, limit=limit)
    return ConversationList(items=items, total=total)
```

## Authentication

- `CurrentUser` — JWT Bearer token (any authenticated user)
- `CurrentAdmin` — JWT + admin role check via `RoleChecker`
- `ValidAPIKey` — API key from header (service-to-service)

```python
# Protected endpoint
async def get_profile(user: CurrentUser) -> Any: ...

# Admin-only endpoint
async def delete_user(user: CurrentAdmin) -> Any: ...

# API key endpoint
async def webhook_callback(api_key: ValidAPIKey) -> Any: ...
```

## Response Format

All route handlers return `-> Any`. The `response_model` parameter handles serialization.

Error responses follow this JSON structure:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "User not found",
    "details": {"user_id": "..."}
  }
}
```

## File Upload

```python
@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    user: CurrentUser,
    service: UserSvc,
) -> Any:
    data = await file.read()
    return await service.update_avatar(user.id, data, file.filename or "avatar.jpg")
```
