import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.logging_config import clear_request_id, configure_logging, log_event, set_request_id
from app.routers.analysis_router import router as analysis_router
from app.routers.admin_router import router as admin_router
from app.routers.auth_router import router as auth_router
from app.routers.demo_router import router as demo_router
from app.routers.report_router import router as report_router
from app.routers.retention_router import router as retention_router
from app.routers.upload_router import router as document_router

settings = get_settings()
logger = configure_logging(settings.log_level)

app = FastAPI(
    title=settings.project_name,
    description=settings.project_description,
    version=settings.version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid4().hex[:16]}"
    set_request_id(request_id)
    request.state.request_id = request_id
    started_at = time.perf_counter()

    log_event(
        "request_started",
        event="request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        clear_request_id()
        raise

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    log_event(
        "request_completed",
        event="request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    clear_request_id()
    return response


app.include_router(document_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(analysis_router, prefix=settings.api_prefix)
app.include_router(report_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(retention_router, prefix=settings.api_prefix)
app.include_router(demo_router)


@app.get("/")
async def root():
    return {
        "message": "Jeonse Fraud Prevention API is running",
        "domains": ["documents", "analysis", "reports", "auth", "retention"],
        "logging": "request_id_json_logging_enabled",
        "metrics": "cloudwatch_ready_metric_hooks_enabled",
    }
