"""Business logic for user-scoped slash command settings (PostgreSQL async).

Two flavors of row live in the same table:
  - **Custom** commands (``prompt`` set) — user-defined `/<name>` shortcuts
    that expand to the stored prompt before being sent to the agent.
  - **Built-in overrides** (``prompt`` is NULL) — record only ``is_enabled``
    for one of the frontend's BUILTIN_COMMANDS. The frontend merges these
    with its own list at render time.

This split keeps built-in metadata (description, action handler) in code
where it belongs while letting users hide commands they never use.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, BadRequestError, NotFoundError
from app.db.models.user_slash_command import UserSlashCommand
from app.repositories import user_slash_command_repo
from app.schemas.user_slash_command import (
    UserSlashCommandCustomCreate,
    UserSlashCommandUpdate,
)


class UserSlashCommandService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_user(
        self, *, user_id: UUID
    ) -> tuple[list[UserSlashCommand], int]:
        return await user_slash_command_repo.list_for_user(self.db, user_id=user_id)

    async def create_custom(
        self, *, user_id: UUID, data: UserSlashCommandCustomCreate
    ) -> UserSlashCommand:
        existing = await user_slash_command_repo.get_by_name(
            self.db, user_id=user_id, name=data.name
        )
        if existing is not None:
            raise AlreadyExistsError(
                message="Slash command with this name already exists",
                details={"name": data.name},
            )
        try:
            return await user_slash_command_repo.create(
                self.db,
                user_id=user_id,
                name=data.name,
                prompt=data.prompt,
                is_enabled=data.is_enabled,
            )
        except IntegrityError as exc:
            raise AlreadyExistsError(
                message="Slash command with this name already exists",
                details={"name": data.name},
            ) from exc

    async def upsert_builtin_override(
        self, *, user_id: UUID, name: str, is_enabled: bool
    ) -> UserSlashCommand:
        """Create or update an override row for a built-in command.

        ``prompt`` stays NULL so the frontend knows this is just an enable
        flag, not a custom prompt.
        """
        existing = await user_slash_command_repo.get_by_name(
            self.db, user_id=user_id, name=name
        )
        if existing is None:
            return await user_slash_command_repo.create(
                self.db,
                user_id=user_id,
                name=name,
                prompt=None,
                is_enabled=is_enabled,
            )
        if existing.prompt is not None:
            raise BadRequestError(
                message="A custom command with this name already exists; "
                "edit it directly instead of overriding the built-in.",
                details={"name": name},
            )
        return await user_slash_command_repo.update(
            self.db, db_command=existing, update_data={"is_enabled": is_enabled}
        )

    async def update(
        self, *, user_id: UUID, command_id: UUID, data: UserSlashCommandUpdate
    ) -> UserSlashCommand:
        db_cmd = await self._get_owned(user_id=user_id, command_id=command_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return db_cmd

        if "name" in update_data and update_data["name"] != db_cmd.name:
            if db_cmd.prompt is None:
                raise BadRequestError(
                    message="Cannot rename a built-in override; delete it instead.",
                    details={"command_id": str(command_id)},
                )
            collision = await user_slash_command_repo.get_by_name(
                self.db, user_id=user_id, name=update_data["name"]
            )
            if collision is not None and collision.id != db_cmd.id:
                raise AlreadyExistsError(
                    message="Slash command with this name already exists",
                    details={"name": update_data["name"]},
                )

        if "prompt" in update_data and db_cmd.prompt is None:
            raise BadRequestError(
                message="Cannot add a prompt to a built-in override.",
                details={"command_id": str(command_id)},
            )

        return await user_slash_command_repo.update(
            self.db, db_command=db_cmd, update_data=update_data
        )

    async def delete(self, *, user_id: UUID, command_id: UUID) -> None:
        db_cmd = await self._get_owned(user_id=user_id, command_id=command_id)
        await user_slash_command_repo.delete(self.db, db_command=db_cmd)

    async def _get_owned(self, *, user_id: UUID, command_id: UUID) -> UserSlashCommand:
        db_cmd = await user_slash_command_repo.get_by_id(self.db, command_id)
        if db_cmd is None or db_cmd.user_id != user_id:
            raise NotFoundError(
                message="Slash command not found",
                details={"command_id": str(command_id)},
            )
        return db_cmd


