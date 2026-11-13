import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user, get_or_create_dev_user
from app.models.job import ConversionJob
from app.models.token import RefreshToken
from app.models.usage import DailyUsage
from app.models.user import User
from app.schemas.auth import (
    AuthTokenResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    TelegramAuthRequest,
    UserProfileResponse,
    VerifyCodeRequest,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Аутентификация"])
settings = get_settings()

_REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    """Устанавливает HttpOnly cookie с refresh токеном."""
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=settings.ENVIRONMENT == "prod",
        samesite="lax",
        max_age=_REFRESH_COOKIE_MAX_AGE,
        path="/api/v1/auth",
    )


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    request: Request,
    body: MagicLinkRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MagicLinkResponse:
    """Запрос отправки 6-значного OTP кода и прямой ссылки на email."""
    # request используется для будущей интеграции slowapi rate limiting
    _ = request
    await auth_service.create_magic_code(db, body.email)
    return MagicLinkResponse(email=body.email)


@router.post("/verify-code", response_model=AuthTokenResponse)
async def verify_code(
    body: VerifyCodeRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    anon_session: Annotated[str | None, Cookie()] = None,
) -> AuthTokenResponse:
    """Проверка 6-значного кода, выдача access JWT и установка refresh cookie."""
    user, access_token, raw_refresh = await auth_service.verify_magic_code(
        db, body.email, body.code, anon_session_raw=anon_session
    )
    _ = user
    _set_refresh_cookie(response, raw_refresh)
    return AuthTokenResponse(access_token=access_token)


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> AuthTokenResponse:
    """Ротация refresh токена и выдача нового access токена."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Refresh токен отсутствует", "code": "NO_REFRESH_TOKEN"},
        )
    token_hash = auth_service.hash_token(refresh_token)
    now_utc = datetime.now(UTC)
    record = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.revoked.is_(False))
        .where(RefreshToken.expires_at > now_utc)
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Недействительный refresh токен",
                "code": "INVALID_REFRESH_TOKEN",
            },
        )

    # Ротация: отзываем старый, создаем новый
    record.revoked = True
    user = await db.scalar(select(User).where(User.id == record.user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Пользователь не найден", "code": "USER_NOT_FOUND"},
        )

    access_token, _ = auth_service.generate_jwt_access_token(user.id)
    raw_refresh = secrets.token_urlsafe(48)
    new_record = RefreshToken(
        user_id=user.id,
        token_hash=auth_service.hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_record)
    await db.commit()

    _set_refresh_cookie(response, raw_refresh)
    return AuthTokenResponse(access_token=access_token)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> None:
    """Отзыв refresh токена и очистка cookie."""
    if refresh_token:
        token_hash = auth_service.hash_token(refresh_token)
        record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if record:
            record.revoked = True
            await db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post("/telegram", response_model=AuthTokenResponse)
async def telegram_auth(
    body: TelegramAuthRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    anon_session: Annotated[str | None, Cookie()] = None,
) -> AuthTokenResponse:
    """Авторизация через Telegram Login Widget."""
    if not auth_service.verify_telegram_data(body):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Недействительная подпись Telegram",
                "code": "INVALID_TELEGRAM_SIGNATURE",
            },
        )

    user = await db.scalar(select(User).where(User.telegram_id == body.id))
    if not user:
        user = User(telegram_id=body.id, telegram_username=body.username, plan="free")
        db.add(user)
        await db.flush()

    # Anonymous claiming
    if anon_session:
        anon_hash = auth_service.hash_token(anon_session)
        await db.execute(
            update(ConversionJob)
            .where(ConversionJob.session_token_hash == anon_hash)
            .where(ConversionJob.user_id.is_(None))
            .values(user_id=user.id)
        )

    access_token, _ = auth_service.generate_jwt_access_token(user.id)
    raw_refresh = secrets.token_urlsafe(48)
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=auth_service.hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(token_record)
    await db.commit()

    _set_refresh_cookie(response, raw_refresh)
    return AuthTokenResponse(access_token=access_token)


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """Получение профиля авторизованного пользователя и остатка дневных конвертаций."""
    from app.services.converter_service import get_utc_today

    today = get_utc_today()
    usage = await db.scalar(
        select(DailyUsage.conversion_count)
        .where(DailyUsage.user_id == current_user.id)
        .where(DailyUsage.usage_date == today)
    )
    conversions_today = usage if usage else 0
    limit = 500 if current_user.plan == "pro" else 3

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        telegram_username=current_user.telegram_username,
        plan=current_user.plan,
        conversions_today=conversions_today,
        conversions_limit=limit,
        is_blocked=current_user.is_blocked,
        created_at=current_user.created_at,
    )


@router.get("/dev-session", response_model=AuthTokenResponse)
async def get_dev_session(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthTokenResponse:
    """Быстрая выдача токена для catishe@gmail.com в режиме быстрой разработки."""
    if not settings.DEV_FAST_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Dev-режим отключен", "code": "DEV_MODE_DISABLED"},
        )
    dev_user = await get_or_create_dev_user(db)
    access_token = auth_service.create_access_token(dev_user.id)
    return AuthTokenResponse(access_token=access_token)
