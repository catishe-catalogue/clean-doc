import pytest
from scripts.seed_dev_data import run_seed
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_seed_runs_twice_without_errors(db_session: AsyncSession) -> None:
    """Проверка идемпотентности сидирования при многократном запуске."""
    await run_seed(db_session)
    await run_seed(db_session)  # повторный запуск не должен вызывать ошибок
    count = await db_session.scalar(
        text("SELECT count(*) FROM b2b_invoices WHERE invoice_number = 'INV-2026-001'")
    )
    assert count == 1
