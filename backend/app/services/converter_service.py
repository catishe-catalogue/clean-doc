import hashlib
import ipaddress
import secrets
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ConversionJob
from app.models.usage import DailyUsage
from app.models.user import User

PDF_MAGIC_BYTES = b"%PDF-"
MAX_FILE_SIZE_FREE = 10 * 1024 * 1024  # 10 МБ
MAX_FILE_SIZE_PRO = 100 * 1024 * 1024  # 100 МБ


def validate_pdf_header_and_mime(
    header_bytes: bytes, filename: str | None, content_type: str | None
) -> None:
    """Проверяет соответствие Magic Bytes (%PDF-) и MIME-типа."""
    if not header_bytes.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Файл не является корректным документом PDF",
                "code": "INVALID_FILE_TYPE",
            },
        )

    is_pdf_ext = filename is not None and filename.lower().endswith(".pdf")
    is_pdf_mime = content_type in (
        "application/pdf",
        "application/x-pdf",
        "binary/octet-stream",
    )

    if not (is_pdf_ext or is_pdf_mime):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Недопустимый формат файла. Требуется расширение .pdf",
                "code": "INVALID_FILE_TYPE",
            },
        )


def validate_file_size(size_bytes: int, user: User | None) -> None:
    """Проверяет ограничение размера файла по тарифу."""
    is_pro = user is not None and user.plan == "pro"
    max_size = MAX_FILE_SIZE_PRO if is_pro else MAX_FILE_SIZE_FREE

    if size_bytes > max_size:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": f"Размер файла превышает лимит вашего тарифа ({max_size // (1024 * 1024)} МБ)",
                "code": "FILE_TOO_LARGE",
                "upgrade_url": "/pricing" if not is_pro else None,
            },
        )


def extract_ip_subnet(client_ip: str) -> str:
    """Извлекает /24 IPv4 или /64 IPv6 подсеть для учета лимитов."""
    try:
        ip = ipaddress.ip_address(client_ip)
        if ip.version == 4:
            network = ipaddress.ip_network(f"{client_ip}/24", strict=False)
            return str(network)
        network6 = ipaddress.ip_network(f"{client_ip}/64", strict=False)
        return str(network6)
    except ValueError:
        return "127.0.0.0/24"


def select_queue(user: User | None, file_size_bytes: int) -> str:
    """
    priority — PRO-пользователи (приоритетный воркер)
    fast     — Free, файл < 5 МБ (текстовый документ)
    heavy    — Free, файл >= 5 МБ (тяжелый скан или многостраничный отчет)
    """
    if user and user.plan == "pro":
        return "priority"
    if file_size_bytes < 5 * 1024 * 1024:
        return "fast"
    return "heavy"


async def check_deduplication(
    db: AsyncSession,
    user: User | None,
    sha256_checksum: str,
) -> ConversionJob | None:
    """Ищет активную или завершенную задачу за сегодня с идентичным хешем."""
    query = (
        select(ConversionJob)
        .where(
            ConversionJob.user_id == (user.id if user else None),
            ConversionJob.sha256_checksum == sha256_checksum,
            ConversionJob.usage_date == date.today(),
            ConversionJob.status.in_(["processing", "completed"]),
        )
        .limit(1)
    )

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_and_increment_daily_limit(
    db: AsyncSession,
    user: User | None,
    fingerprint: str | None,
    client_ip: str,
) -> None:
    """Проверяет суточный лимит Free-тарифа (3 для логина, 1 для анонима) и фиксирует расход."""
    if user and user.plan == "pro":
        return  # Безлимитный PRO-тариф

    today = date.today()
    ip_subnet = extract_ip_subnet(client_ip)

    if user:
        # Авторизованный Free-пользователь: лимит 3 конвертации
        stmt = (
            insert(DailyUsage)
            .values(
                user_id=user.id,
                fingerprint=fingerprint,
                ip_subnet=ip_subnet,
                usage_date=today,
                conversion_count=1,
            )
            .on_conflict_do_update(
                constraint="uq_daily_user",
                set_={"conversion_count": DailyUsage.conversion_count + 1},
            )
            .returning(DailyUsage.conversion_count)
        )
        res = await db.execute(stmt)
        count = res.scalar_one()
        if count > 3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Исчерпан суточный лимит Free-тарифа (3 конвертации в день)",
                    "code": "FREE_LIMIT_EXCEEDED",
                    "upgrade_url": "/pricing",
                },
            )
    else:
        # Анонимный гость: лимит 1 конвертация в сутки
        if fingerprint:
            stmt_guest_fp = (
                insert(DailyUsage)
                .values(
                    user_id=None,
                    fingerprint=fingerprint,
                    ip_subnet=ip_subnet,
                    usage_date=today,
                    conversion_count=1,
                )
                .on_conflict_do_update(
                    index_elements=["fingerprint", "ip_subnet", "usage_date"],
                    index_where=DailyUsage.fingerprint.is_not(None),
                    set_={"conversion_count": DailyUsage.conversion_count + 1},
                )
                .returning(DailyUsage.conversion_count)
            )
            res = await db.execute(stmt_guest_fp)
        else:
            stmt_guest_ip = (
                insert(DailyUsage)
                .values(
                    user_id=None,
                    fingerprint=None,
                    ip_subnet=ip_subnet,
                    usage_date=today,
                    conversion_count=1,
                )
                .on_conflict_do_update(
                    index_elements=["ip_subnet", "usage_date"],
                    index_where=DailyUsage.fingerprint.is_(None),
                    set_={"conversion_count": DailyUsage.conversion_count + 1},
                )
                .returning(DailyUsage.conversion_count)
            )
            res = await db.execute(stmt_guest_ip)

        count = res.scalar_one()
        if count > 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Для продолжения работы требуется бесплатная авторизация",
                    "code": "FREE_LIMIT_EXCEEDED",
                    "upgrade_url": "/pricing",
                },
            )


def create_anon_session_token() -> tuple[str, str]:
    """Генерирует пару: raw_token (для cookie) и sha256_hash (для хранения в БД)."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def verify_anon_session_token(raw_token: str, token_hash: str) -> bool:
    """Сравнивает raw токен из cookie с хешем в conversion_jobs."""
    computed_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return secrets.compare_digest(computed_hash, token_hash)
