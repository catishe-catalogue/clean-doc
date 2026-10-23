import asyncio
import signal
import sys

import structlog

from app.core.config import get_settings
from app.core.redis import get_redis_client

logger = structlog.get_logger()
settings = get_settings()


async def run_worker_stub() -> None:
    """Заглушка воркера для Slice 0.

    В Slice 0 проверяет связь с Redis и находится в цикле ожидания,
    обеспечивая стабильную работу контейнера cleandoc_worker.
    В Slice 1 этот модуль замещается точкой входа rq worker с Docling warmup.
    """
    logger.info("worker_stub_starting", environment=settings.ENVIRONMENT)
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        logger.info("worker_redis_connected", host=settings.REDIS_HOST)
    except Exception as exc:
        logger.error("worker_redis_connection_failed", error=str(exc))

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("worker_stub_stopping")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    logger.info("worker_stub_ready_idle")
    while not stop_event.is_set():
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker_stub())
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
