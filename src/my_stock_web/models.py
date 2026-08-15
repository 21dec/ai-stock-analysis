"""PostgreSQL models for the rebuildable analysis-history index."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_runs_ticker_exchange_as_of", "ticker", "exchange", "as_of"),
        Index("ix_analysis_runs_as_of", "as_of"),
        Index("ix_analysis_runs_content_hash", "content_hash"),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False)
    claim_count: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    report_path: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    claims: Mapped[list["Claim"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    sources: Mapped[list["Source"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    scenarios: Mapped[list["Scenario"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    conflicts: Mapped[list["AnalysisConflict"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    limitations: Mapped[list["AnalysisLimitation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (
        CheckConstraint("kind IN ('fact', 'inference')", name="ck_claims_kind"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_claims_confidence"),
        Index("ix_claims_run_lane", "run_id", "lane"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    claim_id: Mapped[str] = mapped_column(Text, primary_key=True)
    lane: Mapped[str | None] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="claims")
    source_links: Mapped[list["ClaimSource"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="claim_links,source",
    )


class Source(Base):
    __tablename__ = "sources"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[str] = mapped_column(Text, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(128), nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="sources")
    claim_links: Mapped[list["ClaimSource"]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="claim,source_links",
    )


class ClaimSource(Base):
    __tablename__ = "claim_sources"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "claim_id"],
            ["claims.run_id", "claims.claim_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["run_id", "source_id"],
            ["sources.run_id", "sources.source_id"],
            ondelete="CASCADE",
        ),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    claim_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_id: Mapped[str] = mapped_column(Text, primary_key=True)

    claim: Mapped[Claim] = relationship(back_populates="source_links", overlaps="claim_links")
    source: Mapped[Source] = relationship(
        back_populates="claim_links", overlaps="claim,source_links"
    )


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        CheckConstraint("scenario_name IN ('bull', 'base', 'bear')", name="ck_scenarios_name"),
    )

    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    scenario_name: Mapped[str] = mapped_column(String(16), primary_key=True)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="scenarios")
    triggers: Mapped[list["ScenarioTrigger"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", passive_deletes=True
    )


class ScenarioTrigger(Base):
    __tablename__ = "scenario_triggers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "scenario_name"],
            ["scenarios.run_id", "scenarios.scenario_name"],
            ondelete="CASCADE",
        ),
    )

    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    scenario_name: Mapped[str] = mapped_column(String(16), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    scenario: Mapped[Scenario] = relationship(back_populates="triggers")


class AnalysisConflict(Base):
    __tablename__ = "analysis_conflicts"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="conflicts")


class AnalysisLimitation(Base):
    __tablename__ = "analysis_limitations"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_runs.run_id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="limitations")


class IndexError(Base):
    __tablename__ = "index_errors"

    artifact_path: Mapped[str] = mapped_column(Text, primary_key=True)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    file_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
