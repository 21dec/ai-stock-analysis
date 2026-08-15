"""Read-only operational status for the local analysis index."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import (
    get_dashboard_stats,
    get_latest_indexed_at,
    list_index_errors,
)
from my_stock_web.view_models import format_kst, to_index_error_view

router = APIRouter()


@router.get("/system", response_class=HTMLResponse, name="system_status")
def system_status(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    session.execute(text("SELECT 1"))
    snapshot = request.app.state.sync_service.snapshot()
    state_labels = {"idle": "대기 중", "running": "동기화 중", "error": "오류"}
    context = {
        "request": request,
        "database_status": "연결됨",
        "stats": get_dashboard_stats(session),
        "latest_indexed_at": format_kst(
            get_latest_indexed_at(session), "%Y.%m.%d %H:%M:%S 한국시간"
        ),
        "sync": snapshot,
        "sync_state_label": state_labels[snapshot.state],
        "last_started_at": format_kst(snapshot.last_started_at, "%Y.%m.%d %H:%M:%S 한국시간"),
        "last_completed_at": format_kst(snapshot.last_completed_at, "%Y.%m.%d %H:%M:%S 한국시간"),
        "next_sync_at": format_kst(snapshot.next_sync_at, "%Y.%m.%d %H:%M:%S 한국시간"),
        "errors": [to_index_error_view(error) for error in list_index_errors(session)],
        "artifacts_root": str(request.app.state.settings.artifacts_root),
    }
    return request.app.state.templates.TemplateResponse(request, "system.html", context)
