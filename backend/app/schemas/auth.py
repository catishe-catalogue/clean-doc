from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class MagicLinkRequest(BaseModel):
    """Запрос на отправку 6-значного кода и ссылки на email."""

    email: EmailStr = Field(..., description="Электронная почта пользователя")


class MagicLinkResponse(BaseModel):
    """Подтверждение отправки письма."""

    message: str = Field(
        default="Одноразовый код успешно отправлен на указанную почту",
        description="Информационное сообщение для пользователя",
    )
    email: EmailStr
    expires_in_seconds: int = Field(default=900, description="Время жизни кода в секундах")


class VerifyCodeRequest(BaseModel):
    """Подтверждение 6-значного OTP-кода или токена ссылки."""

    email: EmailStr = Field(..., description="Электронная почта пользователя")
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-значный цифровой код из письма",
    )


class TelegramAuthRequest(BaseModel):
    """Данные авторизации от официального Telegram Login Widget."""

    id: int = Field(..., description="Идентификатор пользователя в Telegram")
    first_name: str | None = Field(default=None, description="Имя пользователя")
    last_name: str | None = Field(default=None, description="Фамилия пользователя")
    username: str | None = Field(default=None, description="Юзернейм в Telegram")
    photo_url: str | None = Field(default=None, description="Аватар пользователя")
    auth_date: int = Field(..., description="UNIX timestamp момента авторизации")
    hash: str = Field(..., description="HMAC-SHA256 подпись параметров виджета")


class AuthTokenResponse(BaseModel):
    """Ответ успешной аутентификации с JWT access-токеном."""

    access_token: str = Field(..., description="JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Тип авторизационного токена")
    expires_in: int = Field(default=900, description="Срок жизни токена в секундах (15 минут)")


class UserProfileResponse(BaseModel):
    """Профиль текущего пользователя и состояние лимитов тарифа."""

    id: UUID
    email: str | None = None
    telegram_username: str | None = None
    plan: str = Field(..., description="Текущий тарифный план: free или pro")
    conversions_today: int = Field(..., description="Количество использованных конвертаций сегодня")
    conversions_limit: int = Field(
        ..., description="Дневной лимит конвертаций: 3 для Free, 500 для PRO"
    )
    is_blocked: bool
    created_at: datetime
