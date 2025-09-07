import json
from datetime import datetime
from typing import Optional, Dict
from app.core.redis import get_redis_client
from app.services.api_keys import generate_tenant_id

def get_tenant_config(tenant_id: str) -> Optional[Dict]:
    try:
        r = get_redis_client()
        data = r.get(f"tenant:{tenant_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"Redis error getting tenant config: {e}")
    return None

def save_tenant_config(tenant_id: str, config: Dict):
    try:
        r = get_redis_client()
        r.set(f"tenant:{tenant_id}", json.dumps(config), ex=None)
    except Exception as e:
        print(f"Redis error saving tenant config: {e}")
        raise

def new_tenant_config(registration, defaults) -> Dict:
    cfg = {
        "openrouter_api_key": registration.openrouter_api_key,
        "system_prompt": registration.system_prompt,
        "model": registration.model,
        "allowed_domains": registration.allowed_domains,
        "rate_limit_per_minute": registration.rate_limit_per_minute or defaults["minute"],
        "rate_limit_per_hour": registration.rate_limit_per_hour or defaults["hour"],
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    if getattr(registration, "rag", None):
        cfg["rag"] = registration.rag.dict()
    return cfg