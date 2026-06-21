{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""create materialized view mv_usage_daily

Revision ID: 0015_create_mv_usage_daily
Revises: 0014_credits_usage_events
Create Date: {{ cookiecutter.generated_at }}

Creates a daily-bucketed materialized view for fast usage aggregation queries.
The UNIQUE index on (organization_id, day) allows REFRESH CONCURRENTLY.
"""

from alembic import op

revision = "0015_create_mv_usage_daily"
down_revision = "0014_credits_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE MATERIALIZED VIEW mv_usage_daily AS
        SELECT
            date_trunc('day', created_at AT TIME ZONE 'UTC')::date AS day,
            organization_id,
            SUM(input_tokens)    AS input_tokens,
            SUM(output_tokens)   AS output_tokens,
            SUM(cached_tokens)   AS cached_tokens,
            SUM(credits_charged) AS credits_charged,
            COUNT(*)             AS total_calls
        FROM usage_event
        GROUP BY 1, 2
    """)
    op.execute("""
        CREATE UNIQUE INDEX ix_mv_usage_daily_org_day
        ON mv_usage_daily (organization_id, day)
    """)


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_usage_daily")

{%- else %}
"""create mv_usage_daily — skipped (PostgreSQL + billing + credits not all enabled)

Revision ID: 0015_create_mv_usage_daily
Revises: 0014_credits_usage_events
"""

revision = "0015_create_mv_usage_daily"
down_revision = "0014_credits_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
