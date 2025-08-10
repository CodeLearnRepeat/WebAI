import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    CONVERSATION_REDIS_URL: str | None = os.getenv("CONVERSATION_REDIS_URL")
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    WEBAI_ADMIN_KEY: str = os.getenv("WEBAI_ADMIN_KEY", "your-secure-admin-key")

    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

    HTTP_REFERER: str = os.getenv("OPENROUTER_HTTP_REFERER", "https://webai.chat")
    X_TITLE: str = os.getenv("OPENROUTER_X_TITLE", "WebAI Chat Widget")

settings = Settings()