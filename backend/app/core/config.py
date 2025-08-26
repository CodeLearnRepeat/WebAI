import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
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

    # Stripe Configuration
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

settings = Settings()