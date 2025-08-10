import json
from typing import List, Dict
from app.core.redis import get_conversation_redis

def get_conversation_key(tenant_id: str, session_id: str) -> str:
    return f"conversation:{tenant_id}:{session_id}"

async def get_conversation_history(tenant_id: str, session_id: str, use_redis: bool) -> List[Dict]:
    r = get_conversation_redis()
    if not use_redis or not r:
        return []
    try:
        key = get_conversation_key(tenant_id, session_id)
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"Redis conversation error: {e}")
    return []

async def save_conversation_history(tenant_id: str, session_id: str, messages: List[Dict], use_redis: bool):
    r = get_conversation_redis()
    if not use_redis or not r:
        return
    try:
        key = get_conversation_key(tenant_id, session_id)
        r.setex(key, 86400 * 30, json.dumps(messages))  # 30 days TTL
    except Exception as e:
        print(f"Redis conversation save error: {e}")