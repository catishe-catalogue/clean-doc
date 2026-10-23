import hashlib
import secrets


def hash_token(raw_token: str) -> str:
    """Вычисляет SHA-256 хеш строки для безопасного хранения в БД."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_secure_token(length_bytes: int = 32) -> str:
    """Генерирует криптографически стойкий URL-safe токен."""
    return secrets.token_urlsafe(length_bytes)
