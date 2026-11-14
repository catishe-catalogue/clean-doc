from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_dev_session_get_and_post_return_jwt(async_client: AsyncClient) -> None:
    """Проверка, что GET и POST /dev-session возвращают валидный JWT в dev-режиме."""
    with patch.object(settings, "DEV_FAST_MODE", True):
        # 1. GET запрос
        resp_get = await async_client.get("/api/v1/auth/dev-session")
        assert resp_get.status_code == 200
        data_get = resp_get.json()
        assert "access_token" in data_get
        assert len(data_get["access_token"]) > 20

        # 2. POST запрос
        resp_post = await async_client.post("/api/v1/auth/dev-session")
        assert resp_post.status_code == 200
        data_post = resp_post.json()
        assert "access_token" in data_post
        assert len(data_post["access_token"]) > 20

        # Оба метода имеют одинаковую структуру ответа
        assert set(data_get.keys()) == set(data_post.keys())


@pytest.mark.asyncio
async def test_dev_session_disabled_in_prod(async_client: AsyncClient) -> None:
    """Проверка, что в prod-режиме (DEV_FAST_MODE=False) эндпоинт отдает 403."""
    with patch.object(settings, "DEV_FAST_MODE", False):
        resp_get = await async_client.get("/api/v1/auth/dev-session")
        assert resp_get.status_code == 403
        assert resp_get.json()["detail"]["code"] == "DEV_MODE_DISABLED"

        resp_post = await async_client.post("/api/v1/auth/dev-session")
        assert resp_post.status_code == 403
        assert resp_post.json()["detail"]["code"] == "DEV_MODE_DISABLED"
