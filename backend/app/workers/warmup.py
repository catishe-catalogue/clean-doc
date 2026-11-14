import os
import sys
import tempfile
from typing import Any, cast

import pymupdf
import structlog

logger = structlog.get_logger()


def run_warmup() -> None:
    """Одноразовый прогрев моделей Docling и кеширование весов HuggingFace."""
    logger.info("worker_warmup_docling_started")
    try:
        from app.workers.tasks import _create_docling_converter

        fitz_any: Any = cast(Any, pymupdf)
        doc = fitz_any.open()
        page = doc.new_page()
        page.insert_text((50, 72), "CleanDoc Warmup Document", fontsize=12)
        pdf_bytes = doc.tobytes()
        doc.close()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            f.flush()
            temp_path = f.name

        converter = _create_docling_converter()
        converter.convert(temp_path)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.info("worker_warmup_docling_completed")
    except Exception as exc:
        logger.warning("worker_warmup_docling_skipped", reason=str(exc))


if __name__ == "__main__":
    run_warmup()
    sys.exit(0)
