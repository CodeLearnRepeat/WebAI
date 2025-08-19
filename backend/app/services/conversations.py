import json
from typing import List, Dict
from app.core.redis import get_conversation_redis

def get_conversation_key(tenant_id: str, session_id: str) -> str:
    return f"conversation:{tenant_id}:{session_id}"

async def get_conversation_history(tenant_id: str, session_id: str, use_redis: bool) -> List[Dict]:
    r = get_conversation_redis()
    print(f"[DEBUG] get_conversation_history - Redis client exists: {r is not None}, use_redis: {use_redis}")
    if not use_redis or not r:
        print(f"[DEBUG] Returning empty history - Redis disabled or unavailable")
        return []
    try:
        key = get_conversation_key(tenant_id, session_id)
        print(f"[DEBUG] Looking for conversation key: {key}")
        data = r.get(key)
        if data:
            history = json.loads(data)
            print(f"[DEBUG] Found conversation with {len(history)} messages")
            return history
        else:
            print(f"[DEBUG] No conversation found for key: {key}")
    except Exception as e:
        print(f"Redis conversation error: {e}")
    return []

async def save_conversation_history(tenant_id: str, session_id: str, messages: List[Dict], use_redis: bool):
    r = get_conversation_redis()
    print(f"[DEBUG] save_conversation_history - Redis client exists: {r is not None}, use_redis: {use_redis}")
    if not use_redis or not r:
        print(f"[DEBUG] Not saving - Redis disabled or unavailable")
        return
    try:
        key = get_conversation_key(tenant_id, session_id)
        print(f"[DEBUG] Saving {len(messages)} messages to key: {key}")
        r.setex(key, 86400 * 30, json.dumps(messages))  # 30 days TTL
        print(f"[DEBUG] Successfully saved conversation")
    except Exception as e:
        print(f"Redis conversation save error: {e}")