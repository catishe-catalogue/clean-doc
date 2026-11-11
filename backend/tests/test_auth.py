from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ConversionJob
from app.models.token import RefreshToken
from app.models.user import User
from app.services.auth_service import auth_service

# ---------------------------------------------------------------------------
# Вспомогательные фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
async def registered_user(db_session: AsyncSession) -> User:
    """Создает зарегистрированного пользователя в тестовой БД."""
    user = User(email="test@example.com", plan="free")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def user_with_code(db_session: AsyncSession) -> tuple[User, str]:
    """Создает пользователя с актуальным OTP-кодом."""
    user = User(email="otp@example.com", plan="free")
    db_session.add(user)
    await db_session.flush()

    raw_code = "123456"
    user.magic_code_hash = auth_service.hash_token(raw_code)
    user.magic_code_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    user.magic_code_attempts = 0
    await db_session.commit()
    return user, raw_code


@pytest.fixture
async def user_with_refresh_token(
    db_session: AsyncSession,
) -> tuple[User, str]:
    """Создает пользователя с действующим refresh токеном."""
    user = User(email="refresh@example.com", plan="free")
    db_session.add(user)
    await db_session.flush()

    raw_refresh = "valid_refresh_token_string_long_enough"
    record = RefreshToken(
        user_id=user.id,
        token_hash=auth_service.hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(record)
    await db_session.commit()
    return user, raw_refresh


# ---------------------------------------------------------------------------
# Тесты magic-link flow + bruteforce protection
# ---------------------------------------------------------------------------


async def test_magic_link_sends_email(async_client: AsyncClient) -> None:
    """POST /auth/magic-link вызывает email_service и возвращает 200."""
    with patch(
        "app.services.auth_service.email_service.send_magic_code",
        new_callable=AsyncMock,
    ) as mock_send:
        resp = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "newuser@example.com"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "newuser@example.com"
    assert body["expires_in_seconds"] == 900
    mock_send.assert_awaited_once()


async def test_magic_link_blocked_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /auth/magic-link для заблокированного пользователя возвращает 403."""
    user = User(email="blocked@example.com", plan="free", is_blocked=True)
    db_session.add(user)
    await db_session.commit()

    with patch(
        "app.services.auth_service.email_service.send_magic_code",
        new_callable=AsyncMock,
    ):
        resp = await async_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "blocked@example.com"},
        )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "USER_BLOCKED"


async def test_magic_link_bruteforce_protection(async_client: AsyncClient) -> None:
    """После 5 неудачных попыток шестая возвращает 429 MAX_ATTEMPTS_EXCEEDED."""
    email = "bruteforce@example.com"

    with patch(
        "app.services.auth_service.email_service.send_magic_code",
        new_callable=AsyncMock,
    ):
        resp = await async_client.post("/api/v1/auth/magic-link", json={"email": email})
    assert resp.status_code == 200

    # 5 неудачных попыток
    for _ in range(5):
        bad = await async_client.post(
            "/api/v1/auth/verify-code",
            json={"email": email, "code": "000000"},
        )
        assert bad.status_code == 400

    # Шестая — 429
    blocked = await async_client.post(
        "/api/v1/auth/verify-code",
        json={"email": email, "code": "000000"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "MAX_ATTEMPTS_EXCEEDED"


# ---------------------------------------------------------------------------
# Тесты verify-code — успешный путь + cookie
# ---------------------------------------------------------------------------


async def test_verify_correct_code_sets_cookie(
    async_client: AsyncClient,
    user_with_code: tuple[User, str],
) -> None:
    """POST /auth/verify-code с корректным кодом возвращает access_token и устанавливает cookie."""
    user, raw_code = user_with_code

    resp = await async_client.post(
        "/api/v1/auth/verify-code",
        json={"email": user.email, "code": raw_code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert "refresh_token" in resp.cookies


async def test_verify_wrong_code_increments_attempts(
    async_client: AsyncClient,
    user_with_code: tuple[User, str],
    db_session: AsyncSession,
) -> None:
    """Неверный код увеличивает счетчик попыток и возвращает INVALID_CODE."""
    user, _ = user_with_code

    resp = await async_client.post(
        "/api/v1/auth/verify-code",
        json={"email": user.email, "code": "999999"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_CODE"

    await db_session.refresh(user)
    assert user.magic_code_attempts == 1


async def test_verify_no_code_requested(async_client: AsyncClient) -> None:
    """Попытка верификации без запроса кода возвращает INVALID_CODE."""
    resp = await async_client.post(
        "/api/v1/auth/verify-code",
        json={"email": "nobody@example.com", "code": "123456"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_CODE"


# ---------------------------------------------------------------------------
# Тесты refresh token rotation
# ---------------------------------------------------------------------------


async def test_refresh_token_rotation(
    async_client: AsyncClient,
    user_with_refresh_token: tuple[User, str],
) -> None:
    """POST /auth/refresh ротирует токен: старый отзывается, новый выдается."""
    user, raw_refresh = user_with_refresh_token

    resp = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": raw_refresh},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    # Новая cookie должна быть установлена
    assert "refresh_token" in resp.cookies
    # Новый токен должен отличаться от старого
    assert resp.cookies["refresh_token"] != raw_refresh


async def test_refresh_missing_cookie(async_client: AsyncClient) -> None:
    """POST /auth/refresh без cookie возвращает NO_REFRESH_TOKEN."""
    resp = await async_client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "NO_REFRESH_TOKEN"


async def test_refresh_invalid_token(async_client: AsyncClient) -> None:
    """POST /auth/refresh с несуществующим токеном возвращает INVALID_REFRESH_TOKEN."""
    resp = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": "nonexistent_token"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_REFRESH_TOKEN"


# ---------------------------------------------------------------------------
# Тесты logout
# ---------------------------------------------------------------------------


async def test_logout_revokes_token(
    async_client: AsyncClient,
    user_with_refresh_token: tuple[User, str],
) -> None:
    """POST /auth/logout отзывает refresh токен в БД и очищает cookie."""
    user, raw_refresh = user_with_refresh_token

    resp = await async_client.post(
        "/api/v1/auth/logout",
        cookies={"refresh_token": raw_refresh},
    )
    assert resp.status_code == 204

    # После logout повторный refresh должен вернуть 401
    retry = await async_client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": raw_refresh},
    )
    assert retry.status_code == 401


async def test_logout_without_cookie(async_client: AsyncClient) -> None:
    """POST /auth/logout без cookie завершается успешно (204)."""
    resp = await async_client.post("/api/v1/auth/logout")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Тест Anonymous Claiming
# ---------------------------------------------------------------------------


async def test_anonymous_claiming_on_verify(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """При verify-code анонимные задачи переносятся на авторизованного пользователя."""
    # Создаем анонимную задачу
    anon_token = "anon_session_test_token_123"
    anon_hash = auth_service.hash_token(anon_token)
    job = ConversionJob(
        user_id=None,
        session_token_hash=anon_hash,
        target_format="docx",
        original_filename="test.pdf",
        file_size_bytes=1024,
        s3_input_key="input/test.pdf",
    )
    db_session.add(job)
    await db_session.flush()

    # Создаем пользователя с кодом
    user = User(email="claiming@example.com", plan="free")
    db_session.add(user)
    await db_session.flush()
    raw_code = "654321"
    user.magic_code_hash = auth_service.hash_token(raw_code)
    user.magic_code_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    user.magic_code_attempts = 0
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/auth/verify-code",
        json={"email": user.email, "code": raw_code},
        cookies={"anon_session": anon_token},
    )
    assert resp.status_code == 200

    await db_session.refresh(job)
    assert job.user_id == user.id


# ---------------------------------------------------------------------------
# Тест /me endpoint
# ---------------------------------------------------------------------------


async def test_get_me_requires_auth(async_client: AsyncClient) -> None:
    """GET /auth/me без токена возвращает 401."""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_get_me_returns_profile(
    async_client: AsyncClient,
    registered_user: User,
) -> None:
    """GET /auth/me с валидным JWT возвращает профиль пользователя."""
    access_token, _ = auth_service.generate_jwt_access_token(registered_user.id)

    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == registered_user.email
    assert body["plan"] == "free"
    assert body["conversions_today"] == 0
    assert body["conversions_limit"] == 3
