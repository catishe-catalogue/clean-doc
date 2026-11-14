import logging

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_no_sqlalchemy_engine_info_logging(
    async_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Проверка отсутствия шума SQL-запросов уровня INFO от SQLAlchemy Engine."""
    with caplog.at_level(logging.INFO):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

    # Проверяем, что в записях лога нет записей уровня INFO от sqlalchemy.engine
    engine_logs = [
        rec
        for rec in caplog.records
        if "sqlalchemy.engine" in rec.name and rec.levelno == logging.INFO
    ]
    assert len(engine_logs) == 0, f"Обнаружен лишний SQL-лог: {engine_logs}"
