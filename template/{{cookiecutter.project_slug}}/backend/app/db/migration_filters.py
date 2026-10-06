{%- if cookiecutter.enable_memory or cookiecutter.enable_todo %}
"""What Alembic autogenerate must leave alone.

Some tables are created and migrated at runtime by the library that owns them,
and no model here declares them. Autogenerate compares the database with the
models, so it would write a ``drop_table`` for each into the next migration -
and the memory tables hold users' notes.
"""

EXTERNALLY_MANAGED_TABLES = frozenset(
    {
{%- if cookiecutter.enable_memory %}
        # pydantic-ai-harness PostgresMemoryStore
        "agent_memory",
        "agent_memory_operations",
        "agent_memory_metadata",
{%- endif %}
{%- if cookiecutter.enable_todo %}
        # pydantic-ai-todo AsyncPostgresStorage
        "todos",
{%- endif %}
    }
)


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    """Alembic ``include_name`` hook: skip the externally managed tables."""
    return not (type_ == "table" and name in EXTERNALLY_MANAGED_TABLES)
{%- endif %}
