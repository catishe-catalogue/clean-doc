import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base

settings = get_settings()

# Тестовый асинхронный движок БД
test_engine = create_async_engine(
    settings.async_database_url,
    poolclass=NullPool,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """Создает единый event loop для тестовой сессии."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def prepare_test_db() -> AsyncGenerator[None, None]:
    """Создает схему БД перед прогоном тестов и удаляет после.

    Не autouse — используется только тестами, которым нужна живая БД.
    Запускайте make dev перед make test-py для доступности PostgreSQL.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session(prepare_test_db: None) -> AsyncGenerator[AsyncSession, None]:  # noqa: ARG001
    """Предоставляет изолированную сессию БД с автоматическим откатом транзакции."""
    async with TestingSessionLocal() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
def mock_redis() -> MagicMock:
    """Мок клиента Redis для изоляции юнит-тестов."""
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    return client


@pytest.fixture
def mock_storage() -> MagicMock:
    """Мок хранилища S3 (StorageService) без реальных сетевых вызовов."""
    storage = MagicMock()
    storage.check_health = AsyncMock(return_value=True)
    storage.ensure_bucket_exists = AsyncMock(return_value=None)
    storage.upload_bytes = AsyncMock(return_value=None)
    storage.download_bytes = AsyncMock(return_value=b"%PDF-1.4 test document content")
    storage.generate_presigned_url = AsyncMock(
        return_value="http://localhost:9000/cleandoc-dev/temp/test.pdf?signature=valid"
    )
    return storage


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный тестовый клиент FastAPI с подмененной зависимостью get_db."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client_no_db() -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный тестовый клиент FastAPI без зависимости от get_db.

    Используется для тестов, не требующих реального подключения к БД.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
