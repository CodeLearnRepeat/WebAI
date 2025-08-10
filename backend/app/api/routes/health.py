from fastapi import APIRouter
from app.core.redis import get_redis_client, get_conversation_redis

router = APIRouter()

@router.get("/health")
async def health_check():
    r_main = get_redis_client()
    r_conv = get_conversation_redis()
    return {
        "status": "healthy",
        "redis_config": r_main is not None,
        "redis_conversations": r_conv is not None,
    }