from pydantic import BaseModel, Field, validator
from typing import Literal, List, Optional
from datetime import datetime

class KeyGenerationRequest(BaseModel):
    key_type: Literal["web_admin", "tenant_id"] = Field(..., description="Type of key to generate")
    count: int = Field(1, ge=1, le=100, description="Number of keys to generate (1-100)")

class GeneratedKey(BaseModel):
    key: str
    type: str
    generated_at: str
    info: dict

class KeyGenerationResponse(BaseModel):
    keys: List[GeneratedKey]
    total_generated: int
    key_type: str

class KeyInfoRequest(BaseModel):
    key: str = Field(..., description="API key to analyze")

class KeyInfoResponse(BaseModel):
    key: str
    type: str
    generated_at: str
    prefix: Optional[str] = None
    identifier: Optional[str] = None
    format: Optional[str] = None
    valid: bool

class KeyValidationRequest(BaseModel):
    api_key: str = Field(..., description="API key to validate")
    provider: Literal["openrouter"] = Field(..., description="Provider to validate against")

class KeyValidationResponse(BaseModel):
    valid: bool
    models: Optional[List[str]] = None
    error: Optional[str] = None