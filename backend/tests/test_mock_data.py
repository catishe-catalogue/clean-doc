from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.job import ConversionJob
from app.services.converter_service import validate_file_size

settings = get_settings()
MOCK_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "mock_data"


def test_mock_data_files_exist() -> None:
    """Проверка наличия всех 4 тестовых файлов в mock_data."""
    required = [
        "test-data-memo.pdf",
        "test-data-resume.pdf",
        "test-data-report.pdf",
        "test-data-contract.pdf",
    ]
    for filename in required:
        file_path = MOCK_DATA_DIR / filename
        assert file_path.exists(), f"Файл {filename} отсутствует в mock_data"
        assert file_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_mock_data_prod_mode_branching(
    async_client: AsyncClient, mock_storage: MagicMock
) -> None:
    """Проверка ветвления условий для mock_data в реалистичном Production-режиме."""
    with (
        patch.object(settings, "DEV_FAST_MODE", False),
        patch("app.api.v1.endpoints.convert.storage_service", mock_storage),
        patch("app.api.v1.endpoints.convert.Queue"),
    ):
        # 1. test-data-memo.pdf (90 KB, 1 стр.) — укладывается в Free лимит
        memo_bytes = (MOCK_DATA_DIR / "test-data-memo.pdf").read_bytes()
        resp_memo = await async_client.post(
            "/api/v1/convert/upload",
            files={"file": ("test-data-memo.pdf", memo_bytes, "application/pdf")},
            data={"target_format": "docx"},
        )
        assert resp_memo.status_code == 202

        # 2. test-data-resume.pdf (400 KB, 3 стр.) — принимается на загрузку
        resume_bytes = (MOCK_DATA_DIR / "test-data-resume.pdf").read_bytes()
        resp_resume = await async_client.post(
            "/api/v1/convert/upload",
            files={"file": ("test-data-resume.pdf", resume_bytes, "application/pdf")},
            data={"target_format": "docx"},
            cookies=resp_memo.cookies,
        )
        # Вторая конвертация гостя блокируется лимитом (требуется авторизация)
        assert resp_resume.status_code == 403
        assert resp_resume.json()["detail"]["code"] == "FREE_LIMIT_EXCEEDED"

        # 3. test-data-report.pdf (22.9 MB) — превышает Free лимит 10 МБ
        report_size = (MOCK_DATA_DIR / "test-data-report.pdf").stat().st_size
        with pytest.raises(Exception) as exc_report:
            validate_file_size(report_size, user=None)
        assert getattr(exc_report.value, "status_code", None) == 403

        # 4. test-data-contract.pdf (24.2 MB) — превышает Free лимит 10 МБ
        contract_size = (MOCK_DATA_DIR / "test-data-contract.pdf").stat().st_size
        with pytest.raises(Exception) as exc_contract:
            validate_file_size(contract_size, user=None)
        assert getattr(exc_contract.value, "status_code", None) == 403


@pytest.mark.asyncio
async def test_mock_data_fast_dev_mode(
    async_client: AsyncClient, db_session: AsyncSession, mock_storage: MagicMock
) -> None:
    """Проверка загрузки и скачивания mock_data в режиме быстрой разработки (DEV_FAST_MODE)."""
    with (
        patch.object(settings, "DEV_FAST_MODE", True),
        patch("app.api.v1.endpoints.convert.storage_service", mock_storage),
        patch("app.api.v1.endpoints.convert.Queue"),
    ):
        # В DEV_FAST_MODE даже файлы >10 МБ проходят валидацию (лимит PRO 100 МБ)
        for fname in ["test-data-report.pdf", "test-data-contract.pdf"]:
            fsize = (MOCK_DATA_DIR / fname).stat().st_size
            validate_file_size(fsize, user=None)

        # Проверка создания задачи и мгновенного скачивания без 403
        job_id = uuid4()
        job = ConversionJob(
            id=job_id,
            user_id=None,
            target_format="docx",
            original_filename="test-data-resume.pdf",
            file_size_bytes=400000,
            status="completed",
            page_count=3,
            is_preview_only=False,  # в dev-режиме полный документ
            s3_input_key=f"temp/{job_id}/input.pdf",
            s3_output_key=f"temp/{job_id}/output.docx",
            s3_preview_keys=[f"temp/{job_id}/preview_p1.jpg", f"temp/{job_id}/preview_p2.jpg"],
        )
        db_session.add(job)
        await db_session.commit()

        # Скачивание без куки и без токена в dev-режиме завершается успехом (200 или 307)
        resp_dl = await async_client.get(
            f"/api/v1/convert/jobs/{job.id}/download",
            follow_redirects=False,
        )
        assert resp_dl.status_code in (200, 307)

        # Получение превью
        mock_storage.download_bytes_sync.return_value = b"jpeg_content"
        resp_prev = await async_client.get(f"/api/v1/convert/preview/temp/{job_id}/preview_p1.jpg")
        assert resp_prev.status_code == 200
        assert resp_prev.headers["content-type"] == "image/jpeg"
