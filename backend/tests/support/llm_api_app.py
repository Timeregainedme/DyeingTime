"""仅挂载 LLM 路由的 FastAPI 应用，避免在轻量测试环境中导入完整 app（含 Celery/film 等）。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.routes import llm
from app.bootstrap import bootstrap_all_registries
from app.config import settings
from app.schemas.common import ApiResponse


def _error_message(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict) and "msg" in item:
                loc = item.get("loc", ())
                loc_str = ".".join(str(x) for x in loc if x != "body")
                parts.append(f"{loc_str}: {item['msg']}" if loc_str else item["msg"])
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "Validation error"
    return str(detail)


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        code = exc.status_code
        message = _error_message(exc.detail)
    else:
        code = 500
        message = "Internal server error"
    body = ApiResponse[None](code=code, message=message, data=None, meta=None).model_dump()
    return JSONResponse(status_code=code, content=body)


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    message = _error_message(exc.errors())
    body = ApiResponse[None](code=422, message=message, data=None, meta=None).model_dump()
    return JSONResponse(status_code=422, content=body)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    bootstrap_all_registries()
    yield


def build_llm_only_app() -> FastAPI:
    """与主应用相同的错误壳与 /api/v1/llm 前缀，仅不含 film/studio 等路由。"""
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=_lifespan,
        docs_url=None,
        redoc_url=None,
    )
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(Exception, http_exception_handler)
    application.include_router(llm.router, prefix=f"{settings.api_v1_prefix}/llm", tags=["llm"])
    return application
