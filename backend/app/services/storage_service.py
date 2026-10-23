import asyncio

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
                read_timeout=5,
                retries={"max_attempts": 2},
            ),
        )

    async def ensure_bucket_exists(self) -> None:
        """Проверяет существование бакета и создает его при отсутствии (для dev окружения)."""

        def _check() -> None:
            try:
                self._s3_client.head_bucket(Bucket=self.bucket)
            except Exception:
                self._s3_client.create_bucket(Bucket=self.bucket)

        await asyncio.to_thread(_check)

    async def check_health(self) -> bool:
        """Проверяет доступность S3 сервиса."""

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
        def _upload() -> None:
            self._s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type,
            )

        await asyncio.to_thread(_upload)

    async def download_bytes(self, s3_key: str) -> bytes:
        def _download() -> bytes:
            response = self._s3_client.get_object(Bucket=self.bucket, Key=s3_key)
            return response["Body"].read()  # type: ignore[no-any-return]

        return await asyncio.to_thread(_download)

    async def generate_presigned_url(self, s3_key: str, expires_in_seconds: int = 900) -> str:
        def _presign() -> str:
            return self._s3_client.generate_presigned_url(  # type: ignore[no-any-return]
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expires_in_seconds,
            )

        return await asyncio.to_thread(_presign)


storage_service = StorageService()
