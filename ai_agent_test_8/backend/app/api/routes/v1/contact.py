"""Contact form route — anonymous submissions from the marketing site."""

from typing import Any

from fastapi import APIRouter, status

from app.api.deps import ContactSvc
from app.schemas.contact import ContactSubmissionCreate, ContactSubmissionRead

router = APIRouter()


@router.post(
    "/contact",
    response_model=ContactSubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def submit_contact(
    data: ContactSubmissionCreate,
    service: ContactSvc,
) -> Any:
    """Submit a contact-form inquiry. No auth required."""
    await service.submit(
        name=data.name,
        email=data.email,
        topic=data.topic,
        message=data.message,
    )
    return ContactSubmissionRead()
