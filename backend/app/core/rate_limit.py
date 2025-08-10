import time
from app.core.redis import get_redis_client
from app.core.config import settings

async def check_rate_limit(tenant_id: str, tenant_config: dict) -> tuple[bool, str]:
    try:
        r = get_redis_client()
        current_minute = int(time.time() / 60)
        current_hour = int(time.time() / 3600)

        minute_limit = tenant_config.get("rate_limit_per_minute", settings.RATE_LIMIT_PER_MINUTE)
        hour_limit = tenant_config.get("rate_limit_per_hour", settings.RATE_LIMIT_PER_HOUR)

        minute_key = f"rate_limit:{tenant_id}:minute:{current_minute}"
        minute_count = r.incr(minute_key)
        r.expire(minute_key, 60)
        if minute_count > minute_limit:
            return False, f"Rate limit exceeded: {minute_limit} requests per minute"

        hour_key = f"rate_limit:{tenant_id}:hour:{current_hour}"
        hour_count = r.incr(hour_key)
        r.expire(hour_key, 3600)
        if hour_count > hour_limit:
            return False, f"Rate limit exceeded: {hour_limit} requests per hour"

        return True, ""
    except Exception as e:
        print(f"Rate limit check error: {e}")
        return True, ""  # fail-open