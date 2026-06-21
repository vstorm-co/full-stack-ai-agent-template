"""Database module."""
{%- if cookiecutter.use_sqlalchemy %}

from app.db.base import Base

__all__ = ["Base"]
{%- else %}
# SQLModel uses SQLModel class directly as base, no separate Base class needed
from app.db.base import TimestampMixin

__all__ = ["TimestampMixin"]
{%- endif %}
