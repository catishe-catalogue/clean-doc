from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(async_client_no_db: AsyncClient) -> None:
    """Проверка liveness probe: эндпоинт всегда возвращает 200 OK."""
    response = await async_client_no_db.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_all_healthy(async_client_no_db: AsyncClient) -> None:
    """Проверка readiness probe: когда БД, Redis и S3 доступны, возвращается 200 OK."""
    with (
        patch(
            "app.api.v1.endpoints.health.AsyncSessionLocal",
        ) as mock_session_local,
        patch("app.api.v1.endpoints.health.get_redis_client") as mock_get_redis,
        patch(
            "app.api.v1.endpoints.health.storage_service.check_health",
            new_callable=AsyncMock,
        ) as mock_s3_health,
    ):
        # Мок сессии БД
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()
        mock_session_local.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        mock_s3_health.return_value = True

        response = await async_client_no_db.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] is True
        assert data["checks"]["redis"] is True
        assert data["checks"]["storage"] is True


@pytest.mark.asyncio
async def test_readiness_redis_down(async_client_no_db: AsyncClient) -> None:
    """Проверка readiness probe: сбой Redis приводит к статусу 503 Service Unavailable."""
    with (
        patch(
            "app.api.v1.endpoints.health.AsyncSessionLocal",
        ) as mock_session_local,
        patch("app.api.v1.endpoints.health.get_redis_client") as mock_get_redis,
        patch(
            "app.api.v1.endpoints.health.storage_service.check_health",
            new_callable=AsyncMock,
        ) as mock_s3_health,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()
        mock_session_local.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Redis unreachable")
        mock_get_redis.return_value = mock_redis
        mock_s3_health.return_value = True

        response = await async_client_no_db.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["redis"] is False
        assert data["checks"]["database"] is True


@pytest.mark.asyncio
async def test_readiness_storage_down(async_client_no_db: AsyncClient) -> None:
    """Проверка readiness probe: сбой S3 приводит к статусу 503 Service Unavailable."""
    with (
        patch(
            "app.api.v1.endpoints.health.AsyncSessionLocal",
        ) as mock_session_local,
        patch("app.api.v1.endpoints.health.get_redis_client") as mock_get_redis,
        patch(
            "app.api.v1.endpoints.health.storage_service.check_health",
            new_callable=AsyncMock,
        ) as mock_s3_health,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()
        mock_session_local.return_value = mock_session

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_get_redis.return_value = mock_redis
        mock_s3_health.return_value = False

        response = await async_client_no_db.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["storage"] is False


@pytest.mark.asyncio
async def test_global_exception_handler() -> None:
    """Проверка глобального обработчика ошибок: непредвиденные исключения отдают 500 JSON."""
    import json
    from typing import Any

    from starlette.requests import Request

    from app.main import global_exception_handler

    headers: list[tuple[bytes, bytes]] = []
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "headers": headers,
    }
    request = Request(scope)
    response = await global_exception_handler(request, RuntimeError("Unexpected server crash"))
    assert response.status_code == 500
    data = json.loads(bytes(response.body).decode("utf-8"))
    assert data["code"] == "INTERNAL_SERVER_ERROR"
    assert "Внутренняя ошибка сервера" in data["error"]
