from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ConversionJob
from app.models.user import User
from app.services.converter_service import (
    check_and_increment_daily_limit,
    create_anon_session_token,
    extract_ip_subnet,
    select_queue,
    validate_file_size,
    verify_anon_session_token,
)


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
    with (
        patch("rq.Queue.enqueue", return_value=MagicMock()),
        patch("app.api.v1.endpoints.convert.storage_service", mock_storage),
    ):
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
async def test_upload_deduplication(
    async_client: AsyncClient,
    db_session: AsyncSession,
    sample_pdf_1page: bytes,
    mock_storage: MagicMock,
) -> None:
    """Повторная отправка идентичного документа в те же сутки возвращает существующий job_id без дублирования."""
    with (
        patch("rq.Queue.enqueue", return_value=MagicMock()) as mock_enqueue,
        patch("app.api.v1.endpoints.convert.storage_service", mock_storage),
    ):
        files = {"file": ("act.pdf", BytesIO(sample_pdf_1page), "application/pdf")}
        data = {"target_format": "docx", "fingerprint": "fp_dedup_1"}
        resp1 = await async_client.post("/api/v1/convert/upload", files=files, data=data)
        assert resp1.status_code == 202
        job_id_1 = resp1.json()["job_id"]
        assert mock_enqueue.call_count == 1

        # Симулируем завершение обработки воркером
        from uuid import UUID

        job = await db_session.get(ConversionJob, UUID(job_id_1))
        assert job is not None
        job.status = "completed"
        await db_session.commit()

        # Повторная загрузка того же файла с тем же анонимным токеном
        files2 = {"file": ("act.pdf", BytesIO(sample_pdf_1page), "application/pdf")}
        anon_cookie = resp1.cookies.get("anon_session") or ""
        cookies: dict[str, str] = {"anon_session": anon_cookie}
        resp2 = await async_client.post(
            "/api/v1/convert/upload",
            files=files2,
            data=data,
            cookies=cookies,
        )
        assert resp2.status_code == 202
        job_id_2 = resp2.json()["job_id"]
        # Дедупликация сработала: ID совпадает, в очередь повторно не ставилось
        assert job_id_1 == job_id_2
        assert mock_enqueue.call_count == 1


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
async def test_job_snapshot_success(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """Проверка получения моментального состояния созданной задачи."""
    job = ConversionJob(
        id=uuid4(),
        target_format="docx",
        original_filename="doc.pdf",
        file_size_bytes=4096,
        status="completed",
        s3_input_key="temp/test/input.pdf",
        s3_output_key="temp/test/output.docx",
        s3_preview_keys=["temp/test/preview_p1.jpg"],
        page_count=2,
        is_preview_only=False,
    )
    db_session.add(job)
    await db_session.commit()

    resp = await async_client.get(f"/api/v1/convert/jobs/{job.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(job.id)
    assert data["status"] == "completed"
    assert data["progress_percent"] == 100
    assert data["download_url"] == f"/api/v1/convert/jobs/{job.id}/download"
    assert data["preview_urls"] == ["temp/test/preview_p1.jpg"]


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


@pytest.mark.asyncio
async def test_download_anon_session_validation(
    async_client: AsyncClient, db_session: AsyncSession, mock_storage: MagicMock
) -> None:
    """Проверка доступа гостя к готовому файлу по валидной куке сессии."""
    raw_token, token_hash = create_anon_session_token()
    job = ConversionJob(
        id=uuid4(),
        session_token_hash=token_hash,
        target_format="docx",
        original_filename="order.pdf",
        file_size_bytes=1024,
        status="completed",
        s3_input_key="temp/test/input.pdf",
        s3_output_key="temp/test/output.docx",
        is_preview_only=False,
    )
    db_session.add(job)
    await db_session.commit()

    with patch("app.api.v1.endpoints.convert.storage_service", mock_storage):
        # Попытка скачать без куки -> 403 ACCESS_DENIED
        resp_no_cookie = await async_client.get(f"/api/v1/convert/jobs/{job.id}/download")
        assert resp_no_cookie.status_code == 403
        assert resp_no_cookie.json()["detail"]["code"] == "ACCESS_DENIED"

        # С неверной кукой -> 403 ACCESS_DENIED
        resp_bad_cookie = await async_client.get(
            f"/api/v1/convert/jobs/{job.id}/download",
            cookies={"anon_session": "invalid_cookie_value"},
        )
        assert resp_bad_cookie.status_code == 403

        # С корректной кукой -> 307 Redirect на pre-signed URL
        resp_ok = await async_client.get(
            f"/api/v1/convert/jobs/{job.id}/download",
            cookies={"anon_session": raw_token},
            follow_redirects=False,
        )
        assert resp_ok.status_code == 307
        assert "location" in resp_ok.headers


@pytest.mark.asyncio
async def test_validate_file_size_limits() -> None:
    """Проверка ограничений размера файла для Free и PRO тарифов."""
    free_user = None
    pro_user = MagicMock(plan="pro")

    # В пределах нормы
    validate_file_size(5 * 1024 * 1024, free_user)
    validate_file_size(50 * 1024 * 1024, pro_user)

    # Превышение Free лимита (10 МБ)
    with pytest.raises(HTTPException) as exc_free:
        validate_file_size(11 * 1024 * 1024, free_user)
    assert exc_free.value.status_code == 403
    assert isinstance(exc_free.value.detail, dict)
    assert exc_free.value.detail.get("code") == "FILE_TOO_LARGE"

    # Превышение PRO лимита (100 МБ)
    with pytest.raises(HTTPException) as exc_pro:
        validate_file_size(101 * 1024 * 1024, pro_user)
    assert exc_pro.value.status_code == 403


@pytest.mark.asyncio
async def test_anon_session_token_helpers() -> None:
    """Проверка генерации и верификации анонимных сессионных токенов."""
    raw, token_hash = create_anon_session_token()
    assert verify_anon_session_token(raw, token_hash) is True
    assert verify_anon_session_token("wrong_token", token_hash) is False


@pytest.mark.asyncio
async def test_extract_ip_subnet() -> None:
    """Проверка извлечения подсетей IPv4 и IPv6."""
    assert extract_ip_subnet("192.168.1.50") == "192.168.1.0/24"
    assert extract_ip_subnet("2001:db8::1") == "2001:db8::/64"
    assert extract_ip_subnet("invalid_ip") == "127.0.0.0/24"


def test_tasks_validate_pdf_with_qpdf() -> None:
    """Проверка валидации qpdf при корректном и поврежденном файле."""
    from app.workers.tasks import _validate_pdf_with_qpdf

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        _validate_pdf_with_qpdf("dummy.pdf")

        mock_run.return_value = MagicMock(returncode=1, stderr="Corrupted syntax")
        with pytest.raises(ValueError, match="CORRUPTED_PDF"):
            _validate_pdf_with_qpdf("dummy.pdf")


def test_tasks_render_preview(tmp_path: object, sample_pdf_2page: bytes) -> None:
    """Проверка генерации превью страниц через PyMuPDF."""
    from pathlib import Path

    from app.workers.tasks import _render_preview

    p = Path(str(tmp_path)) / "sample.pdf"
    p.write_bytes(sample_pdf_2page)

    job_id = uuid4()
    with patch("app.workers.tasks.storage_service.upload_bytes_sync") as mock_upload:
        pages, keys = _render_preview(job_id, str(p))
        assert pages == 2
        assert len(keys) == 2
        assert mock_upload.call_count == 2


def test_tasks_publish_events() -> None:
    """Проверка отправки SSE событий воркера в Redis Pub/Sub."""
    from app.workers.tasks import publish_complete, publish_error, publish_progress

    job_id = uuid4()
    with patch("app.workers.tasks._redis_client.publish") as mock_publish:
        publish_progress(job_id, 50, "Анализ структуры...", 1, 2)
        assert mock_publish.call_count == 1

        publish_complete(job_id, ["k1"], "/download", False)
        assert mock_publish.call_count == 2

        publish_error(job_id, "ERROR_CODE", "Ошибка конвертации")
        assert mock_publish.call_count == 3


def test_tasks_parse_and_convert_success(tmp_path: object, sample_pdf_1page: bytes) -> None:
    """Проверка сквозного выполнения задачи воркера при успешной конвертации."""
    from pathlib import Path

    from app.workers.tasks import parse_and_convert

    job_id = uuid4()
    mock_job = MagicMock(
        id=job_id,
        user_id=None,
        target_format="docx",
        s3_input_key=f"temp/{job_id}/input.pdf",
        status="pending",
    )
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_job
    mock_session_ctx = MagicMock()
    mock_session_ctx.__enter__.return_value = mock_session

    p = Path(str(tmp_path)) / "input.pdf"
    p.write_bytes(sample_pdf_1page)

    with (
        patch("app.workers.tasks._SyncSession", return_value=mock_session_ctx),
        patch("app.workers.tasks.storage_service.download_file_sync") as mock_download,
        patch("app.workers.tasks._validate_pdf_with_qpdf") as mock_val,
        patch("app.workers.tasks._render_preview", return_value=(1, ["preview.jpg"])),
        patch("app.workers.tasks._run_docling") as mock_docling,
        patch("app.workers.tasks.storage_service.upload_file_sync"),
        patch("app.workers.tasks._redis_client.publish"),
    ):
        parse_and_convert(str(job_id))
        mock_download.assert_called_once()
        mock_val.assert_called_once()
        mock_docling.assert_called_once()


def test_tasks_parse_and_convert_failure() -> None:
    """Проверка фиксации ошибки воркера в БД и публикации ошибки при исключении."""
    from app.workers.tasks import parse_and_convert

    job_id = uuid4()
    mock_job = MagicMock(
        id=job_id,
        user_id=None,
        target_format="docx",
        s3_input_key=f"temp/{job_id}/input.pdf",
        status="pending",
    )
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = mock_job
    mock_session_ctx = MagicMock()
    mock_session_ctx.__enter__.return_value = mock_session

    with (
        patch("app.workers.tasks._SyncSession", return_value=mock_session_ctx),
        patch("app.workers.tasks.storage_service.download_file_sync"),
        patch(
            "app.workers.tasks._validate_pdf_with_qpdf",
            side_effect=ValueError("CORRUPTED_PDF"),
        ),
        patch("app.workers.tasks._redis_client.publish"),
    ):
        with pytest.raises(ValueError, match="CORRUPTED_PDF"):
            parse_and_convert(str(job_id))


def test_worker_warmup_docling() -> None:
    """Проверка процедуры превентивного прогрева моделей Docling."""
    import sys

    from app.workers.worker import _warmup_docling

    mock_converter_instance = MagicMock()
    mock_docling_module = MagicMock()
    mock_docling_module.DocumentConverter.return_value = mock_converter_instance

    with patch.dict(sys.modules, {"docling.document_converter": mock_docling_module}):
        _warmup_docling()
        mock_converter_instance.convert.assert_called_once()

    # Проверка безопасной обработки ошибки при отсутствии весов
    with patch.dict(sys.modules, {"docling.document_converter": None}):
        _warmup_docling()


@pytest.mark.asyncio
async def test_upload_deduplication_different_guest_not_conflicted(
    async_client: AsyncClient,
    sample_pdf_1page: bytes,
    mock_storage: MagicMock,
) -> None:
    """Два разных анонимных гостя с одинаковым файлом НЕ должны получать один и тот же job_id."""
    with (
        patch("rq.Queue.enqueue", return_value=MagicMock()) as mock_enqueue,
        patch("app.api.v1.endpoints.convert.storage_service", mock_storage),
    ):
        files = {"file": ("shared.pdf", BytesIO(sample_pdf_1page), "application/pdf")}

        # Гость 1 загружает файл
        resp1 = await async_client.post(
            "/api/v1/convert/upload",
            files=files,
            data={"target_format": "docx", "fingerprint": "guest_1_fp"},
        )
        assert resp1.status_code == 202
        job_id_1 = resp1.json()["job_id"]

        # Гость 2 загружает точно такой же файл, но со своей новой сессией и fingerprint
        files2 = {"file": ("shared.pdf", BytesIO(sample_pdf_1page), "application/pdf")}
        resp2 = await async_client.post(
            "/api/v1/convert/upload",
            files=files2,
            data={"target_format": "docx", "fingerprint": "guest_2_fp"},
        )
        assert resp2.status_code == 202
        job_id_2 = resp2.json()["job_id"]

        # Гости изолированы: разные job_id и 2 постановки в очередь
        assert job_id_1 != job_id_2
        assert mock_enqueue.call_count == 2


@pytest.mark.asyncio
async def test_daily_limit_guest_without_fingerprint(db_session: AsyncSession) -> None:
    """Анонимный гость по IP: 1-я конвертация успешна, 2-я отклоняется 403 FREE_LIMIT_EXCEEDED."""
    client_ip = "198.51.100.42"

    # 1-я конвертация проходит
    await check_and_increment_daily_limit(
        db=db_session, user=None, fingerprint=None, client_ip=client_ip
    )

    # 2-я конвертация блокируется
    with pytest.raises(HTTPException) as exc:
        await check_and_increment_daily_limit(
            db=db_session, user=None, fingerprint=None, client_ip=client_ip
        )
    assert exc.value.status_code == 403
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail.get("code") == "FREE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_daily_limit_guest_with_fingerprint(db_session: AsyncSession) -> None:
    """Анонимный гость с fingerprint: лимит изолирован по fingerprint."""
    client_ip = "203.0.113.10"
    fp1 = "browser_fp_alpha"
    fp2 = "browser_fp_beta"

    # FP 1 - первая конвертация ок, вторая блокируется
    await check_and_increment_daily_limit(
        db=db_session, user=None, fingerprint=fp1, client_ip=client_ip
    )
    with pytest.raises(HTTPException) as exc1:
        await check_and_increment_daily_limit(
            db=db_session, user=None, fingerprint=fp1, client_ip=client_ip
        )
    assert exc1.value.status_code == 403

    # FP 2 на том же IP - отдельный лимит
    await check_and_increment_daily_limit(
        db=db_session, user=None, fingerprint=fp2, client_ip=client_ip
    )


@pytest.mark.asyncio
async def test_daily_limit_registered_free_user(db_session: AsyncSession) -> None:
    """Зарегистрированный Free-пользователь: 3 конвертации в сутки, 4-я блокируется."""
    free_user = User(
        email=f"free_test_{uuid4().hex[:8]}@example.com",
        plan="free",
    )
    db_session.add(free_user)
    await db_session.commit()
    await db_session.refresh(free_user)

    client_ip = "192.0.2.1"

    # Первые 3 конвертации успешны
    for _ in range(3):
        await check_and_increment_daily_limit(
            db=db_session, user=free_user, fingerprint=None, client_ip=client_ip
        )

    # 4-я конвертация блокируется
    with pytest.raises(HTTPException) as exc:
        await check_and_increment_daily_limit(
            db=db_session, user=free_user, fingerprint=None, client_ip=client_ip
        )
    assert exc.value.status_code == 403
    assert isinstance(exc.value.detail, dict)
    assert exc.value.detail.get("code") == "FREE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_daily_limit_pro_user_bypasses(db_session: AsyncSession) -> None:
    """PRO-пользователь не имеет суточных лимитов."""
    pro_user = User(
        email=f"pro_test_{uuid4().hex[:8]}@example.com",
        plan="pro",
    )
    db_session.add(pro_user)
    await db_session.commit()

    # Многократные вызовы не вызывают исключений
    for _ in range(10):
        await check_and_increment_daily_limit(
            db=db_session, user=pro_user, fingerprint=None, client_ip="127.0.0.1"
        )


@pytest.mark.asyncio
async def test_stream_completed_job_immediate_response(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """SSE стрим на уже завершенную задачу отдает событие complete мгновенно без зависания."""
    job = ConversionJob(
        id=uuid4(),
        target_format="docx",
        original_filename="ready.pdf",
        file_size_bytes=1024,
        status="completed",
        s3_input_key="temp/test/in.pdf",
        s3_output_key="temp/test/out.docx",
        s3_preview_keys=["temp/test/p1.jpg"],
        page_count=1,
        is_preview_only=False,
    )
    db_session.add(job)
    await db_session.commit()

    resp = await async_client.get(f"/api/v1/convert/jobs/{job.id}/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "event: complete" in text
    assert str(job.id) in text
    assert "download_url" in text


def test_tasks_parse_and_convert_detached_instance_safe(
    tmp_path: object, sample_pdf_1page: bytes
) -> None:
    """Проверка отсутствия DetachedInstanceError при выходе из первой сессии SQLAlchemy."""
    from pathlib import Path

    from app.workers.tasks import parse_and_convert

    job_id = uuid4()
    job = ConversionJob(
        id=job_id,
        user_id=None,
        target_format="docx",
        original_filename="test.pdf",
        file_size_bytes=len(sample_pdf_1page),
        s3_input_key=f"temp/{job_id}/input.pdf",
        status="pending",
    )

    mock_session = MagicMock()
    mock_session.execute.return_value.scalar_one_or_none.return_value = job
    mock_session_ctx = MagicMock()
    mock_session_ctx.__enter__.return_value = mock_session

    p = Path(str(tmp_path)) / "input.pdf"
    p.write_bytes(sample_pdf_1page)

    with (
        patch("app.workers.tasks._SyncSession", return_value=mock_session_ctx),
        patch("app.workers.tasks.storage_service.download_file_sync") as mock_download,
        patch("app.workers.tasks._validate_pdf_with_qpdf"),
        patch("app.workers.tasks._render_preview", return_value=(1, ["preview.jpg"])),
        patch("app.workers.tasks._run_docling"),
        patch("app.workers.tasks.storage_service.upload_file_sync"),
        patch("app.workers.tasks._redis_client.publish"),
    ):
        parse_and_convert(str(job_id))
        mock_download.assert_called_once()
        assert mock_download.call_args[0][0] == f"temp/{job_id}/input.pdf"
