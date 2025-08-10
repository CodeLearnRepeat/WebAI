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