from unittest.mock import MagicMock, patch

from app.core.config import get_settings
from app.workers.warmup import run_warmup
from app.workers.worker import run_worker

settings = get_settings()


def test_worker_warmup_independent_execution() -> None:
    """Проверка, что одноразовый модуль warmup отрабатывает успешно."""
    with patch("app.workers.tasks._create_docling_converter") as mock_converter:
        mock_instance = MagicMock()
        mock_converter.return_value = mock_instance
        run_warmup()
        assert mock_converter.called


def test_worker_skips_warmup_when_configured() -> None:
    """Проверка, что при WORKER_SKIP_WARMUP=True воркер стартует без блокирующего warmup."""
    with (
        patch.object(settings, "WORKER_SKIP_WARMUP", True),
        patch("app.workers.worker._warmup_docling") as mock_warmup,
        patch("redis.Redis"),
        patch("app.workers.worker.SimpleWorker") as mock_worker_cls,
    ):
        mock_worker_instance = MagicMock()
        mock_worker_cls.return_value = mock_worker_instance

        run_worker()

        # Warmup не должен вызываться в основном процессе воркера
        assert not mock_warmup.called
        # Процесс сразу приступает к прослушиванию очередей
        assert mock_worker_instance.work.called
