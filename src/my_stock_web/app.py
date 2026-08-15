"""FastAPI application factory for the local analysis-history product."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from my_stock_web.config import Settings
from my_stock_web.db import create_database_engine, create_session_factory
from my_stock_web.routes import (
    analyses,
    artifacts,
    comparisons,
    dashboard,
    health,
    reports,
    stocks,
    system,
)
from my_stock_web.sync_service import ArtifactSyncService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    templates = Jinja2Templates(directory=str(settings.project_root / "src/my_stock_web/templates"))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.settings = settings
        app.state.templates = templates
        app.state.sync_service = ArtifactSyncService(
            app.state.session_factory,
            settings.artifacts_root,
            interval_seconds=settings.sync_interval_seconds,
        )
        await app.state.sync_service.start()
        try:
            yield
        finally:
            await app.state.sync_service.stop()
            engine.dispose()

    app = FastAPI(
        title="나의 주식 분석 이력",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(settings.project_root / "src/my_stock_web/static")),
        name="static",
    )
    app.include_router(dashboard.router)
    app.include_router(analyses.router)
    app.include_router(stocks.router)
    app.include_router(comparisons.router)
    app.include_router(artifacts.router)
    app.include_router(reports.router)
    app.include_router(system.router)
    app.include_router(health.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        if request.url.path == "/health":
            return await http_exception_handler(request, exc)
        message = (
            "요청한 페이지나 분석 기록을 찾을 수 없습니다."
            if exc.status_code == 404
            else "요청을 처리하지 못했습니다."
        )
        return templates.TemplateResponse(
            request,
            "error.html",
            {"status_code": exc.status_code, "message": message},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _exc: Exception):
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "status_code": 500,
                "message": "분석 이력을 불러오지 못했습니다. 서버 로그를 확인해 주세요.",
            },
            status_code=500,
        )

    return app


app = create_app()
