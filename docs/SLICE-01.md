# SLICE-01: Processing — Детальная спецификация реализации и инженерный харнес

> **Статус:** Действующий / Ready for Implementation  
> **Версия:** v1.0  
> **Дата:** 15 октября 2026 г.  
> **Спринт:** 2 (Дни 15–28)  
> **Зависимости:** Slice 0 (Foundation) — монорепозиторий, `deploy/docker-compose.yml`, `make gate`, базовая модель БД  
> **Единый источник технической правды:** [`docs/TECH.md`](./TECH.md)  
> **Операционный регламент:** [`AGENTS.md`](../AGENTS.md)  

---

## 0. Цель и Definition of Done (DoD)

**Цель Slice 1:** реализовать масштабируемый, отказоустойчивый и безопасный пайплайн фоновой конвертации PDF в форматы `.docx` и `.xlsx` в изолированных воркерах RQ с использованием `Docling 2.0`, нарезкой превью первых двух страниц через `PyMuPDF` (`fitz`), валидацией целостности через `qpdf`, потоковой трансляцией прогресса по протоколу Server-Sent Events (SSE) через Redis Pub/Sub и выдачей временных pre-signed ссылок на скачивание из S3-хранилища в строгом соответствии с 152-ФЗ.

### Definition of Done (DoD)

- [ ] Создана и применена миграция Alembic `0002_conversion_jobs.py` с таблицей `conversion_jobs` и индексами `idx_jobs_user_status`, `idx_jobs_expires`, `idx_jobs_dedup`.
- [ ] Объявлена декларативная модель SQLAlchemy 2.0 `ConversionJob` в `backend/app/models/job.py` с типизированной связью `user.jobs`.
- [ ] Описаны строгие Pydantic v2 схемы в `backend/app/schemas/convert.py` (`UploadResponse`, `JobStatusResponse`, `SSEProgressEvent`, `ApiErrorResponse`).
- [ ] Расширен сервис `backend/app/services/storage_service.py` поддержкой синхронных вызовов для воркеров и асинхронных оберток через `asyncio.to_thread` с обязательным шифрованием `ServerSideEncryption="AES256"`.
- [ ] Реализован сервис `backend/app/services/converter_service.py` с валидацией Magic Bytes (`%PDF-`), расчетом SHA-256, дедупликацией по PostgreSQL, маршрутизацией очередей (`priority`, `fast`, `heavy`), контролем суточных лимитов `daily_usage` и сессионными токенами гостей.
- [ ] Точка входа воркера `backend/app/workers/worker.py` выполняет превентивный разогрев (warmup) ML-моделей `Docling` при старте и запускает обработчик `rq worker priority fast heavy --max-jobs=50`.
- [ ] Фоновая задача `parse_and_convert` в `backend/app/workers/tasks.py` выполняет полный цикл: валидация `qpdf --check`, рендер JPEG-превью 150 DPI через `PyMuPDF`, определение признака `is_preview_only`, парсинг верстки через `Docling`, сохранение результата в S3, фиксацию времени `processing_seconds` и публикацию прогресса в Redis Pub/Sub.
- [ ] Реализован эндпоинт `POST /api/v1/convert/upload`, возвращающий `202 Accepted` и выставляющий HttpOnly cookie `anon_session` для гостей.
- [ ] Реализован эндпоинт моментального состояния `GET /api/v1/convert/jobs/{job_id}` (polling fallback для исключения состояния гонки).
- [ ] Реализован эндпоинт `GET /api/v1/convert/jobs/{job_id}/stream`, транслирующий SSE события (`progress`, `complete`, `error`) с отправкой комментариев `: keepalive\n\n` каждые 15 секунд и корректным закрытием подписки при разрыве соединения.
- [ ] Реализован эндпоинт `GET /api/v1/convert/jobs/{job_id}/download`, проверяющий права доступа (авторизованный пользователь или сессионный токен гостя), блокирующий скачивание при `is_preview_only = True` (`403 UPGRADE_REQUIRED`) и отдающий `307 Temporary Redirect` на pre-signed URL с TTL 15 минут.
- [ ] В логи сервиса и воркеров не попадают персональные данные, имена клиентских файлов и содержимое документов (строго UUID, байты, миллисекунды).
- [ ] Подготовлены программные генераторы синтетических тестовых PDF-файлов в `backend/tests/conftest.py`.
- [ ] Написан исчерпывающий набор юнит- и интеграционных тестов в `backend/tests/test_convert.py` с покрытием бизнес-логики конвертации не менее 85%.
- [ ] Сформирован бенчмарк на 20 эталонных российских B2B-документов (акты, счета, ТОРГ-12, УПД, 1С отчеты, договоры, спецификации).
- [ ] Все проверки качества `make gate` завершаются с кодом `0`.
- [ ] Зафиксированы архитектурные стыки (Seams) и точки расширения для плавного перехода к Slice 2 (Auth & UX).

---

## 1. Архитектурная структура файлов и модулей (Slice 1)

В рамках Slice 1 создаются и модифицируются следующие файлы монорепозитория:

```text
clean-doc/
  backend/
    alembic/
      versions/
        0002_conversion_jobs.py       # Миграция таблицы conversion_jobs и составных индексов
    app/
      api/
        v1/
          endpoints/
            convert.py                # HTTP контроллеры: upload, jobs snapshot, SSE stream, download
          router.py                   # Подключение convert.router в единое дерево API v1
      core/
        config.py                     # Чтение параметров WORKER_MAX_JOBS, WORKER_JOB_TIMEOUT, DOCLING_ARTIFACTS_PATH
      models/
        __init__.py                   # Экспорт модели ConversionJob
        job.py                        # SQLAlchemy 2.0 декларативная модель conversion_jobs
        user.py                       # Связь user.jobs (relationship back_populates)
      schemas/
        __init__.py                   # Экспорт DTO схем конвертации
        convert.py                    # Pydantic v2 схемы запросов, ответов и SSE-событий
      services/
        converter_service.py          # Бизнес-логика: валидация PDF, очереди, дедупликация, лимиты
        storage_service.py            # Дополнение синхронными методами и принудительным шифрованием AES256
      workers/
        worker.py                     # Точка входа rq worker с превентивным warmup Docling
        tasks.py                      # Фоновые задачи: parse_and_convert, render_preview, docling parsing
    tests/
      conftest.py                     # Фикстуры синтетических PDF-документов и mock-сервисов
      test_convert.py                 # Юнит- и интеграционные тесты API, воркеров и логики лимитов
    Dockerfile.worker                 # Сборка воркера: qpdf, PyMuPDF, Docling, системные шрифты, offline кеш
  deploy/
    docker-compose.yml                # Актуализация параметров cleandoc_worker (mem_limit 4g, volumes)
  docs/
    SLICE-01.md                       # Настоящий документ спецификации
```

---

## 2. База данных: миграция Alembic (`0002_conversion_jobs.py`)

Таблица `conversion_jobs` служит центральным реестром жизненного цикла задач конвертации.

### 2.1. Исходный код миграции `backend/alembic/versions/0002_conversion_jobs.py`

```python
"""conversion_jobs

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Создание таблицы conversion_jobs
    op.create_table(
        "conversion_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_token_hash", sa.Text(), nullable=True),
        sa.Column("target_format", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_checksum", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "usage_date",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("s3_input_key", sa.Text(), nullable=False),
        sa.Column("s3_output_key", sa.Text(), nullable=True),
        sa.Column(
            "s3_preview_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "is_preview_only",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("processing_seconds", sa.Numeric(precision=8, scale=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(now() + INTERVAL '2 hours')"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "target_format IN ('docx', 'xlsx')",
            name="check_conversion_jobs_format",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'processing', 'completed', 'failed')",
            name="check_conversion_jobs_status",
        ),
    )

    # 2. Индексы производительности и фильтрации
    op.create_index(
        "idx_jobs_user_status",
        "conversion_jobs",
        ["user_id", "status"],
    )

    op.create_index(
        "idx_jobs_expires",
        "conversion_jobs",
        ["expires_at"],
        postgresql_where=sa.text("status = 'completed'"),
    )

    # 3. Составной частичный индекс дедупликации (user_id, sha256_checksum, usage_date)
    # Исключает повторный расход CPU/RAM при повторной отправке идентичного файла в те же сутки
    op.create_index(
        "idx_jobs_dedup",
        "conversion_jobs",
        ["user_id", "sha256_checksum", "usage_date"],
        postgresql_where=sa.text(
            "sha256_checksum IS NOT NULL AND status IN ('processing', 'completed')"
        ),
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_dedup", table_name="conversion_jobs")
    op.drop_index("idx_jobs_expires", table_name="conversion_jobs")
    op.drop_index("idx_jobs_user_status", table_name="conversion_jobs")
    op.drop_table("conversion_jobs")
```

---

## 3. Модели данных SQLAlchemy 2.0 (`backend/app/models/job.py`)

### 3.1. Реализация модели `backend/app/models/job.py`

```python
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class ConversionJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "conversion_jobs"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    target_format: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256_checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        server_default="pending",
        nullable=False,
    )
    s3_input_key: Mapped[str] = mapped_column(Text, nullable=False)
    s3_output_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    s3_preview_keys: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_preview_only: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("false"),
        nullable=False,
    )
    processing_seconds: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=8, scale=3),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("(now() + INTERVAL '2 hours')"),
        nullable=False,
    )

    user: Mapped["User | None"] = relationship("User", back_populates="jobs")

    __table_args__ = (
        CheckConstraint(
            "target_format IN ('docx', 'xlsx')",
            name="check_conversion_jobs_format",
        ),
        CheckConstraint(
            "status IN ('pending', 'queued', 'processing', 'completed', 'failed')",
            name="check_conversion_jobs_status",
        ),
        Index("idx_jobs_user_status", "user_id", "status"),
        Index(
            "idx_jobs_expires",
            "expires_at",
            postgresql_where=text("status = 'completed'"),
        ),
        Index(
            "idx_jobs_dedup",
            "user_id",
            "sha256_checksum",
            "usage_date",
            postgresql_where=text(
                "sha256_checksum IS NOT NULL AND status IN ('processing', 'completed')"
            ),
        ),
    )
```

### 3.2. Обновление `backend/app/models/user.py`

В файл `backend/app/models/user.py` добавляется типизированная обратная связь:

```python
if TYPE_CHECKING:
    from app.models.job import ConversionJob
    from app.models.token import AppToken, RefreshToken
    from app.models.usage import DailyUsage

# Внутри класса User:
jobs: Mapped[list["ConversionJob"]] = relationship(
    "ConversionJob", back_populates="user", cascade="all, delete-orphan"
)
```

### 3.3. Экспорт в `backend/app/models/__init__.py`

```python
from app.models.base import Base
from app.models.invoice import B2BInvoice
from app.models.job import ConversionJob
from app.models.subscription import Subscription
from app.models.token import AppToken, RefreshToken
from app.models.usage import DailyUsage
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "AppToken",
    "DailyUsage",
    "Subscription",
    "B2BInvoice",
    "ConversionJob",
]
```

---

## 4. Контракты данных и Pydantic схемы (`backend/app/schemas/convert.py`)

Схемы Pydantic v2 задают строгий протокол обмена между клиентом, API и фоновыми воркерами.

```python
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadResponse(BaseModel):
    job_id: UUID
    status: Literal["queued"]
    stream_url: str

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    id: UUID
    status: Literal["pending", "queued", "processing", "completed", "failed"]
    progress_percent: int = Field(0, ge=0, le=100)
    current_step: str
    original_filename: str
    target_format: Literal["docx", "xlsx"]
    page_count: Optional[int] = None
    is_preview_only: bool = False
    preview_urls: list[str] = Field(default_factory=list)
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SSEProgressEvent(BaseModel):
    """Схема сериализации событий, публикуемых воркером в Redis Pub/Sub."""
    job_id: UUID
    status: Literal["pending", "queued", "processing", "completed", "failed"]
    progress_percent: int = Field(..., ge=0, le=100)
    current_step: str
    page_current: Optional[int] = None
    page_total: Optional[int] = None
    preview_urls: Optional[list[str]] = None
    download_url: Optional[str] = None
    is_preview_only: Optional[bool] = None
    error: Optional[str] = None


class ApiErrorResponse(BaseModel):
    error: str
    code: str
    upgrade_url: Optional[str] = None
```

---

## 5. Сервисный слой

### 5.1. `backend/app/services/storage_service.py`

Сервис хранилища расширяется методами для синхронного контекста RQ-воркеров и строгой установкой шифрования `AES256` на стороне сервера (Selectel S3 / MinIO).

```python
import asyncio
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()


class StorageService:
    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET_NAME
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version="s3v4",
                connect_timeout=3,
                read_timeout=15,
                retries={"max_attempts": 3},
            ),
        )

    # --- Синхронный API (для workers/tasks.py) ---

    def upload_bytes_sync(
        self, data: bytes, s3_key: str, content_type: str = "application/octet-stream"
    ) -> None:
        self._s3_client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def upload_file_sync(
        self, local_path: str, s3_key: str, content_type: str = "application/octet-stream"
    ) -> None:
        with open(local_path, "rb") as f:
            self._s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=f,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )

    def download_file_sync(self, s3_key: str, target_local_path: str) -> None:
        self._s3_client.download_file(self.bucket, s3_key, target_local_path)

    def download_bytes_sync(self, s3_key: str) -> bytes:
        response = self._s3_client.get_object(Bucket=self.bucket, Key=s3_key)
        return response["Body"].read()  # type: ignore[no-any-return]

    def generate_presigned_url_sync(
        self, s3_key: str, expires_in_seconds: int = 900, filename: str | None = None
    ) -> str:
        params: dict[str, str] = {"Bucket": self.bucket, "Key": s3_key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self._s3_client.generate_presigned_url(  # type: ignore[no-any-return]
            "get_object",
            Params=params,
            ExpiresIn=expires_in_seconds,
        )

    # --- Асинхронный API (для FastAPI controllers) ---

    async def ensure_bucket_exists(self) -> None:
        def _check() -> None:
            try:
                self._s3_client.head_bucket(Bucket=self.bucket)
            except Exception:
                self._s3_client.create_bucket(Bucket=self.bucket)

        await asyncio.to_thread(_check)

    async def check_health(self) -> bool:
        def _ping() -> bool:
            try:
                self._s3_client.head_bucket(Bucket=self.bucket)
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_ping)

    async def upload_bytes(
        self, data: bytes, s3_key: str, content_type: str = "application/octet-stream"
    ) -> None:
        await asyncio.to_thread(self.upload_bytes_sync, data, s3_key, content_type)

    async def download_bytes(self, s3_key: str) -> bytes:
        return await asyncio.to_thread(self.download_bytes_sync, s3_key)

    async def generate_presigned_url(
        self, s3_key: str, expires_in_seconds: int = 900, filename: str | None = None
    ) -> str:
        return await asyncio.to_thread(
            self.generate_presigned_url_sync, s3_key, expires_in_seconds, filename
        )


storage_service = StorageService()
```

### 5.2. `backend/app/services/converter_service.py`

Модуль `converter_service.py` инкапсулирует ключевые бизнес-правила продукта: валидацию PDF, дедупликацию, селектор очередей RQ и контроль дневных квот.

```python
import hashlib
import ipaddress
import secrets
from datetime import date
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ConversionJob
from app.models.usage import DailyUsage
from app.models.user import User

PDF_MAGIC_BYTES = b"%PDF-"
MAX_FILE_SIZE_FREE = 10 * 1024 * 1024   # 10 МБ
MAX_FILE_SIZE_PRO = 100 * 1024 * 1024   # 100 МБ


def validate_pdf_header_and_mime(header_bytes: bytes, filename: str | None, content_type: str | None) -> None:
    """Проверяет соответствие Magic Bytes (%PDF-) и MIME-типа."""
    if not header_bytes.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Файл не является корректным документом PDF",
                "code": "INVALID_FILE_TYPE",
            },
        )

    is_pdf_ext = filename is not None and filename.lower().endswith(".pdf")
    is_pdf_mime = content_type in ("application/pdf", "application/x-pdf", "binary/octet-stream")

    if not (is_pdf_ext or is_pdf_mime):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Недопустимый формат файла. Требуется расширение .pdf",
                "code": "INVALID_FILE_TYPE",
            },
        )


def validate_file_size(size_bytes: int, user: User | None) -> None:
    """Проверяет ограничение размера файла по тарифу."""
    is_pro = user is not None and user.plan == "pro"
    max_size = MAX_FILE_SIZE_PRO if is_pro else MAX_FILE_SIZE_FREE

    if size_bytes > max_size:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": f"Размер файла превышает лимит вашего тарифа ({max_size // (1024 * 1024)} МБ)",
                "code": "FILE_TOO_LARGE",
                "upgrade_url": "/pricing" if not is_pro else None,
            },
        )


def extract_ip_subnet(client_ip: str) -> str:
    """Извлекает /24 IPv4 или /64 IPv6 подсеть для учета лимитов."""
    try:
        ip = ipaddress.ip_address(client_ip)
        if ip.version == 4:
            network = ipaddress.ip_network(f"{client_ip}/24", strict=False)
            return str(network)
        network6 = ipaddress.ip_network(f"{client_ip}/64", strict=False)
        return str(network6)
    except ValueError:
        return "127.0.0.0/24"


def select_queue(user: User | None, file_size_bytes: int) -> str:
    """
    priority — PRO-пользователи (приоритетный воркер)
    fast     — Free, файл < 5 МБ (текстовый документ)
    heavy    — Free, файл >= 5 МБ (тяжелый скан или многостраничный отчет)
    """
    if user and user.plan == "pro":
        return "priority"
    if file_size_bytes < 5 * 1024 * 1024:
        return "fast"
    return "heavy"


async def check_deduplication(
    db: AsyncSession,
    user: User | None,
    sha256_checksum: str,
) -> ConversionJob | None:
    """Ищет активную или завершенную задачу за сегодня с идентичным хешем."""
    query = select(ConversionJob).where(
        ConversionJob.user_id == (user.id if user else None),
        ConversionJob.sha256_checksum == sha256_checksum,
        ConversionJob.usage_date == date.today(),
        ConversionJob.status.in_(["processing", "completed"]),
    ).limit(1)

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_and_increment_daily_limit(
    db: AsyncSession,
    user: User | None,
    fingerprint: str | None,
    client_ip: str,
) -> None:
    """Проверяет суточный лимит Free-тарифа (3 для логина, 1 для анонима) и фиксирует расход."""
    if user and user.plan == "pro":
        return  # Безлимитный PRO-тариф

    today = date.today()
    ip_subnet = extract_ip_subnet(client_ip)

    if user:
        # Авторизованный Free-пользователь: лимит 3 конвертации
        stmt = (
            insert(DailyUsage)
            .values(
                user_id=user.id,
                fingerprint=fingerprint,
                ip_subnet=ip_subnet,
                usage_date=today,
                conversion_count=1,
            )
            .on_conflict_do_update(
                constraint="uq_daily_user",
                set_={"conversion_count": DailyUsage.conversion_count + 1},
            )
            .returning(DailyUsage.conversion_count)
        )
        res = await db.execute(stmt)
        count = res.scalar_one()
        if count > 3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Исчерпан суточный лимит Free-тарифа (3 конвертации в день)",
                    "code": "FREE_LIMIT_EXCEEDED",
                    "upgrade_url": "/pricing",
                },
            )
    else:
        # Анонимный гость: лимит 1 конвертация в сутки
        if fingerprint:
            stmt_guest_fp = (
                insert(DailyUsage)
                .values(
                    user_id=None,
                    fingerprint=fingerprint,
                    ip_subnet=ip_subnet,
                    usage_date=today,
                    conversion_count=1,
                )
                .on_conflict_do_update(
                    index_elements=["fingerprint", "ip_subnet", "usage_date"],
                    set_={"conversion_count": DailyUsage.conversion_count + 1},
                )
                .returning(DailyUsage.conversion_count)
            )
            res = await db.execute(stmt_guest_fp)
        else:
            stmt_guest_ip = (
                insert(DailyUsage)
                .values(
                    user_id=None,
                    fingerprint=None,
                    ip_subnet=ip_subnet,
                    usage_date=today,
                    conversion_count=1,
                )
                .on_conflict_do_update(
                    index_elements=["ip_subnet", "usage_date"],
                    set_={"conversion_count": DailyUsage.conversion_count + 1},
                )
                .returning(DailyUsage.conversion_count)
            )
            res = await db.execute(stmt_guest_ip)

        count = res.scalar_one()
        if count > 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Для продолжения работы требуется бесплатная авторизация",
                    "code": "FREE_LIMIT_EXCEEDED",
                    "upgrade_url": "/pricing",
                },
            )


def create_anon_session_token() -> tuple[str, str]:
    """Генерирует пару: raw_token (для cookie) и sha256_hash (для хранения в БД)."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def verify_anon_session_token(raw_token: str, token_hash: str) -> bool:
    """Сравнивает raw токен из cookie с хешем в conversion_jobs."""
    computed_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return secrets.compare_digest(computed_hash, token_hash)
```

---

## 6. Фоновые воркеры и обработка задач (`backend/app/workers/`)

### 6.1. Точка входа воркера `backend/app/workers/worker.py`

Воркер запускается в изолированном контейнере Docker и обслуживает очереди `priority`, `fast`, `heavy`. При старте процесса вызывается функция `_warmup_docling()`, загружающая ML-модели парсинга в оперативную память.

```python
import base64
import os
import signal
import sys
import tempfile
import redis
import structlog
from rq import Connection, Worker

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Минимальный валидный 1-страничный PDF-документ (Hello World)
_WARMUP_PDF_B64 = (
    "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2"
    "JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPD4KZW5k"
    "b2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2"
    "MTIgNzkyXQo+PgplbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5"
    "IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAp0cmFpbGVy"
    "Cjw8Ci9TaXplIDQKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjE5MgolJUVPRg=="
)


def _warmup_docling() -> None:
    """Превентивный прогрев моделей Docling перед приемом реальных клиентских задач."""
    logger.info("worker_warmup_docling_started")
    try:
        from docling.document_converter import DocumentConverter

        pdf_bytes = base64.b64decode(_WARMUP_PDF_B64)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            f.flush()
            temp_path = f.name

        converter = DocumentConverter()
        converter.convert(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.info("worker_warmup_docling_completed")
    except Exception as exc:
        logger.warning("worker_warmup_docling_skipped", reason=str(exc))


def run_worker() -> None:
    """Основной цикл RQ-воркера."""
    logger.info(
        "worker_starting",
        environment=settings.ENVIRONMENT,
        max_jobs=settings.WORKER_MAX_JOBS,
        job_timeout=settings.WORKER_JOB_TIMEOUT,
    )

    _warmup_docling()

    redis_conn = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )

    queues = ["priority", "fast", "heavy"]
    with Connection(redis_conn):
        worker = Worker(queues)
        worker.work(max_jobs=settings.WORKER_MAX_JOBS)


if __name__ == "__main__":
    try:
        run_worker()
    except (KeyboardInterrupt, SystemExit):
        logger.info("worker_stopped")
        sys.exit(0)
```

### 6.2. Фоновые задачи `backend/app/workers/tasks.py`

```python
import json
import os
import subprocess
import tempfile
import time
from decimal import Decimal
from uuid import UUID

import fitz  # PyMuPDF
import redis
import structlog
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.job import ConversionJob
from app.models.user import User
from app.schemas.convert import SSEProgressEvent
from app.services.storage_service import storage_service

logger = structlog.get_logger()
settings = get_settings()

# Синхронная сессия SQLAlchemy для изоляции в процессах RQ
_sync_engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
_SyncSession = sessionmaker(bind=_sync_engine)

# Синхронный Redis для отправки сообщений в канал Pub/Sub
_redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
)


def publish_progress(
    job_id: UUID,
    percent: int,
    step: str,
    page_current: int | None = None,
    page_total: int | None = None,
) -> None:
    event = SSEProgressEvent(
        job_id=job_id,
        status="processing",
        progress_percent=percent,
        current_step=step,
        page_current=page_current,
        page_total=page_total,
    )
    _redis_client.publish(f"job:{job_id}:progress", event.model_dump_json())


def publish_complete(
    job_id: UUID,
    preview_urls: list[str],
    download_url: str | None,
    is_preview_only: bool,
) -> None:
    event = SSEProgressEvent(
        job_id=job_id,
        status="completed",
        progress_percent=100,
        current_step="Готово к скачиванию",
        preview_urls=preview_urls,
        download_url=download_url,
        is_preview_only=is_preview_only,
    )
    _redis_client.publish(f"job:{job_id}:progress", event.model_dump_json())


def publish_error(job_id: UUID, error_code: str, step_msg: str) -> None:
    event = SSEProgressEvent(
        job_id=job_id,
        status="failed",
        progress_percent=0,
        current_step=step_msg,
        error=error_code,
    )
    _redis_client.publish(f"job:{job_id}:progress", event.model_dump_json())


def _validate_pdf_with_qpdf(local_pdf_path: str) -> None:
    """Проверяет синтаксическую валидность и отсутствие шифрования паролем через qpdf."""
    cmd = ["qpdf", "--check", local_pdf_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        logger.warning("qpdf_validation_failed", returncode=res.returncode, stderr=res.stderr)
        raise ValueError("CORRUPTED_PDF")


def _render_preview(job_id: UUID, input_path: str) -> tuple[int, list[str]]:
    """
    Рендерит страницы 1-2 в JPEG с качеством 150 DPI через PyMuPDF (fitz).
    Возвращает (общее количество страниц, список ключей S3).
    """
    doc = fitz.open(input_path)
    total_pages = len(doc)
    pages_to_render = min(total_pages, 2)
    s3_preview_keys: list[str] = []

    for idx in range(pages_to_render):
        page = doc[idx]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")

        s3_key = f"temp/{job_id}/preview_p{idx + 1}.jpg"
        storage_service.upload_bytes_sync(img_bytes, s3_key, content_type="image/jpeg")
        s3_preview_keys.append(s3_key)

    doc.close()
    return total_pages, s3_preview_keys


def _run_docling(target_format: str, input_path: str, output_path: str) -> None:
    """Запускает парсинг Docling и экспортирует в .docx или .xlsx."""
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(input_path)

    if len(result.document.pages) == 0:
        raise ValueError("CONVERSION_FAILED")

    if target_format == "docx":
        result.document.save_as_docx(output_path)
    elif target_format == "xlsx":
        result.document.save_as_xlsx(output_path)
    else:
        raise ValueError("UNSUPPORTED_TARGET_FORMAT")


def parse_and_convert(job_id_str: str) -> None:
    """Главная задача воркера RQ: конвертирует PDF и транслирует статус."""
    job_id = UUID(job_id_str)
    start_time = time.perf_counter()

    logger.info("job_processing_started", job_id=str(job_id))

    with _SyncSession() as session:
        job = session.execute(
            select(ConversionJob).where(ConversionJob.id == job_id)
        ).scalar_one_or_none()
        if not job:
            logger.error("job_not_found_in_worker", job_id=str(job_id))
            return

        user_plan = "free"
        if job.user_id:
            user = session.execute(
                select(User).where(User.id == job.user_id)
            ).scalar_one_or_none()
            if user:
                user_plan = user.plan

        job.status = "processing"
        session.commit()

    publish_progress(job_id, 5, "Начинаем обработку...")

    temp_dir = tempfile.mkdtemp(prefix=f"cleandoc_{job_id}_")
    local_input = os.path.join(temp_dir, "input.pdf")

    try:
        # Шаг 1: Скачивание из S3
        publish_progress(job_id, 10, "Получение документа из хранилища...")
        storage_service.download_file_sync(job.s3_input_key, local_input)

        # Шаг 2: Проверка целостности qpdf
        publish_progress(job_id, 20, "Проверка целостности документа...")
        _validate_pdf_with_qpdf(local_input)

        # Шаг 3: Рендер JPEG превью через PyMuPDF
        publish_progress(job_id, 30, "Создание превью (страницы 1–2)...")
        total_pages, preview_keys = _render_preview(job_id, local_input)

        # Определение признака is_preview_only (Free + документ > 2 стр.)
        is_preview_only = user_plan == "free" and total_pages > 2

        s3_output_key: str | None = None

        if not is_preview_only:
            publish_progress(
                job_id,
                50,
                f"Анализ структуры документа (стр. 1 из {total_pages})...",
                page_current=1,
                page_total=total_pages,
            )

            local_output = os.path.join(temp_dir, f"output.{job.target_format}")
            _run_docling(job.target_format, local_input, local_output)

            publish_progress(job_id, 85, f"Формирование файла {job.target_format.upper()}...")
            s3_output_key = f"temp/{job_id}/output.{job.target_format}"

            mime_type = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if job.target_format == "docx"
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            storage_service.upload_file_sync(local_output, s3_output_key, content_type=mime_type)

        duration = Decimal(str(round(time.perf_counter() - start_time, 3)))

        # Обновление статуса в БД
        with _SyncSession() as session:
            session.execute(
                update(ConversionJob)
                .where(ConversionJob.id == job_id)
                .values(
                    status="completed",
                    page_count=total_pages,
                    s3_preview_keys=preview_keys,
                    s3_output_key=s3_output_key,
                    is_preview_only=is_preview_only,
                    processing_seconds=duration,
                )
            )
            session.commit()

        download_url = f"/api/v1/convert/jobs/{job_id}/download" if not is_preview_only else None
        publish_complete(job_id, preview_keys, download_url, is_preview_only)

        logger.info(
            "job_processing_completed",
            job_id=str(job_id),
            duration_seconds=float(duration),
            pages=total_pages,
            preview_only=is_preview_only,
        )

    except Exception as exc:
        duration_err = Decimal(str(round(time.perf_counter() - start_time, 3)))
        err_msg = str(exc)
        logger.error("job_processing_failed", job_id=str(job_id), error=err_msg)

        with _SyncSession() as session:
            session.execute(
                update(ConversionJob)
                .where(ConversionJob.id == job_id)
                .values(
                    status="failed",
                    error_message=err_msg,
                    processing_seconds=duration_err,
                )
            )
            session.commit()

        publish_error(job_id, err_msg, "Ошибка конвертации")
        raise
    finally:
        # Гарантированная очистка временных локальных файлов
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
```

---

## 7. HTTP контроллеры и SSE стриминг (`backend/app/api/v1/endpoints/convert.py`)

### 7.1. Реализация эндпоинтов

```python
import asyncio
import hashlib
from typing import Literal
from uuid import UUID

import redis.asyncio as aioredis
import structlog
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse, StreamingResponse
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.job import ConversionJob
from app.models.user import User
from app.schemas.convert import JobStatusResponse, SSEProgressEvent, UploadResponse
from app.services import converter_service
from app.services.storage_service import storage_service

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_pdf(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    target_format: Literal["docx", "xlsx"] = Form(...),
    fingerprint: str | None = Form(None),
    anon_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Принимает PDF, валидирует Magic Bytes, выполняет дедупликацию,
    проверяет лимит тарифа, загружает входной файл в S3 и ставит задачу в RQ.
    """
    header = await file.read(1024)
    converter_service.validate_pdf_header_and_mime(header, file.filename, file.content_type)
    await file.seek(0)

    content = await file.read()
    file_size = len(content)
    await file.seek(0)

    # В Slice 1 текущий пользователь берется из контекста сессии (или None для гостей)
    current_user: User | None = getattr(request.state, "user", None)
    converter_service.validate_file_size(file_size, current_user)

    sha256_checksum = hashlib.sha256(content).hexdigest()

    # Дедупликация: проверка наличия активной/готовой задачи за сегодня
    existing_job = await converter_service.check_deduplication(db, current_user, sha256_checksum)
    if existing_job:
        logger.info("deduplication_hit", job_id=str(existing_job.id), sha256=sha256_checksum)
        return UploadResponse(
            job_id=existing_job.id,
            status="queued",
            stream_url=f"/api/v1/convert/jobs/{existing_job.id}/stream",
        )

    # Проверка дневного лимита Free-тарифа
    client_ip = request.client.host if request.client else "127.0.0.1"
    await converter_service.check_and_increment_daily_limit(db, current_user, fingerprint, client_ip)

    # Идентификатор сессии гостя для безопасного скачивания
    session_token_hash: str | None = None
    if current_user is None:
        if anon_session:
            session_token_hash = hashlib.sha256(anon_session.encode("utf-8")).hexdigest()
        else:
            raw_token, session_token_hash = converter_service.create_anon_session_token()
            response.set_cookie(
                key="anon_session",
                value=raw_token,
                max_age=7200,  # 2 часа TTL
                httponly=True,
                samesite="lax",
                secure=(settings.ENVIRONMENT == "prod"),
            )

    job_id = UUID(int=asyncio.get_event_loop().time_ns() ^ id(content))  # Уникальный временный seed
    s3_input_key = f"temp/{job_id}/input.pdf"

    await storage_service.upload_bytes(content, s3_input_key, content_type="application/pdf")

    new_job = ConversionJob(
        id=job_id,
        user_id=current_user.id if current_user else None,
        session_token_hash=session_token_hash,
        target_format=target_format,
        original_filename=file.filename or "document.pdf",
        file_size_bytes=file_size,
        sha256_checksum=sha256_checksum,
        status="queued",
        s3_input_key=s3_input_key,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # Постановка задачи в очередь RQ
    queue_name = converter_service.select_queue(current_user, file_size)
    from app.workers.tasks import parse_and_convert
    import redis as sync_redis

    r_sync = sync_redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
    )
    rq_queue = Queue(queue_name, connection=r_sync)
    rq_queue.enqueue(parse_and_convert, str(new_job.id), job_timeout=settings.WORKER_JOB_TIMEOUT)

    logger.info("job_enqueued", job_id=str(new_job.id), queue=queue_name)

    return UploadResponse(
        job_id=new_job.id,
        status="queued",
        stream_url=f"/api/v1/convert/jobs/{new_job.id}/stream",
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_snapshot(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """
    Polling fallback: возвращает моментальный снимок задачи.
    Устраняет race condition при быстром завершении конвертации до открытия SSE.
    """
    job = await db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Задача не найдена или срок хранения истек", "code": "JOB_NOT_FOUND"},
        )

    download_url = f"/api/v1/convert/jobs/{job.id}/download" if job.status == "completed" and not job.is_preview_only else None

    # Определение человекочитаемого статуса шага
    step_descriptions = {
        "pending": "Ожидание в очереди...",
        "queued": "Задача в очереди обработки...",
        "processing": "Обработка документа...",
        "completed": "Готово к скачиванию",
        "failed": "Ошибка конвертации",
    }
    current_step = step_descriptions.get(job.status, "Обработка...")
    progress_val = 100 if job.status == "completed" else 0

    return JobStatusResponse(
        id=job.id,
        status=job.status,  # type: ignore[arg-type]
        progress_percent=progress_val,
        current_step=current_step,
        original_filename=job.original_filename,
        target_format=job.target_format,  # type: ignore[arg-type]
        page_count=job.page_count,
        is_preview_only=job.is_preview_only,
        preview_urls=job.s3_preview_keys,
        download_url=download_url,
        error_message=job.error_message,
        expires_at=job.expires_at,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Server-Sent Events (SSE) стриминг прогресса обработки документа.
    Включает keepalive комментарии каждые 15 секунд для предотвращения обрыва Caddy.
    """
    job = await db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Задача не найдена", "code": "JOB_NOT_FOUND"},
        )

    async def event_generator():
        r_async = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r_async.pubsub()
        channel = f"job:{job_id}:progress"
        await pubsub.subscribe(channel)

        try:
            while True:
                try:
                    # Ожидание сообщения из Redis Pub/Sub с таймаутом 15 секунд для keepalive
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=15.0,
                    )
                    if message and message.get("type") == "message":
                        data_str = message["data"]
                        event = SSEProgressEvent.model_validate_json(data_str)
                        sse_type = "complete" if event.status == "completed" else "error" if event.status == "failed" else "progress"
                        yield f"event: {sse_type}\ndata: {data_str}\n\n"

                        if event.status in ("completed", "failed"):
                            break
                except asyncio.TimeoutError:
                    # SSE keepalive comment для предотвращения сброса Caddy proxy
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            logger.info("sse_client_disconnected", job_id=str(job_id))
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await r_async.aclose()

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), headers=headers, media_type="text/event-stream")


@router.get("/jobs/{job_id}/download")
async def download_converted_file(
    job_id: UUID,
    request: Request,
    anon_session: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Выдает 307 Redirect на временный S3 pre-signed URL готового документа.
    Проверяет права авторства задачи и блокирует скачивание при is_preview_only = True.
    """
    job = await db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Файл не найден или срок его хранения истек", "code": "JOB_NOT_FOUND"},
        )

    if job.status != "completed" or not job.s3_output_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Обработка файла еще не завершена", "code": "CONVERSION_NOT_READY"},
        )

    # Проверка авторства
    current_user: User | None = getattr(request.state, "user", None)
    if job.user_id:
        if not current_user or current_user.id != job.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Доступ к файлу запрещен", "code": "ACCESS_DENIED"},
            )
    else:
        # Проверка гостевой сессии
        if not anon_session or not job.session_token_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Сессия гостя не найдена", "code": "ACCESS_DENIED"},
            )
        if not converter_service.verify_anon_session_token(anon_session, job.session_token_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Доступ к чужой задаче запрещен", "code": "ACCESS_DENIED"},
            )

    # Проверка ограничения Free-тарифа (многостраничный документ)
    if job.is_preview_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Для скачивания полного многостраничного документа оформите тариф PRO",
                "code": "UPGRADE_REQUIRED",
                "upgrade_url": "/pricing",
            },
        )

    base_name = job.original_filename.rsplit(".", 1)[0]
    out_filename = f"{base_name}.{job.target_format}"
    presigned_url = await storage_service.generate_presigned_url(
        job.s3_output_key,
        expires_in_seconds=900,  # 15 минут
        filename=out_filename,
    )
    return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
```

### 7.2. Регистрация в `backend/app/api/v1/router.py`

```python
from fastapi import APIRouter

from app.api.v1.endpoints import convert, health

api_v1_router = APIRouter()

api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(convert.router, prefix="/convert", tags=["convert"])
```

---

## 8. Инфраструктура воркера (Docker & deploy)

### 8.1. `backend/Dockerfile.worker`

Dockerfile фонового воркера включает установку утилит `qpdf`, системных библиотек рендеринга `libgl1`, графических шрифтов и предзагрузку артефактов `Docling` в офлайн-режиме:

```dockerfile
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HUGGINGFACE_HUB_VERBOSITY=error \
    DOCLING_ARTIFACTS_PATH=/app/.docling

WORKDIR /app

# Установка системных зависимостей: qpdf, OpenGL для PyMuPDF/EasyOCR, шрифты
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    qpdf \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-rus \
    tesseract-ocr-eng \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

# Создание локальной директории кеша моделей Docling
RUN mkdir -p /app/.docling && chmod 777 /app/.docling

CMD ["python", "-m", "app.workers.worker"]
```

### 8.2. Конфигурация воркера в `deploy/docker-compose.yml`

```yaml
  worker:
    build:
      context: ../backend
      dockerfile: Dockerfile.worker
    container_name: cleandoc_worker
    restart: unless-stopped
    command: ["python", "-m", "app.workers.worker"]
    environment:
      ENVIRONMENT: dev
      DEBUG: "true"
      POSTGRES_SERVER: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER:-cleandoc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-secure_pg_password}
      POSTGRES_DB: ${POSTGRES_DB:-cleandoc_db}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      S3_ENDPOINT_URL: http://minio:9000
      S3_ACCESS_KEY_ID: ${S3_ACCESS_KEY_ID:-minioadmin}
      S3_SECRET_ACCESS_KEY: ${S3_SECRET_ACCESS_KEY:-minioadmin}
      S3_BUCKET_NAME: ${S3_BUCKET_NAME:-cleandoc-dev}
      WORKER_JOB_TIMEOUT: 180
      WORKER_MAX_JOBS: 50
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 4096M
    volumes:
      - ../backend/app:/app/app:ro
      - /tmp/cleandoc_worker_temp:/tmp
```

---

## 9. Тестовый харнес и бенчмарк 20 документов

### 9.1. Программные генераторы фикстур в `backend/tests/conftest.py`

Для исключения хранения бинарных PDF в репозитории тесты используют программную генерацию через `PyMuPDF` (`fitz`):

```python
import fitz
import pytest


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
```

### 9.2. Тестовый набор `backend/tests/test_convert.py`

```python
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ConversionJob
from app.services.converter_service import select_queue


@pytest.mark.asyncio
async def test_upload_rejects_fake_pdf(async_client: AsyncClient, sample_fake_pdf: bytes) -> None:
    """Проверка возврата 400 INVALID_FILE_TYPE при нарушении Magic Bytes."""
    files = {"file": ("test.pdf", BytesIO(sample_fake_pdf), "application/pdf")}
    data = {"target_format": "docx"}
    resp = await async_client.post("/api/v1/convert/upload", files=files, data=data)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_FILE_TYPE"


@pytest.mark.asyncio
async def test_upload_success_queued(
    async_client: AsyncClient, sample_pdf_2page: bytes, mock_storage: MagicMock
) -> None:
    """Проверка успешной загрузки валидного PDF и получения 202 с job_id."""
    with patch("rq.Queue.enqueue", return_value=MagicMock()):
        files = {"file": ("invoice.pdf", BytesIO(sample_pdf_2page), "application/pdf")}
        data = {"target_format": "docx", "fingerprint": "fp_test_123"}
        resp = await async_client.post("/api/v1/convert/upload", files=files, data=data)
        assert resp.status_code == 202
        body = resp.json()
        assert "job_id" in body
        assert body["status"] == "queued"
        assert body["stream_url"].endswith("/stream")
        assert "anon_session" in resp.cookies


@pytest.mark.asyncio
async def test_queue_selection_logic() -> None:
    """Проверка разделения очередей: priority, fast, heavy."""
    pro_user = MagicMock(plan="pro")
    free_user = MagicMock(plan="free")

    assert select_queue(pro_user, 1024) == "priority"
    assert select_queue(pro_user, 20 * 1024 * 1024) == "priority"
    assert select_queue(free_user, 2 * 1024 * 1024) == "fast"
    assert select_queue(free_user, 7 * 1024 * 1024) == "heavy"
    assert select_queue(None, 3 * 1024 * 1024) == "fast"
    assert select_queue(None, 8 * 1024 * 1024) == "heavy"


@pytest.mark.asyncio
async def test_job_snapshot_not_found(async_client: AsyncClient) -> None:
    """Проверка возврата 404 для несуществующего job_id."""
    resp = await async_client.get(f"/api/v1/convert/jobs/{uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_download_preview_only_blocked(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Проверка блокировки скачивания с кодом 403 UPGRADE_REQUIRED при is_preview_only."""
    job = ConversionJob(
        id=uuid4(),
        target_format="docx",
        original_filename="contract.pdf",
        file_size_bytes=2048,
        status="completed",
        s3_input_key="temp/test/input.pdf",
        s3_output_key="temp/test/output.docx",
        is_preview_only=True,
    )
    db_session.add(job)
    await db_session.commit()

    resp = await async_client.get(f"/api/v1/convert/jobs/{job.id}/download")
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "UPGRADE_REQUIRED"
    assert resp.json()["detail"]["upgrade_url"] == "/pricing"
```

### 9.3. Бенчмарк: 20 эталонных российских B2B-документов

Для проверки конвертации создается матрица сценариев:

| No | Тип документа | Специфика верстки | Целевой формат | Ожидаемый результат |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Акт выполненных работ | Банковская шапка, подписи, печати | `docx` | Сохранение двухколоночных реквизитов |
| 2 | Счет на оплату 1С | Таблица с номенклатурой, НДС | `xlsx` | Корректные формулы/ячейки сумм |
| 3 | Товарная накладная ТОРГ-12 | Широкая таблица на 15 колонок | `xlsx` | Корректная сетка ячеек без объединений со смещением |
| 4 | УПД (Универсальный документ) | Комплексная сетка, статус (1) | `xlsx` | Строгое совпадение строк |
| 5 | Оборотно-сальдовая ведомость | Многостраничная вложенная иерархия | `xlsx` | Числовые значения в ячейках |
| 6 | Ведомость зарплаты (Т-51) | Большое число строк и кодов | `xlsx` | Точные строки сотрудников |
| 7 | Договор поставки (2 колонки) | Двухколоночный текст условий | `docx` | Чистый текстовый поток Word |
| 8 | Договор аренды с графиком | Текст + таблица платежей | `docx` | Таблица платежей внутри Word |
| 9 | Спецификация оборудования | Таблица с артикулами и ценами | `xlsx` | Артикулы без автоформатирования в дату |
| 10 | Счет-фактура (Пост. 1137) | Регламентированные графы | `xlsx` | Заголовки колонок 1–14 |
| 11 | Акт сверки расчетов | Две параллельные таблицы Дт/Кт | `xlsx` | Синхронность строк периода |
| 12 | Штатное расписание (Т-3) | Таблица окладов и надбавок | `xlsx` | Числовой формат окладов |
| 13 | Табель учета времени (Т-13) | Сетка кодов Я/Н/В | `xlsx` | Календарная матрица дат |
| 14 | Путевой лист | Лицевая и оборотная стороны | `docx` | Сохранение блоков маршрутов |
| 15 | Смета строительных работ | Иерархические разделы с итогами | `xlsx` | Структура разделов сметы |
| 16 | Справка 2-НДФЛ | Блоки доходов по месяцам | `xlsx` | Таблица кодов доходов |
| 17 | Коммерческое предложение | Врезки текста, списки, таблицы | `docx` | Структурные заголовки Word |
| 18 | Скан акта с графической печатью | Текстовый слой + векторная графика | `docx` | Текст распознан без мусора |
| 19 | Скан договора с поворотом 90° | Альбомная ориентация страниц | `docx` | Автоповорот и чистый текст |
| 20 | Карточка предприятия | Таблица реквизитов и банков | `docx` | Точные номера расчетных счетов |

---

## 10. Плавное перетекание в Slice 2 (Auth & UX Seams & Extension Points)

Slice 1 закладывает строгие архитектурные швы (Seams) для подключения клиентского интерфейса и аутентификации в Slice 2:

### 10.1. Frontend-стык (TypeScript контракты и Zustand стор)

В Slice 2 создается клиентский Zustand-стор `frontend/src/store/useConverterStore.ts`. Контракт Slice 1 полностью готов к интеграции:

```typescript
// frontend/src/lib/types.ts
export type JobStatus = 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
export type TargetFormat = 'docx' | 'xlsx';

export interface SSEProgressPayload {
  job_id: string;
  status: JobStatus;
  progress_percent: number;
  current_step: string;
  page_current?: number;
  page_total?: number;
  preview_urls?: string[];
  download_url?: string | null;
  is_preview_only?: boolean;
  error?: string | null;
}

export interface UploadResponse {
  job_id: string;
  status: 'queued';
  stream_url: string;
}
```

Клиентский хук подписки на SSE использует URL `/api/v1/convert/jobs/${jobId}/stream`, автоматически переключаясь на `GET /jobs/${jobId}` при получении завершающего события.

### 10.2. Стык перевода гостевых задач (Anonymous Claiming Seam)

Когда анонимный пользователь выполняет конвертацию в Slice 1, задача помечается `session_token_hash` из cookie `anon_session`.
В Slice 2 при успешной аутентификации через Magic Link (`POST /api/v1/auth/verify-code`) или Telegram (`POST /api/v1/auth/telegram`) сервис аутентификации выполняет сквозное связывание:

```sql
UPDATE conversion_jobs
SET user_id = :authenticated_user_id
WHERE session_token_hash = :anon_token_hash
  AND user_id IS NULL;
```

Это гарантирует, что пользователь не теряет результаты выполненной конвертации и сразу видит документ в личном кабинете.

### 10.3. Стык апселла PRO (Upsell PRO Modal Seam)

При `is_preview_only = True` эндпоинт `GET /download` возвращает статус `403` со структурой:

```json
{
  "error": "Для скачивания полного многостраничного документа оформите тариф PRO",
  "code": "UPGRADE_REQUIRED",
  "upgrade_url": "/pricing"
}
```

Фронтенд в Slice 2 перехватывает этот ответ и открывает модальное окно перехода на тариф PRO, не прерывая показ первых 2 страниц в превьювере.

### 10.4. Стык защиты лимитов (Rate Limiting & Daily Usage Seam)

Таблица `daily_usage` и функция `check_and_increment_daily_limit` в Slice 1 готовы для отдачи профиля пользователя в Slice 2 (`GET /api/v1/users/me`):
- `conversions_today` рассчитывается через `SELECT conversion_count FROM daily_usage WHERE user_id = :id AND usage_date = CURRENT_DATE`.
- `conversions_limit` отдается как `3` для Free или `500` для PRO.

---

## 11. Пошаговый регламент реализации (Step-by-Step Implementation Guide)

Реализация функциональности Slice 1 выполняется строго в следующей последовательности:

```text
Шаг 1: Alembic миграция 0002_conversion_jobs.py
  ├── Создание файла backend/alembic/versions/0002_conversion_jobs.py
  └── Применение миграции: cd backend && uv run alembic upgrade head

Шаг 2: Модели SQLAlchemy 2.0
  ├── Создание backend/app/models/job.py
  ├── Обновление backend/app/models/user.py (relationship jobs)
  └── Экспорт ConversionJob в backend/app/models/__init__.py

Шаг 3: DTO схемы Pydantic v2
  ├── Создание backend/app/schemas/convert.py
  └── Экспорт схем в backend/app/schemas/__init__.py

Шаг 4: Расширение StorageService
  └── Добавление синхронных методов и ServerSideEncryption="AES256" в backend/app/services/storage_service.py

Шаг 5: Сервис конвертации ConverterService
  └── Реализация backend/app/services/converter_service.py (валидация, sha256, дедупликация, лимиты, очереди)

Шаг 6: Фоновые воркеры
  ├── Реализация tasks.py (_validate_pdf_with_qpdf, _render_preview, _run_docling, parse_and_convert)
  └── Реализация worker.py (_warmup_docling, rq worker priority fast heavy)

Шаг 7: Контроллеры API и роутер
  ├── Реализация эндпоинтов в backend/app/api/v1/endpoints/convert.py (upload, snapshot, stream, download)
  └── Регистрация convert.router в backend/app/api/v1/router.py

Шаг 8: Обновление Dockerfile.worker и манифеста Compose
  ├── backend/Dockerfile.worker (установка qpdf, tesseract, системных библиотек)
  └── deploy/docker-compose.yml (проверка volumes, mem_limit 4g)

Шаг 9: Тестовый харнес
  ├── Добавление фикстур в backend/tests/conftest.py
  └── Создание набора тестов в backend/tests/test_convert.py

Шаг 10: Сквозная валидация make gate
  └── Запуск make gate локально и устранение всех замечаний линтеров и тестов
```

---

## 12. Контрольный чеклист и верификация `make gate`

Перед сдачей среза Slice 1 разработчик или агент обязан проверить выполнение всех контрольных точек:

- [ ] `cd backend && uv run ruff check app tests` — 0 предупреждений.
- [ ] `cd backend && uv run ruff format --check app tests` — форматирование чистое.
- [ ] `cd backend && uv run mypy --strict app` — 0 ошибок типизации во всех модулях.
- [ ] `cd backend && uv run pytest -v tests` — все тесты проходят успешно, покрытие >= 85%.
- [ ] `markdownlint "**/*.md" --ignore node_modules` — документация валидна.
- [ ] `docker compose -f deploy/docker-compose.yml config --quiet` — конфигурация валидна.
- [ ] `make gate` выполняется одной командой и завершается с кодом `0`.

---

## 13. Связанные документы

- [Single Source of Truth (`docs/TECH.md`)](./TECH.md) — единый источник технической спецификации.
- [Архитектурный обзор (`docs/ARCHITECTURE.md`)](./ARCHITECTURE.md) — компонентные и контейнерные диаграммы C4.
- [Регламент разработки (`AGENTS.md`)](../AGENTS.md) — правила разработки, безопасность и конвенции коммитов.
- [Спецификация Slice 0: Foundation (`docs/SLICE-00.md`)](./SLICE-00.md) — спецификация монорепозитория и инфраструктуры.
- **Следующий этап:** Спецификация Slice 2 (Auth & UX) — клиентский интерфейс, Passwordless авторизация и личный кабинет.
