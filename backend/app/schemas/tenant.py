from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, List, Literal, Dict

class RagMilvusConfig(BaseModel):
    uri: str
    token: Optional[str] = None
    db_name: Optional[str] = None
    collection: str
    vector_field: str = "embedding"
    text_field: str = "text"
    metadata_field: Optional[str] = "metadata"  # JSON string field for metadata
    metric_type: Literal["IP", "COSINE", "L2"] = "IP"

class RagConfig(BaseModel):
    enabled: bool = False
    self_rag_enabled: bool = False
    provider: Literal["milvus"] = "milvus"
    milvus: Optional[RagMilvusConfig] = None
    embedding_provider: Literal["sentence_transformers", "openai", "voyageai"] = "sentence_transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    provider_keys: Dict[str, str] = {}
    top_k: int = 3

class TenantRegistration(BaseModel):
    openrouter_api_key: str
    system_prompt: str
    allowed_domains: List[str]
    model: str = "anthropic/claude-3.5-sonnet"
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    rag: Optional[RagConfig] = None

    @field_validator('allowed_domains')
    def validate_domains(cls, v):
        if not v:
            raise ValueError("At least one allowed domain is required")
        for domain in v:
            if not domain or domain.strip() != domain:
                raise ValueError(f"Invalid domain: {domain}")
        return v

class TenantUpdate(BaseModel):
    system_prompt: Optional[str] = None
    allowed_domains: Optional[List[str]] = None
    model: Optional[str] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    active: Optional[bool] = None
    rag: Optional[RagConfig] = None