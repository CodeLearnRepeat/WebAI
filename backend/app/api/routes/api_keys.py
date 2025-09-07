from fastapi import APIRouter, HTTPException, Header, Query
from app.core.config import settings
from app.schemas.api_keys import (
    KeyGenerationRequest, 
    KeyGenerationResponse, 
    KeyInfoRequest, 
    KeyInfoResponse,
    GeneratedKey
)
from app.services.api_keys import (
    generate_api_key, 
    generate_multiple_keys, 
    get_key_info
)
from datetime import datetime

router = APIRouter()

@router.post("/generate", response_model=KeyGenerationResponse)
async def generate_keys(
    request: KeyGenerationRequest,
    x_admin_key: str = Header(None)
):
    """Generate API keys of the specified type.
    
    Requires admin authentication to generate keys.
    """
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        # Generate the requested keys
        keys = generate_multiple_keys(request.key_type, request.count)
        
        # Create response with key information
        generated_keys = []
        for key in keys:
            key_info = get_key_info(key)
            generated_keys.append(GeneratedKey(
                key=key,
                type=key_info["type"],
                generated_at=key_info["generated_at"],
                info=key_info
            ))
        
        return KeyGenerationResponse(
            keys=generated_keys,
            total_generated=len(keys),
            key_type=request.key_type
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate keys: {str(e)}")

@router.get("/generate/{key_type}")
async def generate_single_key(
    key_type: str,
    x_admin_key: str = Header(None)
):
    """Generate a single API key of the specified type (quick endpoint).
    
    Args:
        key_type: Either 'web_admin' or 'tenant_id'
    """
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    if key_type not in ["web_admin", "tenant_id"]:
        raise HTTPException(
            status_code=400, 
            detail="key_type must be 'web_admin' or 'tenant_id'"
        )
    
    try:
        key = generate_api_key(key_type)
        key_info = get_key_info(key)
        
        return {
            "key": key,
            "type": key_type,
            "generated_at": datetime.utcnow().isoformat(),
            "info": key_info
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate key: {str(e)}")

@router.post("/info", response_model=KeyInfoResponse)
async def analyze_key(request: KeyInfoRequest):
    """Analyze an API key and return its information.
    
    This endpoint does not require authentication as it only analyzes format.
    """
    try:
        info = get_key_info(request.key)
        
        return KeyInfoResponse(
            key=info["key"],
            type=info["type"],
            generated_at=info["generated_at"],
            prefix=info.get("prefix"),
            identifier=info.get("identifier"),
            format=info.get("format"),
            valid=info["type"] != "unknown"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze key: {str(e)}")

@router.get("/info/{key}")
async def analyze_key_get(key: str):
    """Analyze an API key via GET request.
    
    Args:
        key: The API key to analyze
    """
    try:
        info = get_key_info(key)
        
        return {
            "key": info["key"],
            "type": info["type"],
            "generated_at": info["generated_at"],
            "prefix": info.get("prefix"),
            "identifier": info.get("identifier"),
            "format": info.get("format"),
            "valid": info["type"] != "unknown"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze key: {str(e)}")

@router.get("/examples")
async def get_key_examples():
    """Get examples of each key type format.
    
    This endpoint provides format examples without requiring authentication.
    """
    return {
        "web_admin": {
            "format": "UUID v4",
            "example": "0f81c721-dffa-4d78-9c63-a4f4bb037f82",
            "description": "Standard UUID format for web admin authentication"
        },
        "tenant_id": {
            "format": "tenant_ + base64url",
            "example": "tenant_PyKfd99yWzORf6ExHk0Nbw",
            "description": "Tenant identifier with 'tenant_' prefix and URL-safe base64 suffix"
        }
    }