import redis
from functools import lru_cache
from app.core.config import settings

@lru_cache
def get_redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)

@lru_cache
def get_conversation_redis() -> redis.Redis | None:
    return redis.from_url(settings.CONVERSATION_REDIS_URL) if settings.CONVERSATION_REDIS_URL else None