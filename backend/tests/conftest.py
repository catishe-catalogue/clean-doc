from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import fitz
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


@pytest.fixture
def sample_pdf_1page() -> bytes:
    """Генерирует валидный 1-страничный PDF с текстом."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Акт выполненных работ No 123", fontsize=14)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def sample_pdf_2page() -> bytes:
    """Генерирует 2-страничный PDF с текстом."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Счет на оплату No 45. Страница 1", fontsize=14)
    p2 = doc.new_page()
    p2.insert_text((50, 72), "Условия поставки. Страница 2", fontsize=14)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def sample_pdf_multipage_10page() -> bytes:
    """Генерирует 10-страничный PDF для проверки ограничения Free-тарифа."""
    doc = fitz.open()
    for i in range(10):
        page = doc.new_page()
        page.insert_text((50, 72), f"Договор оказания услуг. Страница {i + 1}", fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def sample_pdf_table() -> bytes:
    """Генерирует PDF с нарисованной сеткой таблицы."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Товарная накладная ТОРГ-12", fontsize=14)
    # Рисуем простую таблицу 3x3
    for r in range(4):
        y = 100 + r * 30
        page.draw_line(fitz.Point(50, y), fitz.Point(400, y))
    for c in range(4):
        x = 50 + c * 116
        page.draw_line(fitz.Point(x, 100), fitz.Point(x, 190))
    page.insert_text((60, 120), "Наименование")
    page.insert_text((180, 120), "Кол-во")
    page.insert_text((300, 120), "Сумма")
    data = doc.tobytes()
    doc.close()
    return data


@pytest.fixture
def sample_corrupted_pdf() -> bytes:
    """Генерирует файл с невалидным синтаксисом."""
    return b"%PDF-1.4\ncorrupted syntax and no xref table"


@pytest.fixture
def sample_fake_pdf() -> bytes:
    """Файл с неверными Magic Bytes."""
    return b"NOT_A_PDF_FILE_HEADER_BINARY_DATA"
