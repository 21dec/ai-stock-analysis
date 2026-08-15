"""Safe serving of indexed standalone reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from my_stock_web.dependencies import get_session
from my_stock_web.repository import get_analysis_run

router = APIRouter()


@router.get("/reports/{run_id}", name="report")
def report(run_id: str, request: Request, session: Session = Depends(get_session)) -> FileResponse:
    run = get_analysis_run(session, run_id)
    if run is None or run.report_path is None:
        raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다.")

    artifacts_root = request.app.state.settings.artifacts_root.resolve()
    path = (artifacts_root / run.report_path).resolve()
    if not path.is_relative_to(artifacts_root) or not path.is_file():
        raise HTTPException(status_code=404, detail="보고서 파일을 찾을 수 없습니다.")
    return FileResponse(path, media_type="text/html; charset=utf-8")
