import asyncio

from fastapi import APIRouter, Response, status
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client
from app.schemas.health import HealthResponse, ReadinessChecks, ReadinessResponse
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health_check() -> HealthResponse:
    """Liveness probe: возвращает 200 OK, пока сервис запущен."""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
async def readiness_check(response: Response) -> ReadinessResponse:
    """Readiness probe: проверяет доступность PostgreSQL, Redis и S3."""
    db_ok = False
    redis_ok = False
    storage_ok = False

    # 1. Проверка PostgreSQL (таймаут 3с)
    try:
        async with AsyncSessionLocal() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=3.0)
            db_ok = True
    except Exception:
        db_ok = False

    # 2. Проверка Redis (таймаут 3с)
    try:
        redis_client: Redis[str] = get_redis_client()
        await asyncio.wait_for(redis_client.ping(), timeout=3.0)
        redis_ok = True
    except Exception:
        redis_ok = False

    # 3. Проверка S3 хранилища (таймаут 3с)
    try:
        storage_ok = await asyncio.wait_for(storage_service.check_health(), timeout=3.0)
    except Exception:
        storage_ok = False

    all_ready = db_ok and redis_ok and storage_ok
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ok" if all_ready else "unhealthy",
        checks=ReadinessChecks(
            database=db_ok,
            redis=redis_ok,
            storage=storage_ok,
        ),
    )
