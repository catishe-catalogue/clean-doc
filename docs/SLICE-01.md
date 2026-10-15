# SLICE-01: Processing — Спецификация реализации

> **Статус:** Действующий / Ready for Implementation
> **Версия:** v0.3
> **Дата:** 15 октября 2026 г.
> **Спринт:** 2 (Дни 15–28)
> **Зависимости:** Slice 0 (Foundation) — монорепозиторий, `docker-compose.yml`, `make gate`, базовые модели БД

---

## 0. Цель и Definition of Done

**Цель Slice 1:** реализовать полный пайплайн конвертации PDF → DOCX/XLSX в фоновых воркерах RQ
с передачей прогресса по SSE и сохранением результата в S3.

### Definition of Done (DoD)

- [ ] `POST /api/v1/convert/upload` принимает PDF, сохраняет в S3, ставит задачу в RQ, возвращает `202` с `job_id`.
- [ ] Воркер RQ выполняет полный цикл: скачивает PDF из S3 → `qpdf` нарезка превью → `Docling` конвертация → загружает результат в S3 → публикует прогресс в Redis Pub/Sub.
- [ ] `GET /api/v1/convert/jobs/{job_id}/stream` стримит прогресс через SSE (события `progress`, `complete`, `error`).
- [ ] `GET /api/v1/convert/jobs/{job_id}/download` возвращает `307 redirect` на pre-signed S3 URL.
- [ ] Статус задачи (`pending` → `queued` → `processing` → `completed`/`failed`) корректно отражается в PostgreSQL.
- [ ] При превышении `job_timeout = 180` секунд задача переходит в `failed`, пользователь получает сообщение.
- [ ] Все тесты (`make gate`) проходят.
- [ ] Валидация на 20 тестовых PDF: акты, счета, отчеты 1C, многостраничные договора.

---

## 1. Компоненты и модули

### 1.1. Новые файлы, создаваемые в рамках Slice 1

```text
backend/
  app/
    api/v1/endpoints/
      convert.py            # POST /upload, GET /jobs/{id}/stream, GET /jobs/{id}/download
    services/
      converter_service.py  # координация: валидация PDF, постановка задачи, pre-signed URLs
      storage_service.py    # S3 клиент (boto3 sync + run_in_executor): upload, download, presign
    workers/
      worker.py             # точка входа rq worker с warmup-инициализацией Docling
      tasks.py              # фоновые задачи: parse_and_convert, render_preview
    models/
      job.py                # SQLAlchemy модель conversion_jobs
    schemas/
      convert.py            # Pydantic схемы UploadResponse, JobStatusResponse
  alembic/versions/
    0002_conversion_jobs.py # миграция таблицы conversion_jobs
```

---

## 2. Контракт API (детальный)

### 2.1. `POST /api/v1/convert/upload`

**Назначение:** принять PDF, провалидировать, сохранить в S3, поставить задачу в очередь RQ.

**Request:**

- `Content-Type: multipart/form-data`
- `file` (UploadFile, обязательный): бинарный PDF
- `target_format` (str, обязательный): `"docx"` или `"xlsx"`
- `fingerprint` (str, опциональный, `max_length=128`): отпечаток браузера для учета Free-лимита

**Валидация на входе (порядок обязательный):**

1. MIME-тип `Content-Type: application/pdf` ИЛИ расширение `.pdf`.
2. Magic Bytes: первые 4 байта файла == `%PDF` (0x25 0x50 0x44 0x46).
3. Размер файла <= 10 МБ (Free-тариф) или <= 100 МБ (PRO-тариф). Лимит тарифа определяется из JWT токена или анонимного статуса.
4. Проверка суточного лимита:
   - Авторизованный пользователь: `daily_usage.conversion_count` по `user_id`.
   - Аноним с `fingerprint`: по `(fingerprint, ip_subnet, usage_date)`.
   - Аноним без `fingerprint` (редкий случай): по `(ip_subnet, usage_date)`.

**Логика:**

```python
# Псевдокод порядка операций в endpoint
async def upload_pdf(file, target_format, fingerprint, request, db, user):
    validate_file_type(file)        # Magic Bytes + MIME
    validate_file_size(file, user)  # 10MB / 100MB
    sha256 = compute_sha256(file)   # SHA-256 входного PDF

    # Дедупликация через PostgreSQL (индекс idx_jobs_dedup)
    # Redis SET-подход не используется: ненадёжен при перезапуске Redis.
    existing_job = await check_dedup_pg(sha256, user, db)  # SELECT по (user_id, sha256, CURRENT_DATE)
    if existing_job:
        return UploadResponse(
            job_id=existing_job.id,
            status=existing_job.status,
            stream_url=f"/api/v1/convert/jobs/{existing_job.id}/stream"
        )

    check_daily_limit(user, fingerprint, request.client.host, db)

    s3_key = f"temp/{uuid4()}/input.pdf"
    await storage_service.upload(file, s3_key)

    # Токен доступа для анонимных пользователей
    session_token_hash: str | None = None
    if user is None:
        raw_token = f"{uuid4()}{request.client.host}{request.headers.get('user-agent', '')}"
        session_token_hash = sha256hex(raw_token)
        set_anon_session_cookie(response, session_token_hash)  # HttpOnly, TTL 2h

    job = ConversionJob(
        user_id=user.id if user else None,
        session_token_hash=session_token_hash,
        target_format=target_format,
        original_filename=file.filename,
        file_size_bytes=file.size,
        sha256_checksum=sha256,
        usage_date=date.today(),  # заполняется явно для индекса дедупликации
        status="queued",
        s3_input_key=s3_key,
    )
    db.add(job); await db.commit()

    queue_name = select_queue(user, file.size)
    rq_queue = Queue(queue_name, connection=redis_conn)
    rq_queue.enqueue(parse_and_convert, job.id, job_timeout=180)

    return UploadResponse(
        job_id=job.id,
        status="queued",
        stream_url=f"/api/v1/convert/jobs/{job.id}/stream"
    )
```

**Ответ `202 Accepted`:**

```json
{
  "job_id": "8fa8b7d2-7c3e-4b42-9a5c-7b2a59a72190",
  "status": "queued",
  "stream_url": "/api/v1/convert/jobs/8fa8b7d2-7c3e-4b42-9a5c-7b2a59a72190/stream"
}
```

**Ошибки:**

| HTTP | `code` | Условие |
| :--- | :--- | :--- |
| `400` | `INVALID_FILE_TYPE` | Magic Bytes не соответствуют PDF |
| `400` | `CORRUPTED_PDF` | `qpdf --check` вернул ошибку или файл зашифрован |
| `403` | `FILE_TOO_LARGE` | Размер файла превышает лимит тарифа |
| `403` | `FREE_LIMIT_EXCEEDED` | Дневной лимит конвертаций исчерпан |

---

### 2.2. `GET /api/v1/convert/jobs/{job_id}`

**Назначение:** Polling fallback — вернуть текущий снапшот статуса задачи без подписки на SSE.

**Алгоритм для клиента:**
1. Получить `job_id` после `POST /upload`.
2. Вызвать `GET /jobs/{job_id}` — если `status == 'completed'`/`'failed'`, отобразить результат и не открывать SSE.
3. Иначе — открыть SSE-стрим для оповещений в реальном времени.

**Ответ (200 OK):** JSON `JobStatusResponse`.

**Ошибки:**

| HTTP | `code` | Условие |
| :--- | :--- | :--- |
| `404` | `JOB_NOT_FOUND` | `job_id` не найден или `expires_at` истек |

---

### 2.3. `GET /api/v1/convert/jobs/{job_id}/stream`

**Назначение:** SSE-стриминг прогресса конвертации.

**Протокол:** Server-Sent Events (`text/event-stream`).

**Заголовки ответа:**

```text
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
Flush: true
```

> **Caddy Caddyfile:** для upstream FastAPI обязательно указать `flush_interval -1`, иначе Caddy буферизирует ответ.

**Механизм:**

1. Handler подписывается на Redis-канал `job:{job_id}:progress`.
2. Воркер публикует JSON-события через `PUBLISH job:{job_id}:progress <json>`.
3. Handler пересылает каждое сообщение клиенту как SSE-событие.
4. **Keepalive:** если в течение **15 секунд** нет событий от воркера, handler отправляет SSE-комментарий `': keepalive'` — предотвращает разрыв Caddy/nginx.
5. При закрытии клиентом соединения (`asyncio.CancelledError`) handler вызывает `redis_pubsub.unsubscribe()` и освобождает ресурсы.
6. Завершающее событие типа `complete` или `error` — handler закрывает соединение после отправки.

**Формат SSE-сообщений:**

```text
event: progress
data: {"job_id":"...","status":"processing","progress_percent":45,"current_step":"Анализ табличной структуры (стр. 3 из 8)","page_current":3,"page_total":8}

event: complete
data: {"job_id":"...","status":"completed","progress_percent":100,"current_step":"Готово к скачиванию","download_url":"/api/v1/convert/jobs/.../download","preview_urls":["/api/v1/convert/jobs/.../preview/0","/api/v1/convert/jobs/.../preview/1"],"is_preview_only":false}

event: error
data: {"job_id":"...","status":"failed","progress_percent":0,"current_step":"Ошибка конвертации","error":"CONVERSION_FAILED"}
```

**Значения `current_step` (русский язык, для отображения пользователю):**

| Шаг | `current_step` |
| :--- | :--- |
| Загрузка | `"Файл получен, ожидание очереди..."` |
| Начало обработки | `"Начинаем обработку..."` |
| Проверка PDF | `"Проверка целостности документа..."` |
| qpdf нарезка | `"Создание превью (страницы 1–2)..."` |
| Docling анализ | `"Анализ структуры документа (стр. {n} из {total})"` |
| Генерация DOCX/XLSX | `"Формирование файла {format}..."` |
| Загрузка в S3 | `"Сохранение результата..."` |
| Готово | `"Готово к скачиванию"` |

**Ошибки:**

| HTTP | `code` | Условие |
| :--- | :--- | :--- |
| `404` | `JOB_NOT_FOUND` | `job_id` не найден или `expires_at` истек |

---

### 2.4. `GET /api/v1/convert/jobs/{job_id}/download`

**Назначение:** перенаправить на pre-signed S3 URL готового файла.

**Логика:**

1. Загрузить запись `conversion_jobs` из БД по `job_id`.
2. Проверить: `status == 'completed'` И `expires_at > NOW()`.
3. **Проверка авторства:**
   - Авторизованный: `job.user_id == current_user.id` → если нет → `403 ACCESS_DENIED`.
   - Анонимный: сравнить `SHA-256(значение cookie anon_session)` == `job.session_token_hash` → если нет → `403 ACCESS_DENIED`.
4. Проверить `is_preview_only`:
   - `True` → вернуть `403 UPGRADE_REQUIRED` (нужен PRO для скачивания всего документа).
   - `False` → сгенерировать pre-signed URL на `s3_output_key` с TTL 15 минут.
5. Вернуть `307 Temporary Redirect` с заголовком `Content-Disposition: attachment; filename="{original_filename_without_ext}.{target_format}"`.

**Ошибки:**

| HTTP | `code` | Условие |
| :--- | :--- | :--- |
| `403` | `ACCESS_DENIED` | Жоб принадлежит другому пользователю |
| `403` | `UPGRADE_REQUIRED` | `is_preview_only = True`, нужна PRO-подписка |
| `404` | `JOB_NOT_FOUND` | Задача не найдена или срок хранения истек |

---

## 3. Логика воркера (tasks.py)

### 3.1. Задача `parse_and_convert(job_id: UUID)`

**Полный алгоритм (строгий порядок шагов):**

```python
def parse_and_convert(job_id: UUID) -> None:
    """RQ-задача: полный пайплайн PDF -> DOCX/XLSX."""
    job = get_job_sync(job_id)
    update_job_status(job_id, "processing")
    publish_progress(job_id, 5, "Начинаем обработку...")

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_input:
            storage_service.download_sync(job.s3_input_key, tmp_input.name)
            publish_progress(job_id, 10, "Проверка целостности документа...")

            _validate_pdf_with_qpdf(tmp_input.name)

            publish_progress(job_id, 20, "Создание превью (страницы 1-2)...")
            preview_keys = _render_preview(job_id, tmp_input.name)

            is_preview_only = _check_preview_only(job)

            if not is_preview_only:
                publish_progress(job_id, 40, "Анализ структуры документа...")
                output_path = _run_docling(job, tmp_input.name)
                publish_progress(job_id, 85, f"Формирование файла {job.target_format.upper()}...")

                s3_output_key = f"temp/{job_id}/output.{job.target_format}"
                storage_service.upload_sync(output_path, s3_output_key)
            else:
                s3_output_key = None

            update_job_completed(job_id, s3_output_key, preview_keys, is_preview_only)

            download_url = f"/api/v1/convert/jobs/{job_id}/download" if not is_preview_only else None
            publish_complete(job_id, preview_keys, download_url, is_preview_only)

    except Exception as exc:
        update_job_failed(job_id, str(exc))
        publish_error(job_id)
        if isinstance(exc, ConversionError):
            notify_admin_telegram(f"Job {job_id} failed: {exc}")
        raise
```

### 3.2. Функция `_render_preview(job_id, input_path) -> list[str]`

**Описание:** воркер генерирует JPEG-снимки первых 2 страниц через **PyMuPDF** (`fitz`). `qpdf` используется только для проверки целостности PDF.

```python
import fitz  # PyMuPDF

def _render_preview(job_id: UUID, input_path: str) -> list[str]:
    doc = fitz.open(input_path)
    page_count = min(len(doc), 2)
    preview_keys = []

    for i in range(page_count):
        page = doc[i]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")

        s3_key = f"temp/{job_id}/preview_p{i + 1}.jpg"
        storage_service.upload_bytes_sync(img_bytes, s3_key, content_type="image/jpeg")
        preview_keys.append(s3_key)

    doc.close()
    return preview_keys
```

> **Формат файлов:** JPEG (не PDF). Ключи в S3: `temp/{job_id}/preview_p1.jpg`, `temp/{job_id}/preview_p2.jpg`. Фронтенд отображает изображения напрямую через `<img>` без CORS-проблем PDF.js. Уровень DPI=150 обеспечивает читаемость при размере ~1000-1200px по ширине.

### 3.3. Функция `_run_docling(job, input_path) -> str`

```python
from docling.document_converter import DocumentConverter

def _run_docling(job, input_path: str) -> str:
    converter = DocumentConverter()  # создается внутри функции, не глобально
    result = converter.convert(input_path)

    output_path = f"/tmp/{job.id}/output.{job.target_format}"

    if job.target_format == "docx":
        result.document.save_as_docx(output_path)
    elif job.target_format == "xlsx":
        result.document.save_as_xlsx(output_path)

    return output_path
```

### 3.4. Определение `is_preview_only` и `page_count`

```python
def _check_preview_only(job: ConversionJob) -> bool:
    """Только Free-пользователи с документами > 2 страниц получают preview_only."""
    user = get_user_sync(job.user_id)
    user_plan = user.plan if user else "free"
    # page_count заполняется воркером AFTER qpdf (не NULL)
    page_count = job.page_count  # актуальное значение после обновления в БД

    if user_plan == "free" and page_count is not None and page_count > 2:
        return True
    return False
```

> **Контракт `page_count`:** воркер обязан обновить `job.page_count = doc.page_count` в `_render_preview()` до вызова `_check_preview_only()`. Вызов `get_user_sync(None)` (для анонимов) возвращает `user_plan = "free"`.

---

## 3a. Warmup воркера (worker.py)

До Docling загружает ML-модели (~2–4 ГБ) при первом вызове `DocumentConverter.convert()`. Чтобы первый реальный job не выходил по таймауту, воркер проводит **warmup** при старте:

```python
import base64
import tempfile
from docling.document_converter import DocumentConverter

# Минимальный валидный 1-страничный PDF (кодирован base64-константой в коде)
_WARMUP_PDF_B64 = (
    "JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2"
    "JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPD4KZW5k"
    "b2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2"
    "MTIgNzkyXQo+PgplbmRvYmoKeHJlZgowIDQKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5"
    "IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDExNSAwMDAwMCBuIAp0cmFpbGVy"
    "Cjw8Ci9TaXplIDQKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjE5MgolJUVPRg=="
)


def _warmup_docling() -> None:
    """Preload Docling ML-models on worker startup to avoid cold-start on first job."""
    pdf_bytes = base64.b64decode(_WARMUP_PDF_B64)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        f.flush()
        try:
            DocumentConverter().convert(f.name)
        except Exception:  # noqa: BLE001  # warmup ошибки не критичны
            pass


if __name__ == "__main__":
    _warmup_docling()  # <-- вызывается до старта RQ Worker цикла
    from rq import Connection, Worker
    with Connection(redis_conn):
        Worker(["priority", "fast", "heavy"]).work(max_jobs=settings.WORKER_MAX_JOBS)
```

> **Примечание:** время warmup (~10–20 сек) не входит в `job_timeout`. Docker `healthcheck` для воркера не нужен — используем стандартный `restart: unless-stopped`.

---

## 4. Сервисный слой

### 4.1. `storage_service.py`

```python
import boto3
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings

_executor = ThreadPoolExecutor(max_workers=4)


class StorageService:
    """S3-клиент на базе boto3 (sync).

    В FastAPI-эндпоинтах асинхронные методы вызываются через
    asyncio.run_in_executor, чтобы не блокировать event loop.
    В workers/tasks.py (синхронный RQ-контекст) — вызываются напрямую.
    """

    def __init__(self):
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )

    # --- Sync API (для workers/tasks.py) ---

    def upload_sync(self, file_obj, s3_key: str) -> None:
        self._client.upload_fileobj(
            file_obj, settings.S3_BUCKET_NAME, s3_key,
            ExtraArgs={"ServerSideEncryption": "AES256"}
        )

    def download_sync(self, s3_key: str, local_path: str) -> None:
        self._client.download_file(settings.S3_BUCKET_NAME, s3_key, local_path)

    def generate_presigned_url_sync(self, s3_key: str, expires_in: int = 900) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    # --- Async API (для FastAPI endpoints) ---

    async def upload(self, file_obj, s3_key: str) -> None:
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_executor, self.upload_sync, file_obj, s3_key)

    async def download(self, s3_key: str, local_path: str) -> None:
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_executor, self.download_sync, s3_key, local_path)

    async def generate_presigned_url(self, s3_key: str, expires_in: int = 900) -> str:
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor, self.generate_presigned_url_sync, s3_key, expires_in
        )
```

> **Стратегия S3-клиентов:** проект использует единый синхронный `boto3` во всем коде. В FastAPI-эндпоинтах `StorageService` вызывается через `asyncio.run_in_executor(None, ...)`, чтобы не блокировать event loop. В `tasks.py` (RQ-воркер) — вызывается напрямую. Это устраняет неоднозначность и N+1 подключений.

### 4.2. `converter_service.py` — алгоритм выбора очереди

```python
def select_queue(user: User | None, file_size_bytes: int) -> str:
    """
    priority  — PRO-пользователи (всегда)
    fast      — Free, файл < 5 МБ (предполагается текстовый PDF)
    heavy     — Free, файл >= 5 МБ (вероятно скан или большой документ)
    """
    if user and user.plan == "pro":
        return "priority"
    if file_size_bytes < 5 * 1024 * 1024:
        return "fast"
    return "heavy"
```

---

## 5. Схема БД (только для Slice 1)

Таблица `conversion_jobs` объявлена в `docs/TECH.md` (раздел 4.1).

**Alembic миграция** `0002_conversion_jobs.py` должна создать:

- Таблицу `conversion_jobs`.
- Индексы: `idx_jobs_user_status`, `idx_jobs_expires`.

---

## 6. Pydantic схемы (schemas/convert.py)

```python
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    job_id: UUID
    status: Literal["queued"]
    stream_url: str


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


class SSEProgressEvent(BaseModel):
    """Схема JSON-тела SSE-событий (публикуется в Redis Pub/Sub)."""
    job_id: UUID
    status: Literal["pending", "queued", "processing", "completed", "failed"]
    progress_percent: int
    current_step: str
    page_current: Optional[int] = None
    page_total: Optional[int] = None
    preview_urls: Optional[list[str]] = None
    download_url: Optional[str] = None
    is_preview_only: Optional[bool] = None
    error: Optional[str] = None
```

---

## 7. Redis Pub/Sub — протокол сообщений

**Канал:** `job:{job_id}:progress`

**Публикация из воркера:**

```python
import redis
import json

r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


def publish_progress(job_id: UUID, percent: int, step: str, **kwargs) -> None:
    event = SSEProgressEvent(
        job_id=job_id,
        status="processing",
        progress_percent=percent,
        current_step=step,
        **kwargs
    )
    r.publish(f"job:{job_id}:progress", event.model_dump_json())


def publish_complete(job_id, preview_urls, download_url, is_preview_only) -> None:
    event = SSEProgressEvent(
        job_id=job_id, status="completed", progress_percent=100,
        current_step="Готово к скачиванию",
        preview_urls=preview_urls,
        download_url=download_url,
        is_preview_only=is_preview_only,
    )
    r.publish(f"job:{job_id}:progress", event.model_dump_json())
```

**Подписка в SSE-хендлере (FastAPI):**

```python
async def stream_job(job_id: UUID):
    pubsub = redis_async.pubsub()
    await pubsub.subscribe(f"job:{job_id}:progress")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode()
                event = SSEProgressEvent.model_validate_json(data)
                sse_type = "complete" if event.status == "completed" else "error" if event.status == "failed" else "progress"
                yield f"event: {sse_type}\ndata: {data}\n\n"
                if event.status in ("completed", "failed"):
                    break
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(f"job:{job_id}:progress")
        await pubsub.close()
```

---

## 8. Защита от ошибок и пограничные случаи

| Случай | Обработка |
| :--- | :--- |
| PDF зашифрован паролем | `qpdf --check` вернет ошибку → `status='failed'`, код `CORRUPTED_PDF` |
| PDF повреждены Magic Bytes | Проверка на входе в `/upload`, 400 `INVALID_FILE_TYPE` |
| Docling вернул пустой документ | Проверить `len(result.document.pages) == 0` → ошибка `CONVERSION_FAILED` |
| Таймаут 180 сек в RQ | RQ убивает процесс, статус → `failed` |
| Потеря соединения с Redis | SSE-хендлер: `try/except redis.ConnectionError` → закрыть поток |
| S3 недоступен | `aioboto3` raises `botocore.exceptions.ClientError` → 503 `SERVICE_OVERLOADED` |
| Воркер убит OOM (`--max-jobs=50`) | Docker `restart: unless-stopped` перезапустит, задача остается в очереди RQ |
| Документ 1 страница, Free-тариф | `is_preview_only=False` — 1 страница <= 2, полная конвертация разрешена |

---

## 9. Требования к тестированию (Slice 1)

### 9.1. Unit-тесты (`backend/tests/test_convert.py`)

- [ ] `test_magic_bytes_validation_rejects_non_pdf` — загрузка файла с неверными Magic Bytes → 400.
- [ ] `test_upload_success_returns_202` — корректный PDF → `202` и `job_id` в ответе.
- [ ] `test_select_queue_free_small_file` — `file_size < 5MB` → очередь `fast`.
- [ ] `test_select_queue_free_large_file` — `file_size >= 5MB` → очередь `heavy`.
- [ ] `test_select_queue_pro_user` — PRO-пользователь → очередь `priority`.
- [ ] `test_check_preview_only_free_multipage` — Free + >2 стр. → `is_preview_only=True`.
- [ ] `test_check_preview_only_pro` — PRO-пользователь → `is_preview_only=False`.
- [ ] `test_daily_limit_exceeded_returns_403` — превышение лимита → 403 `FREE_LIMIT_EXCEEDED`.

### 9.2. Интеграционные тесты (с MinIO и фикстурными PDF)

- [ ] `test_full_pipeline_docx_conversion` — загрузка 2-страничного текстового PDF, ожидаем `completed` и непустой DOCX.
- [ ] `test_full_pipeline_xlsx_conversion` — PDF с таблицами, ожидаем `completed` и непустой XLSX.
- [ ] `test_preview_generation` — `s3_preview_keys` содержит <= 2 элементов, файлы доступны в S3.
- [ ] `test_job_timeout` — мок-задача, превышающая 180 сек → статус `failed`.
- [ ] `test_sse_stream_events_order` — подписка на SSE, ожидаем `progress` → `complete`.
- [ ] `test_download_redirect` — `GET /jobs/{id}/download` → `307`, URL содержит `X-Amz-Expires`.
- [ ] `test_download_preview_only_blocked` — Free-пользователь с `is_preview_only=True` → 403 `UPGRADE_REQUIRED`.

### 9.3. Тестовые PDF (fixtures)

Создать через `conftest.py` программно (без бинарных файлов в репозитории):

| Файл | Описание | Ожидаемый результат |
| :--- | :--- | :--- |
| `text_2page.pdf` | Текстовый, 2 стр. | DOCX с текстом, `is_preview_only=False` |
| `text_10page.pdf` | Текстовый, 10 стр. | Free-лимит: `is_preview_only=True`, превью 2 стр. |
| `table_simple.pdf` | PDF с таблицей 5x5 | XLSX с данными в ячейках |
| `multicolumn.pdf` | 2 колонки текста | DOCX с сохранением структуры |
| `encrypted.pdf` | Защищен паролем | 400 `CORRUPTED_PDF` |
| `fake_pdf.txt` | Файл .pdf с неверными Magic Bytes | 400 `INVALID_FILE_TYPE` |

---

## 10. Docker Compose: конфигурация воркера (dev)

```yaml
worker:
  build:
    context: ./backend
    dockerfile: Dockerfile.worker
  command: rq worker priority fast heavy --max-jobs=${WORKER_MAX_JOBS:-50}
  environment:
    - DATABASE_URL=postgresql+asyncpg://cleandoc:cleandoc@postgres:5432/cleandoc_db
    - REDIS_HOST=redis
    - REDIS_PORT=6379
    - S3_ENDPOINT_URL=http://minio:9000
    - S3_BUCKET_NAME=cleandoc-dev
    - S3_ACCESS_KEY_ID=minioadmin
    - S3_SECRET_ACCESS_KEY=minioadmin
    - WORKER_JOB_TIMEOUT=180
    - WORKER_MAX_JOBS=50
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    - TELEGRAM_ADMIN_CHAT_ID=${TELEGRAM_ADMIN_CHAT_ID}
  depends_on:
    - postgres
    - redis
    - minio
  mem_limit: 4g
  restart: unless-stopped
  volumes:
    - /tmp/cleandoc_worker:/tmp
```

---

## 11. Дополнения к .env.example (Slice 1)

```ini
# Настройки воркера конвертации
WORKER_JOB_TIMEOUT=180
WORKER_MAX_JOBS=50

# Docling (путь к кешу ML-моделей)
DOCLING_ARTIFACTS_PATH=/app/.docling

# Docling / HuggingFace (офлайн-режим: модели должны быть в Docker-образе, интернет запрещен)
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HUGGINGFACE_HUB_VERBOSITY=error
```

---

## 12. Порядок реализации (рекомендованный)

```text
1.  Alembic миграция 0002_conversion_jobs.py (включая usage_date, idx_jobs_dedup)
2.  SQLAlchemy модель models/job.py
3.  Pydantic схемы schemas/convert.py
4.  storage_service.py (upload, download, presign, upload_bytes_sync) + unit-тесты с MinIO
5.  converter_service.py (валидация Magic Bytes, select_queue, check_daily_limit, check_dedup_pg)
6.  tasks.py: _render_preview (JPEG через PyMuPDF), _run_docling, _check_preview_only
7.  tasks.py: parse_and_convert (полный пайплайн) + Redis Pub/Sub publish + keepalive цикл
8.  worker.py: точка входа rq worker (читает WORKER_MAX_JOBS из Settings)
9.  convert.py: POST /upload endpoint (дедупликация через check_dedup_pg)
10. convert.py: GET /jobs/{id} endpoint (polling fallback)
11. convert.py: GET /jobs/{id}/stream endpoint (SSE + keepalive + Redis SUBSCRIBE)
12. convert.py: GET /jobs/{id}/download endpoint
13. Интеграционные тесты: test_convert.py
14. make gate — полный прогон, ручная проверка на 20 PDF
```

---

## 13. Связанные документы

- [Single Source of Truth (`TECH.md`)](./TECH.md) — схема БД, API контракты, SSE формат
- [Регламент разработки (`AGENTS.md`)](../AGENTS.md) — правила разработки, `CONTRACT GAP` процедура
- [Спецификация Slice 0: Foundation (`SLICE-00.md`)](./SLICE-00.md) — монорепозиторий и инфраструктура
- **Следующий срез:** Slice 2 (Auth & UX) — интерфейс конвертера, Passwordless вход
