from typing import List, Dict, AsyncGenerator, Optional
import json
import httpx
from app.core.config import settings

async def stream_openrouter_response(messages: List[Dict], api_key: str, model: str) -> AsyncGenerator[str, None]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.HTTP_REFERER,
        "X-Title": settings.X_TITLE,
    }
    payload = {"model": model, "messages": messages, "stream": True}
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", settings.OPENROUTER_API_URL, headers=headers, json=payload, timeout=60.0) as response:
            if response.status_code != 200:
                error_data = await response.aread()
                yield f"data: {json.dumps({'error': error_data.decode()})}\n\n"
                return
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield f"{line}\n\n"

async def chat_completion(messages: List[Dict], api_key: str, model: str, response_format: Optional[Dict] = None) -> Dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.HTTP_REFERER,
        "X-Title": settings.X_TITLE,
    }
    payload: Dict = {"model": model, "messages": messages}
    if response_format:
        payload["response_format"] = response_format  # OpenAI-compatible; may be ignored by some models
    async with httpx.AsyncClient() as client:
        resp = await client.post(settings.OPENROUTER_API_URL, headers=headers, json=payload, timeout=60.0)
        resp.raise_for_status()
        return resp.json()

async def validate_openrouter_key(api_key: str) -> Dict:
    """
    Validate OpenRouter API key by attempting to fetch available models.
    Returns dict with 'valid' bool and 'models' list if valid.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.HTTP_REFERER,
        "X-Title": settings.X_TITLE,
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Use OpenRouter's models endpoint to validate the key
            models_url = "https://openrouter.ai/api/v1/models"
            resp = await client.get(models_url, headers=headers, timeout=30.0)
            
            if resp.status_code == 401:
                return {"valid": False, "error": "Invalid API key"}
            elif resp.status_code == 403:
                return {"valid": False, "error": "API key access denied"}
            elif resp.status_code != 200:
                return {"valid": False, "error": f"API validation failed: {resp.status_code}"}
            
            # Extract model IDs from response
            models_data = resp.json()
            if "data" in models_data:
                model_ids = [model.get("id", "") for model in models_data["data"] if model.get("id")]
                # Filter to commonly used models for better UX
                preferred_models = [
                    "anthropic/claude-3.5-sonnet",
                    "anthropic/claude-3-haiku",
                    "openai/gpt-4o",
                    "openai/gpt-4o-mini",
                    "meta-llama/llama-3.2-90b-vision-instruct",
                    "google/gemini-pro-1.5"
                ]
                available_preferred = [m for m in preferred_models if m in model_ids]
                final_models = available_preferred if available_preferred else model_ids[:10]  # Top 10 if no preferred found
                
                return {"valid": True, "models": final_models}
            else:
                return {"valid": False, "error": "Unexpected API response format"}
                
    except httpx.TimeoutException:
        return {"valid": False, "error": "API validation timeout"}
    except Exception as e:
        return {"valid": False, "error": f"Validation error: {str(e)}"}