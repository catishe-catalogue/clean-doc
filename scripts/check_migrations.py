#!/usr/bin/env python3
"""Скрипт проверки применения всех миграций Alembic перед стартом."""
import asyncio
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

# Добавляем backend в путь для импорта app
sys.path.insert(0, "backend")

from app.core.config import get_settings  # noqa: E402


async def check_db_migrations() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)

    alembic_cfg = Config("backend/alembic.ini")
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
