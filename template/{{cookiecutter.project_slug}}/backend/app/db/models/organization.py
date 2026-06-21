{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_sqlmodel %}
"""Organization, OrganizationMember and Invitation models (PostgreSQL + SQLModel)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func, text
from sqlmodel import Field, Relationship, SQLModel

from app.db.base import TimestampMixin


class OrgRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(TimestampMixin, SQLModel, table=True):
    """Organization — the primary multi-tenant unit. Every user gets a Personal org on signup."""

    __tablename__ = "organizations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(sa_column=Column(String(128), nullable=False))
    slug: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    is_personal: bool = Field(default=False, sa_column=Column(nullable=False, default=False, index=True))
    avatar_url: str | None = Field(default=None, sa_column=Column(String(500), nullable=True))
    created_by_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
    )
{%- if cookiecutter.enable_billing %}
    stripe_customer_id: str | None = Field(
        default=None, sa_column=Column(String(64), unique=True, nullable=True, index=True)
    )
    stripe_subscription_id: str | None = Field(
        default=None, sa_column=Column(String(128), unique=True, nullable=True, index=True)
    )
    subscription_tier: str = Field(
        default="free", sa_column=Column(String(32), nullable=False, default="free", index=True)
    )
    seats_limit: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    credits_balance: int = Field(default=0, sa_column=Column(nullable=False, default=0))
    trial_ends_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
{%- endif %}

    members: list["OrganizationMember"] = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    invitations: list["Invitation"] = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, slug={self.slug}, personal={self.is_personal})>"


class OrganizationMember(SQLModel, table=True):
    """Membership of a User in an Organization with a role."""

    __tablename__ = "organization_members"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    organization_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    role: str = Field(default=OrgRole.MEMBER.value, sa_column=Column(String(20), nullable=False))
    invited_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=True,
        ),
    )
    joined_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )

    organization: "Organization" = Relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("ix_org_member_org_role", "organization_id", "role"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"


class Invitation(SQLModel, table=True):
    """Email invitation to join an Organization."""

    __tablename__ = "invitations"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    organization_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    email: str = Field(sa_column=Column(String(255), nullable=False, index=True))
    role: str = Field(default=OrgRole.MEMBER.value, sa_column=Column(String(20), nullable=False))
    invited_by_user_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=False,
        ),
    )
    token: str = Field(sa_column=Column(String(64), unique=True, nullable=False, index=True))
    status: str = Field(
        default=InvitationStatus.PENDING.value,
        sa_column=Column(String(20), nullable=False, default=InvitationStatus.PENDING.value, index=True),
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    accepted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    accepted_by_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id"),
            nullable=True,
        ),
    )

    organization: "Organization" = Relationship(back_populates="invitations")

    __table_args__ = (
        Index(
            "uq_pending_invitation",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Invitation(org={self.organization_id}, email={self.email}, status={self.status})>"


{%- else %}
"""Organization, OrganizationMember and Invitation models (PostgreSQL async)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text

from app.db.base import Base, TimestampMixin


class OrgRole(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class InvitationStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(Base, TimestampMixin):
    """Organization — the primary multi-tenant unit. Every user gets a Personal org on signup."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_personal: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
{%- if cookiecutter.enable_billing %}
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    subscription_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="free", index=True)
    seats_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credits_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
{%- endif %}

    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, slug={self.slug}, personal={self.is_personal})>"


class OrganizationMember(Base):
    """Membership of a User in an Organization with a role."""

    __tablename__ = "organization_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=OrgRole.MEMBER.value)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="members")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("ix_org_member_org_role", "organization_id", "role"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"


class Invitation(Base):
    """Email invitation to join an Organization."""

    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=OrgRole.MEMBER.value)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvitationStatus.PENDING.value,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    organization: Mapped["Organization"] = relationship("Organization", back_populates="invitations")

    __table_args__ = (
        Index(
            "uq_pending_invitation",
            "organization_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Invitation(org={self.organization_id}, email={self.email}, status={self.status})>"


{%- endif %}
{%- endif %}
