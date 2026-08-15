"""Side-by-side comparison for two runs of the same stock."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import get_analysis_detail, list_stock_runs
from my_stock_web.view_models import stock_display_name, to_analysis_comparison, to_analysis_row

router = APIRouter()


@router.get(
    "/stocks/{exchange}/{ticker}/compare",
    response_class=HTMLResponse,
    name="compare_stock_runs",
)
def compare_stock_runs(
    exchange: str,
    ticker: str,
    request: Request,
    before: str = "",
    after: str = "",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    runs = list_stock_runs(session, exchange, ticker)
    if not runs:
        raise HTTPException(status_code=404, detail="종목 분석 이력을 찾을 수 없습니다.")

    run_ids = {run.run_id for run in runs}
    if before and before not in run_ids:
        raise HTTPException(status_code=404, detail="이전 분석 기록을 찾을 수 없습니다.")
    if after and after not in run_ids:
        raise HTTPException(status_code=404, detail="비교 분석 기록을 찾을 수 없습니다.")

    selected_before = before
    selected_after = after
    if len(runs) >= 2:
        selected_before = selected_before or runs[1].run_id
        selected_after = selected_after or runs[0].run_id

    comparison = None
    selection_error = None
    if selected_before and selected_after:
        if selected_before == selected_after:
            selection_error = "서로 다른 두 분석을 선택해 주세요."
        else:
            before_run = get_analysis_detail(session, selected_before)
            after_run = get_analysis_detail(session, selected_after)
            if before_run is None or after_run is None:
                raise HTTPException(status_code=404, detail="비교할 분석을 찾을 수 없습니다.")
            comparison = to_analysis_comparison(before_run, after_run)

    row_views = [to_analysis_row(run) for run in runs]
    return request.app.state.templates.TemplateResponse(
        request,
        "comparison.html",
        {
            "ticker": ticker,
            "display_name": stock_display_name(exchange, ticker),
            "exchange": exchange,
            "exchange_label": row_views[0].exchange_label,
            "runs": row_views,
            "selected_before": selected_before,
            "selected_after": selected_after,
            "selection_error": selection_error,
            "comparison": comparison,
        },
    )
