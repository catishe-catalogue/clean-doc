from unittest.mock import MagicMock, patch

import pytest

from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_storage_health_success() -> None:
    """Проверяет положительный результат проверки доступности S3."""
    storage = StorageService()
    with patch.object(storage._s3_client, "head_bucket", return_value={}):
        is_healthy = await storage.check_health()
        assert is_healthy is True


@pytest.mark.asyncio
async def test_storage_health_failure() -> None:
    """Проверяет корректную обработку недоступности бакета S3."""
    storage = StorageService()
    with patch.object(
        storage._s3_client, "head_bucket", side_effect=Exception("Connection refused")
    ):
        is_healthy = await storage.check_health()
        assert is_healthy is False


@pytest.mark.asyncio
async def test_storage_upload_and_download_bytes() -> None:
    """Проверяет методы загрузки и скачивания бинарных данных."""
    storage = StorageService()
    test_data = b"%PDF-1.4 sample file content"
    test_key = "temp/test_job/input.pdf"

    mock_body = MagicMock()
    mock_body.read.return_value = test_data

    with (
        patch.object(storage._s3_client, "put_object", return_value={}) as mock_put,
        patch.object(
            storage._s3_client, "get_object", return_value={"Body": mock_body}
        ) as mock_get,
    ):
        await storage.upload_bytes(test_data, test_key, content_type="application/pdf")
        mock_put.assert_called_once_with(
            Bucket=storage.bucket,
            Key=test_key,
            Body=test_data,
            ContentType="application/pdf",
            ServerSideEncryption="AES256",
        )

        downloaded = await storage.download_bytes(test_key)
        assert downloaded == test_data
        mock_get.assert_called_once_with(Bucket=storage.bucket, Key=test_key)


@pytest.mark.asyncio
async def test_storage_generate_presigned_url() -> None:
    """Проверяет формирование подписанной ссылки на скачивание."""
    storage = StorageService()
    expected_url = "https://s3.selcloud.ru/cleandoc-prod/temp/doc.docx?X-Amz-Signature=abc"
    test_key = "temp/test_job/result.docx"

    with patch.object(
        storage._s3_client, "generate_presigned_url", return_value=expected_url
    ) as mock_presign:
        url = await storage.generate_presigned_url(test_key, expires_in_seconds=900)
        assert url == expected_url
        mock_presign.assert_called_once_with(
            "get_object",
            Params={"Bucket": storage.bucket, "Key": test_key},
            ExpiresIn=900,
        )
