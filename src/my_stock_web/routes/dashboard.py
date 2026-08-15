"""Dashboard route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import get_dashboard_stats, list_latest_by_stock, list_recent_runs
from my_stock_web.view_models import format_kst, to_analysis_row

router = APIRouter()


@router.get("/", response_class=HTMLResponse, name="dashboard")
def dashboard(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
    stats = get_dashboard_stats(session)
    sync = request.app.state.sync_service.snapshot()
    context = {
        "request": request,
        "stats": stats,
        "latest_date": format_kst(stats.latest_as_of, "%Y.%m.%d"),
        "recent_runs": [to_analysis_row(run) for run in list_recent_runs(session)],
        "latest_by_stock": [to_analysis_row(run) for run in list_latest_by_stock(session)],
        "last_sync": sync.last_result,
    }
    return request.app.state.templates.TemplateResponse(request, "dashboard.html", context)
