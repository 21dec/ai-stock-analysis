"""Safe browser access to indexed evidence JSON."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import get_analysis_run

router = APIRouter()


@router.get(
    "/artifacts/{run_id}/evidence",
    response_class=HTMLResponse,
    name="evidence_artifact",
)
def evidence_artifact(
    run_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> HTMLResponse:
    run = get_analysis_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evidence를 찾을 수 없습니다.")
    return request.app.state.templates.TemplateResponse(
        request,
        "raw_evidence.html",
        {
            "run_id": run_id,
            "ticker": run.ticker,
            "json_text": json.dumps(run.evidence_json, ensure_ascii=False, indent=2),
        },
    )
