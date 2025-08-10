from pydantic import BaseModel
from typing import Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str
    use_redis_conversations: bool = False
    # Per-request overrides
    use_rag: Optional[bool] = None  # if None, use tenant default
    rag_top_k: Optional[int] = None