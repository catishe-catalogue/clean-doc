from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.database import engine
from app.core.redis import redis_pool
from app.services.storage_service import storage_service

settings = get_settings()

# Настройка структурированного логирования structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
        if settings.ENVIRONMENT == "prod"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20 if not settings.DEBUG else 10),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # Инициализация при старте
    logger.info("startup", project=settings.PROJECT_NAME, env=settings.ENVIRONMENT)
    try:
        await storage_service.ensure_bucket_exists()
    except Exception as exc:
        logger.warning("s3_init_warning", error=str(exc))
    yield
    # Очистка при завершении
    logger.info("shutdown", project=settings.PROJECT_NAME)
    try:
        await engine.dispose()
        await redis_pool.disconnect()
    except Exception as exc:
        logger.warning("cleanup_warning", error=str(exc))


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    docs_url=f"{settings.API_V1_STR}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_STR}/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus метрики
if settings.PROMETHEUS_ENABLED:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Подключение маршрутов API v1
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


# Централизованная обработка непредвиденных ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_server_error", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Внутренняя ошибка сервера. Пожалуйста, повторите попытку позже.",
            "code": "INTERNAL_SERVER_ERROR",
        },
    )
