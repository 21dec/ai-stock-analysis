"""Per-stock analysis timeline route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import list_stock_runs
from my_stock_web.view_models import format_kst, stock_display_name, to_analysis_row

router = APIRouter()


@router.get(
    "/stocks/{exchange}/{ticker}",
    response_class=HTMLResponse,
    name="stock_timeline",
)
def stock_timeline(
    exchange: str,
    ticker: str,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    runs = list_stock_runs(session, exchange, ticker)
    if not runs:
        raise HTTPException(status_code=404, detail="종목 분석 이력을 찾을 수 없습니다.")

    row_views = [to_analysis_row(run) for run in runs]
    context = {
        "request": request,
        "ticker": ticker,
        "display_name": stock_display_name(exchange, ticker),
        "exchange": exchange,
        "exchange_label": row_views[0].exchange_label,
        "runs": row_views,
        "first_date": format_kst(runs[-1].as_of, "%Y.%m.%d"),
        "latest_date": format_kst(runs[0].as_of, "%Y.%m.%d"),
        "filtered_history_url": request.url_for("analyses").include_query_params(
            q=ticker, exchange=exchange
        ),
    }
    return request.app.state.templates.TemplateResponse(request, "stock_timeline.html", context)
