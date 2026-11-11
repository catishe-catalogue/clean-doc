import hashlib
import secrets
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

logger = structlog.get_logger()
settings = get_settings()

_bearer = HTTPBearer(auto_error=False)


def hash_token(raw_token: str) -> str:
    """Вычисляет SHA-256 хеш строки для безопасного хранения в БД."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_secure_token(length_bytes: int = 32) -> str:
    """Генерирует криптографически стойкий URL-safe токен."""
    return secrets.token_urlsafe(length_bytes)


def _decode_access_token(token: str) -> UUID:
    """Декодирует JWT access-токен и возвращает user_id."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        sub = payload.get("sub")
        token_type = payload.get("type")
        if not sub or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Недействительный токен", "code": "INVALID_TOKEN"},
            )
        return UUID(str(sub))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Недействительный токен", "code": "INVALID_TOKEN"},
        ) from None


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User:
    """Обязательная зависимость: возвращает авторизованного пользователя или 401."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Необходима авторизация", "code": "UNAUTHORIZED"},
        )
    user_id = _decode_access_token(credentials.credentials)
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Пользователь не найден", "code": "USER_NOT_FOUND"},
        )
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Учетная запись заблокирована", "code": "USER_BLOCKED"},
        )
    return user


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> User | None:
    """Опциональная зависимость: возвращает пользователя если токен валиден, иначе None."""
    if not credentials:
        return None
    try:
        user_id = _decode_access_token(credentials.credentials)
        return await db.scalar(select(User).where(User.id == user_id))
    except HTTPException:
        return None
