"""Analysis-history search route."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import (
    AnalysisFilters,
    get_analysis_detail,
    get_filter_options,
    list_analyses,
    list_stock_runs,
)
from my_stock_web.view_models import (
    exchange_label,
    horizon_label,
    timeframe_label,
    to_analysis_detail,
    to_analysis_row,
)

router = APIRouter()


def _parse_date(value: str, field_name: str, errors: list[str]) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field_name} 날짜 형식이 올바르지 않아 적용하지 않았습니다.")
        return None


@router.get("/analyses", response_class=HTMLResponse, name="analyses")
def analyses(
    request: Request,
    q: str = "",
    exchange: str = "",
    timeframe: str = "",
    horizon: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    filter_errors: list[str] = []
    filters = AnalysisFilters(
        query=q.strip(),
        exchange=exchange,
        timeframe=timeframe,
        horizon=horizon,
        date_from=_parse_date(date_from, "시작", filter_errors),
        date_to=_parse_date(date_to, "종료", filter_errors),
    )
    result = list_analyses(session, filters, page=page)
    previous_url = None
    next_url = None
    if result.page > 1:
        previous_url = str(request.url.include_query_params(page=result.page - 1))
    if result.page < result.total_pages:
        next_url = str(request.url.include_query_params(page=result.page + 1))

    options = get_filter_options(session)
    context = {
        "request": request,
        "filters": {
            "q": q,
            "exchange": exchange,
            "timeframe": timeframe,
            "horizon": horizon,
            "date_from": date_from,
            "date_to": date_to,
        },
        "filter_errors": filter_errors,
        "options": {
            "exchanges": [(value, exchange_label(value)) for value in options.exchanges],
            "timeframes": [(value, timeframe_label(value)) for value in options.timeframes],
            "horizons": [(value, horizon_label(value)) for value in options.horizons],
        },
        "analyses": [to_analysis_row(run) for run in result.items],
        "total": result.total,
        "page": result.page,
        "total_pages": result.total_pages,
        "previous_url": previous_url,
        "next_url": next_url,
    }
    return request.app.state.templates.TemplateResponse(request, "analyses.html", context)


@router.get("/analyses/{run_id}", response_class=HTMLResponse, name="analysis_detail")
def analysis_detail(
    run_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    run = get_analysis_detail(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="분석 기록을 찾을 수 없습니다.")

    context = {
        "request": request,
        "analysis": to_analysis_detail(run),
        "timeline_count": len(list_stock_runs(session, run.exchange, run.ticker)),
    }
    return request.app.state.templates.TemplateResponse(request, "analysis_detail.html", context)
