#!/usr/bin/env python3
"""Скрипт проверки применения всех миграций Alembic перед стартом."""
import asyncio
from pathlib import Path
import sys

# Добавляем backend в sys.path независимо от рабочей директории запуска
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings


async def check_db_migrations() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)

    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    script = ScriptDirectory.from_config(alembic_cfg)
    head_revision = script.get_current_head()

    async with engine.connect() as conn:
        def _get_rev(sync_conn: object) -> str | None:
            context = MigrationContext.configure(sync_conn)  # type: ignore[arg-type]
            return context.get_current_revision()

        current_rev = await conn.run_sync(_get_rev)

    await engine.dispose()

    if current_rev != head_revision:
        print(f"ERROR: DB revision ({current_rev}) does not match Alembic head ({head_revision})")
        sys.exit(1)
    print(f"OK: DB revision is up to date ({current_rev})")


if __name__ == "__main__":
    asyncio.run(check_db_migrations())
