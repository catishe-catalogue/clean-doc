from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

settings = get_settings()

redis_pool: ConnectionPool = ConnectionPool.from_url(  # type: ignore[type-arg]
    settings.redis_url,
    max_connections=20,
    decode_responses=True,
)


def get_redis_client() -> Redis:  # type: ignore[type-arg]
    return Redis(connection_pool=redis_pool)
