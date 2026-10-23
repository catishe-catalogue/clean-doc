import asyncio
import hashlib
from collections.abc import AsyncGenerator
from typing import Annotated, Literal, cast
from uuid import UUID, uuid4

import redis as sync_redis
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
    file: Annotated[UploadFile, File(...)],
    target_format: Annotated[Literal["docx", "xlsx"], Form(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    fingerprint: Annotated[str | None, Form()] = None,
    anon_session: Annotated[str | None, Cookie()] = None,
) -> UploadResponse:
    """Принимает PDF, валидирует Magic Bytes, выполняет дедупликацию,
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
    await converter_service.check_and_increment_daily_limit(
        db, current_user, fingerprint, client_ip
    )

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

    job_id = uuid4()
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobStatusResponse:
    """Polling fallback: возвращает моментальный снимок задачи.
    Устраняет race condition при быстром завершении конвертации до открытия SSE.
    """
    job = await db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Задача не найдена или срок хранения истек", "code": "JOB_NOT_FOUND"},
        )

    download_url = (
        f"/api/v1/convert/jobs/{job.id}/download"
        if job.status == "completed" and not job.is_preview_only
        else None
    )

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
        status=cast(Literal["pending", "queued", "processing", "completed", "failed"], job.status),
        progress_percent=progress_val,
        current_step=current_step,
        original_filename=job.original_filename,
        target_format=cast(Literal["docx", "xlsx"], job.target_format),
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Server-Sent Events (SSE) стриминг прогресса обработки документа.
    Включает keepalive комментарии каждые 15 секунд для предотвращения обрыва Caddy.
    """
    job = await db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Задача не найдена", "code": "JOB_NOT_FOUND"},
        )

    async def event_generator() -> AsyncGenerator[str, None]:
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
                        sse_type = (
                            "complete"
                            if event.status == "completed"
                            else "error"
                            if event.status == "failed"
                            else "progress"
                        )
                        yield f"event: {sse_type}\ndata: {data_str}\n\n"

                        if event.status in ("completed", "failed"):
                            break
                except TimeoutError:
                    # SSE keepalive comment для предотвращения сброса Caddy proxy
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            logger.info("sse_client_disconnected", job_id=str(job_id))
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await r_async.close()

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
    db: Annotated[AsyncSession, Depends(get_db)],
    anon_session: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    """Выдает 307 Redirect на временный S3 pre-signed URL готового документа.
    Проверяет права авторства задачи и блокирует скачивание при is_preview_only = True.
    """
    job = await db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Файл не найден или срок его хранения истек", "code": "JOB_NOT_FOUND"},
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Обработка файла еще не завершена", "code": "CONVERSION_NOT_READY"},
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

    if not job.s3_output_key:
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

    base_name = job.original_filename.rsplit(".", 1)[0]
    out_filename = f"{base_name}.{job.target_format}"
    presigned_url = await storage_service.generate_presigned_url(
        job.s3_output_key,
        expires_in_seconds=900,  # 15 минут
        filename=out_filename,
    )
    return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
