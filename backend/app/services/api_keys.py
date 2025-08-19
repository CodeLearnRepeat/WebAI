import uuid
import secrets
from typing import Literal
from datetime import datetime

def generate_web_admin_key() -> str:
    """Generate a web admin key in UUID format.
    
    Example: 0f81c721-dffa-4d78-9c63-a4f4bb037f82
    """
    return str(uuid.uuid4())

def generate_tenant_id() -> str:
    """Generate a tenant ID with 'tenant_' prefix.
    
    Example: tenant_PyKfd99yWzORf6ExHk0Nbw
    """
    return f"tenant_{secrets.token_urlsafe(16)}"

def generate_api_key(key_type: Literal["web_admin", "tenant_id"]) -> str:
    """Generate an API key of the specified type.
    
    Args:
        key_type: Either "web_admin" or "tenant_id"
        
    Returns:
        Generated API key string
        
    Raises:
        ValueError: If key_type is not supported
    """
    if key_type == "web_admin":
        return generate_web_admin_key()
    elif key_type == "tenant_id":
        return generate_tenant_id()
    else:
        raise ValueError(f"Unsupported key type: {key_type}. Must be 'web_admin' or 'tenant_id'")

def generate_multiple_keys(key_type: Literal["web_admin", "tenant_id"], count: int = 1) -> list[str]:
    """Generate multiple API keys of the specified type.
    
    Args:
        key_type: Either "web_admin" or "tenant_id"
        count: Number of keys to generate (default: 1, max: 100)
        
    Returns:
        List of generated API key strings
        
    Raises:
        ValueError: If key_type is not supported or count is invalid
    """
    if count < 1 or count > 100:
        raise ValueError("Count must be between 1 and 100")
    
    return [generate_api_key(key_type) for _ in range(count)]

def get_key_info(key: str) -> dict:
    """Get information about an API key.
    
    Args:
        key: The API key to analyze
        
    Returns:
        Dictionary with key information
    """
    info = {
        "key": key,
        "generated_at": datetime.utcnow().isoformat(),
    }
    
    if key.startswith("tenant_"):
        info["type"] = "tenant_id"
        info["prefix"] = "tenant_"
        info["identifier"] = key[7:]  # Remove 'tenant_' prefix
    elif _is_uuid_format(key):
        info["type"] = "web_admin"
        info["format"] = "uuid"
    else:
        info["type"] = "unknown"
    
    return info

def _is_uuid_format(key: str) -> bool:
    """Check if a string is in UUID format."""
    try:
        uuid.UUID(key)
        return True
    except ValueError:
        return False