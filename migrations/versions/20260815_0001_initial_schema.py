"""Create the analysis-history index schema.

Revision ID: 20260815_0001
Revises: None
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_runs",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("timeframe", sa.String(length=32), nullable=False),
        sa.Column("horizon", sa.String(length=64), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_verdict", sa.String(length=16), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("claim_count", sa.Integer(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("report_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint("artifact_path"),
    )
    op.create_index("ix_analysis_runs_as_of", "analysis_runs", ["as_of"])
    op.create_index("ix_analysis_runs_content_hash", "analysis_runs", ["content_hash"])
    op.create_index(
        "ix_analysis_runs_ticker_exchange_as_of",
        "analysis_runs",
        ["ticker", "exchange", "as_of"],
    )

    op.create_table(
        "index_errors",
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("file_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("artifact_path"),
    )

    op.create_table(
        "analysis_conflicts",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "position"),
    )
    op.create_table(
        "analysis_limitations",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "position"),
    )
    op.create_table(
        "claims",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("claim_id", sa.Text(), nullable=False),
        sa.Column("lane", sa.String(length=32), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_claims_confidence"),
        sa.CheckConstraint("kind IN ('fact', 'inference')", name="ck_claims_kind"),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "claim_id"),
    )
    op.create_index("ix_claims_run_lane", "claims", ["run_id", "lane"])
    op.create_table(
        "scenarios",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("scenario_name", sa.String(length=16), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("invalidation", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "scenario_name IN ('bull', 'base', 'bear')", name="ck_scenarios_name"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "scenario_name"),
    )
    op.create_table(
        "sources",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_type", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id", "source_id"),
    )
    op.create_table(
        "claim_sources",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("claim_id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "claim_id"],
            ["claims.run_id", "claims.claim_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id", "source_id"],
            ["sources.run_id", "sources.source_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", "claim_id", "source_id"),
    )
    op.create_table(
        "scenario_triggers",
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("scenario_name", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id", "scenario_name"],
            ["scenarios.run_id", "scenarios.scenario_name"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", "scenario_name", "position"),
    )


def downgrade() -> None:
    op.drop_table("scenario_triggers")
    op.drop_table("claim_sources")
    op.drop_table("sources")
    op.drop_table("scenarios")
    op.drop_index("ix_claims_run_lane", table_name="claims")
    op.drop_table("claims")
    op.drop_table("analysis_limitations")
    op.drop_table("analysis_conflicts")
    op.drop_table("index_errors")
    op.drop_index("ix_analysis_runs_ticker_exchange_as_of", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_content_hash", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_as_of", table_name="analysis_runs")
    op.drop_table("analysis_runs")
