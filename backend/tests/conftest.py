from collections.abc import AsyncGenerator
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
async def prepare_test_db() -> AsyncGenerator[None, None]:
    """Гарантирует наличие схемы БД перед прогоном тестов.

    Не удаляет таблицы на выходе (drop_all), чтобы не ломать миграции
    и структуру таблиц в dev-базе. Изоляция данных в каждом тесте
    обеспечивается автоматическим откатом транзакции (rollback) в фикстуре db_session.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest.fixture
async def db_session(prepare_test_db: None) -> AsyncGenerator[AsyncSession, None]:  # noqa: ARG001
    """Предоставляет изолированную сессию БД с автоматическим откатом через savepoint.

    Любые вызовы session.commit() внутри теста фиксируют только точку сохранения (savepoint),
    а в конце теста внешняя транзакция откатывается, гарантируя полную изоляцию без удаления таблиц.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
            autoflush=False,
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


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
