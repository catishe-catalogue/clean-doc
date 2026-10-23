import base64
import os
import sys
import tempfile

import redis
import structlog
from rq import Worker

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
    worker = Worker(queues, connection=redis_conn)
    worker.work(max_jobs=settings.WORKER_MAX_JOBS)


if __name__ == "__main__":
    try:
        run_worker()
    except (KeyboardInterrupt, SystemExit):
        logger.info("worker_stopped")
        sys.exit(0)
