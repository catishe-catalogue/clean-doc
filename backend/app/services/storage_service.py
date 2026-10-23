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
