from fastapi import APIRouter, HTTPException, Header
from app.core.config import settings
from app.schemas.tenant import TenantRegistration, TenantUpdate
from app.services.tenants import generate_tenant_id, get_tenant_config, save_tenant_config, new_tenant_config

router = APIRouter()

@router.post("/register-tenant")
async def register_tenant(registration: TenantRegistration, x_admin_key: str = Header(None)):
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    tenant_id = generate_tenant_id()
    config = new_tenant_config(
        registration,
        defaults={"minute": settings.RATE_LIMIT_PER_MINUTE, "hour": settings.RATE_LIMIT_PER_HOUR},
    )
    # Add RAG config if provided (validate minimal fields when enabled)
    if registration.rag and registration.rag.enabled:
        rag = registration.rag.dict()
        if rag["provider"] == "milvus":
            milvus = rag.get("milvus") or {}
            required = ["uri", "collection"]
            for field in required:
                if not milvus.get(field):
                    raise HTTPException(status_code=400, detail=f"rag.milvus.{field} is required when RAG is enabled")
        emb_provider = rag.get("embedding_provider", "sentence_transformers")
        if emb_provider == "openai" and not (rag.get("provider_keys", {}).get("openai")):
            raise HTTPException(status_code=400, detail="OpenAI embedding requires rag.provider_keys.openai")
        if emb_provider == "voyageai" and not (rag.get("provider_keys", {}).get("voyageai")):
            raise HTTPException(status_code=400, detail="VoyageAI embedding requires rag.provider_keys.voyageai")
        config["rag"] = rag

    save_tenant_config(tenant_id, config)
    print(f"New tenant registered: {tenant_id} with domains: {registration.allowed_domains}")
    return {"tenant_id": tenant_id, "message": "Tenant registered successfully", "allowed_domains": registration.allowed_domains}

@router.put("/update-tenant/{tenant_id}")
async def update_tenant(tenant_id: str, update: TenantUpdate, x_admin_key: str = Header(None)):
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    config = get_tenant_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if update.system_prompt is not None:
        config["system_prompt"] = update.system_prompt
    if update.allowed_domains is not None:
        config["allowed_domains"] = update.allowed_domains
    if update.model is not None:
        config["model"] = update.model
    if update.rate_limit_per_minute is not None:
        config["rate_limit_per_minute"] = update.rate_limit_per_minute
    if update.rate_limit_per_hour is not None:
        config["rate_limit_per_hour"] = update.rate_limit_per_hour
    if update.active is not None:
        config["active"] = update.active
    if update.rag is not None:
        rag = update.rag.dict()
        if rag.get("enabled"):
            if rag.get("provider") == "milvus":
                milvus = rag.get("milvus") or {}
                if not milvus.get("uri") or not milvus.get("collection"):
                    raise HTTPException(status_code=400, detail="rag.milvus.uri and rag.milvus.collection are required when enabling RAG")
            emb_provider = rag.get("embedding_provider", "sentence_transformers")
            if emb_provider == "openai" and not (rag.get("provider_keys", {}).get("openai")):
                raise HTTPException(status_code=400, detail="OpenAI embedding requires rag.provider_keys.openai")
            if emb_provider == "voyageai" and not (rag.get("provider_keys", {}).get("voyageai")):
                raise HTTPException(status_code=400, detail="VoyageAI embedding requires rag.provider_keys.voyageai")
        config["rag"] = rag

    # Update timestamp
    from datetime import datetime
    config["updated_at"] = datetime.utcnow().isoformat()
    save_tenant_config(tenant_id, config)

    return {"message": "Tenant updated successfully", "tenant_id": tenant_id, "updated_fields": update.dict(exclude_unset=True)}