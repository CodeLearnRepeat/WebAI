from fastapi import APIRouter, HTTPException, Header, Request
from app.core.config import settings
from app.services.tenants import get_tenant_config
from app.utils.domains import validate_origin

router = APIRouter()

@router.get("/validate-origin-test/{tenant_id}")
async def test_origin_validation(tenant_id: str, request: Request, x_admin_key: str = Header(None)):
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    config = get_tenant_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Tenant not found")

    origin = request.headers.get("origin") or request.headers.get("referer")
    is_valid = validate_origin(origin, config["allowed_domains"])
    return {
        "origin": origin,
        "allowed_domains": config["allowed_domains"],
        "is_valid": is_valid,
    }
@router.get("/rag/test/{tenant_id}")
async def rag_test(tenant_id: str, x_admin_key: str = Header(None)):
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    cfg = get_tenant_config(tenant_id)
    if not cfg or not cfg.get("rag") or not cfg["rag"].get("enabled"):
        raise HTTPException(status_code=400, detail="RAG not enabled for tenant")
    rag = cfg["rag"]
    if rag.get("provider") != "milvus":
        raise HTTPException(status_code=400, detail="Only milvus provider supported in this test")
    try:
        from app.services.vectorstores.milvus_store import get_milvus_retriever
        milvus = rag["milvus"]
        _ = get_milvus_retriever(
            uri=milvus["uri"],
            token=milvus.get("token"),
            db_name=milvus.get("db_name"),
            collection=milvus["collection"],
            vector_field=milvus.get("vector_field", "embedding"),
            text_field=milvus.get("text_field", "text"),
            metric_type=milvus.get("metric_type", "IP"),
        )
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}