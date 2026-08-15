"""Local health check."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.models import AnalysisRun

router = APIRouter()


@router.get("/health", name="health")
def health(request: Request, session: Session = Depends(get_session)) -> dict[str, object]:
    session.execute(text("SELECT 1"))
    indexed_runs = session.scalar(select(func.count()).select_from(AnalysisRun)) or 0
    sync = request.app.state.sync_service.snapshot()
    return {
        "status": "ok" if sync.state != "error" else "degraded",
        "database": "connected",
        "indexed_runs": indexed_runs,
        "sync": sync.state,
        "sync_interval_seconds": sync.interval_seconds,
    }
