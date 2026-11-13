import os
import shutil
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
_SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)

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
    res = subprocess.run(cmd, capture_output=True, text=True)
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
    if not os.environ.get("DOCLING_ARTIFACTS_PATH"):
        os.environ.pop("DOCLING_ARTIFACTS_PATH", None)

    import docx
    import pandas as pd
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(input_path)

    if len(result.document.pages) == 0:
        raise ValueError("CONVERSION_FAILED")

    if target_format == "docx":
        doc = docx.Document()
        for item, level in result.document.iterate_items():
            item_type = type(item).__name__
            if "Header" in item_type or "Title" in item_type:
                doc.add_heading(getattr(item, "text", ""), level=min(level, 3))
            elif "Table" in item_type and hasattr(item, "export_to_dataframe"):
                df = item.export_to_dataframe(doc=result.document)
                tbl = doc.add_table(rows=df.shape[0] + 1, cols=df.shape[1])
                tbl.style = "Table Grid"
                for j, col in enumerate(df.columns):
                    tbl.cell(0, j).text = str(col)
                for i, row in enumerate(df.itertuples(index=False)):
                    for j, val in enumerate(row):
                        tbl.cell(i + 1, j).text = str(val) if val is not None else ""
            elif hasattr(item, "text") and item.text:
                doc.add_paragraph(item.text)
        doc.save(output_path)
    elif target_format == "xlsx":
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if result.document.tables:
                for idx, table_item in enumerate(result.document.tables):
                    df = table_item.export_to_dataframe(doc=result.document)
                    sheet_name = f"Таблица {idx + 1}"[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                lines = [
                    it.text
                    for it, _ in result.document.iterate_items()
                    if hasattr(it, "text") and it.text
                ]
                df = pd.DataFrame({"Текст": lines})
                df.to_excel(writer, sheet_name="Документ", index=False)
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

        s3_input_key = job.s3_input_key
        target_format = job.target_format
        user_id = job.user_id

        user_plan = "free"
        if user_id:
            user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
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
        storage_service.download_file_sync(s3_input_key, local_input)

        # Шаг 2: Проверка целостности qpdf
        publish_progress(job_id, 20, "Проверка целостности документа...")
        _validate_pdf_with_qpdf(local_input)

        # Шаг 3: Рендер JPEG превью через PyMuPDF
        publish_progress(job_id, 30, "Создание превью (страницы 1–2)...")
        total_pages, preview_keys = _render_preview(job_id, local_input)

        # Определение признака is_preview_only (Free + документ > 2 стр., в DEV_FAST_MODE снимается)
        is_preview_only = (user_plan == "free" and total_pages > 2) and not settings.DEV_FAST_MODE

        s3_output_key: str | None = None

        if not is_preview_only:
            publish_progress(
                job_id,
                50,
                f"Анализ структуры документа (стр. 1 из {total_pages})...",
                page_current=1,
                page_total=total_pages,
            )

            local_output = os.path.join(temp_dir, f"output.{target_format}")
            _run_docling(target_format, local_input, local_output)

            publish_progress(job_id, 85, f"Формирование файла {target_format.upper()}...")
            s3_output_key = f"temp/{job_id}/output.{target_format}"

            mime_type = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                if target_format == "docx"
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
            shutil.rmtree(temp_dir, ignore_errors=True)
