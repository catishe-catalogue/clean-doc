import hashlib
import hmac as _hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.job import ConversionJob
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import TelegramAuthRequest
from app.services.email_service import email_service

logger = structlog.get_logger()
settings = get_settings()


class AuthService:
    def hash_token(self, raw_token: str) -> str:
        """Хеширует токен или код алгоритмом SHA-256."""
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    def generate_jwt_access_token(self, user_id: UUID) -> tuple[str, int]:
        """Генерирует короткоживущий JWT access-токен (15 минут)."""
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        expire_at = datetime.now(UTC) + expires_delta
        payload = {
            "sub": str(user_id),
            "exp": expire_at,
            "iat": datetime.now(UTC),
            "type": "access",
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return token, int(expires_delta.total_seconds())

    async def create_magic_code(self, db: AsyncSession, email: str) -> None:
        """Генерирует 6-значный OTP, сохраняет его хеш и отправляет письмо."""
        email_clean = email.lower().strip()
        user = await db.scalar(select(User).where(User.email == email_clean))
        if not user:
            user = User(email=email_clean, plan="free")
            db.add(user)
            await db.flush()

        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Учетная запись заблокирована", "code": "USER_BLOCKED"},
            )

        raw_code = f"{secrets.randbelow(1000000):06d}"
        code_hash = self.hash_token(raw_code)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)

        user.magic_code_hash = code_hash
        user.magic_code_expires_at = expires_at
        user.magic_code_attempts = 0
        await db.commit()

        magic_link_url = f"{settings.FRONTEND_URL}/auth/verify?email={email_clean}&code={raw_code}"
        await email_service.send_magic_code(email_clean, raw_code, magic_link_url)

    async def verify_magic_code(
        self,
        db: AsyncSession,
        email: str,
        raw_code: str,
        anon_session_raw: str | None = None,
    ) -> tuple[User, str, str]:
        """
        Проверяет код, возвращает кортеж (User, access_token, raw_refresh_token).
        При наличии anon_session_raw выполняет связывание гостевых конвертаций.
        """
        email_clean = email.lower().strip()
        user = await db.scalar(select(User).where(User.email == email_clean))
        if not user or not user.magic_code_hash or not user.magic_code_expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Код не запрашивался или устарел", "code": "INVALID_CODE"},
            )

        if user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Учетная запись заблокирована", "code": "USER_BLOCKED"},
            )

        # Защита от брутфорса: максимум 5 попыток ввода
        if user.magic_code_attempts >= 5:
            user.magic_code_hash = None
            user.magic_code_expires_at = None
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Превышено количество попыток. Запросите новый код.",
                    "code": "MAX_ATTEMPTS_EXCEEDED",
                },
            )

        now_utc = datetime.now(UTC)
        if now_utc > user.magic_code_expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Срок действия кода истек", "code": "CODE_EXPIRED"},
            )

        candidate_hash = self.hash_token(raw_code)
        if not _hmac.compare_digest(candidate_hash, user.magic_code_hash):
            user.magic_code_attempts += 1
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Неверный код подтверждения", "code": "INVALID_CODE"},
            )

        # Сброс кода после успешной проверки
        user.magic_code_hash = None
        user.magic_code_expires_at = None
        user.magic_code_attempts = 0

        # Выпуск JWT access токена и Refresh токена
        access_token, _ = self.generate_jwt_access_token(user.id)
        raw_refresh = secrets.token_urlsafe(48)
        refresh_hash = self.hash_token(raw_refresh)

        token_record = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        db.add(token_record)

        # Выполнение связывания сессии анонимного гостя (Anonymous Claiming)
        if anon_session_raw:
            anon_hash = self.hash_token(anon_session_raw)
            await db.execute(
                update(ConversionJob)
                .where(ConversionJob.session_token_hash == anon_hash)
                .where(ConversionJob.user_id.is_(None))
                .values(user_id=user.id)
            )

        await db.commit()
        return user, access_token, raw_refresh

    def verify_telegram_data(self, data: TelegramAuthRequest) -> bool:
        """Проверяет криптографическую валидность HMAC-SHA256 подписи Telegram виджета."""
        if not settings.TELEGRAM_BOT_TOKEN:
            return False

        secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode("utf-8")).digest()
        data_dict = data.model_dump(exclude={"hash"}, exclude_none=True)
        sorted_pairs = [f"{k}={v}" for k, v in sorted(data_dict.items())]
        data_check_string = "\n".join(sorted_pairs)

        calculated_hash = _hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return _hmac.compare_digest(calculated_hash, data.hash)


auth_service = AuthService()
