import os
import sys
import tempfile

import redis
import structlog
from rq import SimpleWorker

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def _warmup_docling() -> None:
    """Превентивный прогрев моделей Docling перед приемом реальных клиентских задач."""
    if not os.environ.get("DOCLING_ARTIFACTS_PATH"):
        os.environ.pop("DOCLING_ARTIFACTS_PATH", None)
    logger.info("worker_warmup_docling_started")
    try:
        import fitz
        from docling.document_converter import DocumentConverter

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "CleanDoc Warmup Document", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

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
    worker = SimpleWorker(queues, connection=redis_conn)
    worker.work(max_jobs=settings.WORKER_MAX_JOBS)


if __name__ == "__main__":
    try:
        run_worker()
    except (KeyboardInterrupt, SystemExit):
        logger.info("worker_stopped")
        sys.exit(0)
