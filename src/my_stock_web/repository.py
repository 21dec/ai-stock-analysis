"""Read-only PostgreSQL queries for dashboard and analysis-history screens."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import ceil

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.orm import Session, selectinload

from my_stock_web.models import AnalysisRun, Claim, ClaimSource, IndexError, Scenario


@dataclass(frozen=True)
class DashboardStats:
    total_runs: int
    total_stocks: int
    latest_as_of: datetime | None
    index_errors: int


@dataclass(frozen=True)
class AnalysisFilters:
    query: str = ""
    exchange: str = ""
    timeframe: str = ""
    horizon: str = ""
    date_from: date | None = None
    date_to: date | None = None


@dataclass(frozen=True)
class AnalysisPage:
    items: list[AnalysisRun]
    total: int
    page: int
    per_page: int

    @property
    def total_pages(self) -> int:
        return max(1, ceil(self.total / self.per_page))


@dataclass(frozen=True)
class FilterOptions:
    exchanges: list[str]
    timeframes: list[str]
    horizons: list[str]


def get_dashboard_stats(session: Session) -> DashboardStats:
    total_runs = session.scalar(select(func.count()).select_from(AnalysisRun)) or 0
    stock_pairs = select(AnalysisRun.ticker, AnalysisRun.exchange).distinct().subquery()
    total_stocks = session.scalar(select(func.count()).select_from(stock_pairs)) or 0
    latest_as_of = session.scalar(select(func.max(AnalysisRun.as_of)))
    index_errors = session.scalar(select(func.count()).select_from(IndexError)) or 0
    return DashboardStats(total_runs, total_stocks, latest_as_of, index_errors)


def list_recent_runs(session: Session, limit: int = 10) -> list[AnalysisRun]:
    statement = select(AnalysisRun).order_by(AnalysisRun.as_of.desc()).limit(limit)
    return list(session.scalars(statement))


def list_latest_by_stock(session: Session, limit: int = 12) -> list[AnalysisRun]:
    ranked = select(
        AnalysisRun.run_id,
        func.row_number()
        .over(
            partition_by=(AnalysisRun.exchange, AnalysisRun.ticker),
            order_by=AnalysisRun.as_of.desc(),
        )
        .label("position"),
    ).subquery()
    statement = (
        select(AnalysisRun)
        .join(ranked, ranked.c.run_id == AnalysisRun.run_id)
        .where(ranked.c.position == 1)
        .order_by(AnalysisRun.as_of.desc())
        .limit(limit)
    )
    return list(session.scalars(statement))


def list_analyses(
    session: Session,
    filters: AnalysisFilters,
    *,
    page: int = 1,
    per_page: int = 20,
) -> AnalysisPage:
    conditions = []
    if filters.query:
        pattern = f"%{filters.query}%"
        conditions.append(or_(AnalysisRun.ticker.ilike(pattern), AnalysisRun.run_id.ilike(pattern)))
    if filters.exchange:
        conditions.append(AnalysisRun.exchange == filters.exchange)
    if filters.timeframe:
        conditions.append(AnalysisRun.timeframe == filters.timeframe)
    if filters.horizon:
        conditions.append(AnalysisRun.horizon == filters.horizon)
    if filters.date_from:
        conditions.append(cast(AnalysisRun.as_of, Date) >= filters.date_from)
    if filters.date_to:
        conditions.append(cast(AnalysisRun.as_of, Date) <= filters.date_to)

    count_statement = select(func.count()).select_from(AnalysisRun).where(*conditions)
    total = session.scalar(count_statement) or 0
    statement = (
        select(AnalysisRun)
        .where(*conditions)
        .order_by(AnalysisRun.as_of.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return AnalysisPage(list(session.scalars(statement)), total, page, per_page)


def get_filter_options(session: Session) -> FilterOptions:
    def values(column) -> list[str]:
        return list(session.scalars(select(column).distinct().order_by(column)))

    return FilterOptions(
        exchanges=values(AnalysisRun.exchange),
        timeframes=values(AnalysisRun.timeframe),
        horizons=values(AnalysisRun.horizon),
    )


def get_analysis_run(session: Session, run_id: str) -> AnalysisRun | None:
    return session.get(AnalysisRun, run_id)


def get_analysis_detail(session: Session, run_id: str) -> AnalysisRun | None:
    statement = (
        select(AnalysisRun)
        .where(AnalysisRun.run_id == run_id)
        .options(
            selectinload(AnalysisRun.claims)
            .selectinload(Claim.source_links)
            .selectinload(ClaimSource.source),
            selectinload(AnalysisRun.sources),
            selectinload(AnalysisRun.scenarios).selectinload(Scenario.triggers),
            selectinload(AnalysisRun.conflicts),
            selectinload(AnalysisRun.limitations),
        )
    )
    return session.scalar(statement)


def list_stock_runs(session: Session, exchange: str, ticker: str) -> list[AnalysisRun]:
    statement = (
        select(AnalysisRun)
        .where(AnalysisRun.exchange == exchange, AnalysisRun.ticker == ticker)
        .order_by(AnalysisRun.as_of.desc())
    )
    return list(session.scalars(statement))


def list_index_errors(session: Session) -> list[IndexError]:
    statement = select(IndexError).order_by(IndexError.recorded_at.desc())
    return list(session.scalars(statement))


def get_latest_indexed_at(session: Session) -> datetime | None:
    return session.scalar(select(func.max(AnalysisRun.indexed_at)))
