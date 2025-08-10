from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
import json, gzip, io, re
from jsonschema import Draft7Validator, ValidationError

from app.services.tenants import get_tenant_config
from app.services.rag_ingest import ingest_to_milvus

router = APIRouter()

class IngestDocument(BaseModel):
    text: str
    metadata: Optional[dict] = None

class RagIngestRequest(BaseModel):
    documents: List[IngestDocument]
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None

@router.post("/rag/ingest")
async def rag_ingest(payload: RagIngestRequest, x_tenant_id: str = Header(None)):
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    cfg = get_tenant_config(x_tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Tenant not found")
    rag = (cfg.get("rag") or {})
    if not rag.get("enabled"):
        raise HTTPException(status_code=400, detail="RAG not enabled for tenant")
    if (rag.get("provider") != "milvus") or not rag.get("milvus"):
        raise HTTPException(status_code=400, detail="Milvus/Zilliz configuration is required")

    emb_provider = payload.embedding_provider or rag.get("embedding_provider", "sentence_transformers")
    emb_model = payload.embedding_model or rag.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
    provider_keys = rag.get("provider_keys", {})
    provider_key = None
    if emb_provider == "openai":
        provider_key = provider_keys.get("openai")
        if not provider_key:
            raise HTTPException(status_code=400, detail="OpenAI embedding key missing in tenant rag.provider_keys.openai")
    elif emb_provider == "voyageai":
        provider_key = provider_keys.get("voyageai")
        if not provider_key:
            raise HTTPException(status_code=400, detail="VoyageAI embedding key missing in tenant rag.provider_keys.voyageai")

    texts = [d.text for d in payload.documents]
    metas = [d.metadata or {} for d in payload.documents]
    if not texts:
        return {"upserted": 0}
    result = ingest_to_milvus(
        texts=texts,
        metadatas=metas,
        milvus_conf=rag["milvus"],
        emb_provider=emb_provider,
        emb_model=emb_model,
        provider_key=provider_key,
    )
    return {"status": "ok", **result}

# -------- File upload ingestion with schema mapping --------

def _parse_dot_path(path: str, obj: Any) -> Any:
    # Supports dot paths and [index], e.g., "items[0].content"
    if not path:
        return None
    cur = obj
    token_re = re.compile(r"\.?([^[.\]]+)|\[(\d+)\]")
    for m in token_re.finditer(path):
        key, idx = m.groups()
        if key:
            if not isinstance(cur, dict) or key not in cur:
                return None
            cur = cur[key]
        else:
            i = int(idx)
            if not isinstance(cur, list) or i >= len(cur):
                return None
            cur = cur[i]
    return cur

def _maybe_gzip_readall(file_bytes: bytes, filename: str) -> bytes:
    if filename.endswith(".gz"):
        return gzip.decompress(file_bytes)
    # magic header check
    if len(file_bytes) >= 2 and file_bytes[0] == 0x1F and file_bytes[1] == 0x8B:
        return gzip.decompress(file_bytes)
    return file_bytes

@router.post("/rag/ingest-file")
async def rag_ingest_file(
    x_tenant_id: str = Header(None),
    file: UploadFile = File(...),
    schema_json: str = Form(...),  # user-provided schema/mapping JSON
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None)
):
    """
    Multipart ingestion endpoint.

    schema_json structure:
    {
      "format": "json_array" | "ndjson",
      "validation_schema": { ... JSON Schema Draft-07 ... },  // optional
      "mapping": {
        "content_path": "path.to.field",
        "metadata_paths": { "url": "path.to.url", "title": "meta.title", ... }
      },
      "chunking": { "strategy": "none" | "recursive", "max_chars": 1200, "overlap": 150 } // optional
    }
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    cfg = get_tenant_config(x_tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Tenant not found")

    rag = (cfg.get("rag") or {})
    if not rag.get("enabled"):
        raise HTTPException(status_code=400, detail="RAG not enabled for tenant")
    if (rag.get("provider") != "milvus") or not rag.get("milvus"):
        raise HTTPException(status_code=400, detail="Milvus/Zilliz configuration is required")

    try:
        schema = json.loads(schema_json)
    except Exception:
        raise HTTPException(status_code=400, detail="schema_json must be valid JSON")

    fmt = (schema.get("format") or "json_array").lower()
    if fmt not in ("json_array", "ndjson"):
        raise HTTPException(status_code=400, detail="schema_json.format must be 'json_array' or 'ndjson'")

    validation_schema = schema.get("validation_schema")
    mapping = schema.get("mapping") or {}
    content_path = mapping.get("content_path")
    metadata_paths = mapping.get("metadata_paths") or {}
    chunking = schema.get("chunking") or {"strategy": "none"}

    if not content_path:
        raise HTTPException(status_code=400, detail="schema_json.mapping.content_path is required")

    # Embedding provider selection (override tenant if provided)
    emb_provider = embedding_provider or rag.get("embedding_provider", "sentence_transformers")
    emb_model = embedding_model or rag.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
    provider_keys = rag.get("provider_keys", {})
    provider_key = None
    if emb_provider == "openai":
        provider_key = provider_keys.get("openai")
        if not provider_key:
            raise HTTPException(status_code=400, detail="OpenAI embedding key missing in tenant rag.provider_keys.openai")
    elif emb_provider == "voyageai":
        provider_key = provider_keys.get("voyageai")
        if not provider_key:
            raise HTTPException(status_code=400, detail="VoyageAI embedding key missing in tenant rag.provider_keys.voyageai")

    # Read file (support gz)
    raw = await file.read()
    raw = _maybe_gzip_readall(raw, file.filename or "")

    items: List[Dict[str, Any]] = []
    try:
        if fmt == "json_array":
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, list):
                raise HTTPException(status_code=400, detail="File content must be a JSON array for format=json_array")
            items = data
        else:
            # NDJSON: one JSON object per line [tinybird.co](https://www.tinybird.co/docs/guides/ingest-ndjson-data.html), [estuary.dev](https://estuary.dev/blog/json-to-bigquery/)
            items = []
            for line in io.StringIO(raw.decode("utf-8")):
                s = line.strip()
                if not s:
                    continue
                items.append(json.loads(s))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Validate items with JSON Schema if provided [json-schema.org](https://json-schema.org/), [docs.seqera.io](https://docs.seqera.io/platform-cloud/pipeline-schema/overview), [byteplus.com](https://www.byteplus.com/en/topic/542256)
    if validation_schema:
        try:
            validator = Draft7Validator(validation_schema)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid validation_schema: {str(e)}")
        errors = []
        for i, it in enumerate(items):
            for err in validator.iter_errors(it):
                errors.append({"index": i, "error": err.message, "path": list(err.path)})
        if errors:
            # Provide actionable feedback on first N errors
            raise HTTPException(status_code=400, detail={"validation_errors": errors[:20]})

    # Extract content + metadata
    def chunk_text(text: str) -> List[str]:
        if not text:
            return []
        strat = (chunking.get("strategy") or "none").lower()
        if strat == "none":
            return [text]
        # simple recursive char-based chunking
        max_chars = int(chunking.get("max_chars", 1200))
        overlap = int(chunking.get("overlap", 150))
        chunks = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + max_chars)
            chunks.append(text[start:end])
            if end == n:
                break
            start = max(0, end - overlap)
        return chunks

    texts: List[str] = []
    metas: List[dict] = []
    for it in items:
        content = _parse_dot_path(content_path, it)
        if not isinstance(content, str):
            # skip invalid or empty content
            continue
        chunks = chunk_text(content)
        if not chunks:
            continue
        # build metadata from mapping paths
        md: Dict[str, Any] = {}
        for k, p in metadata_paths.items():
            md[k] = _parse_dot_path(p, it)
        # replicate metadata per chunk
        for ch in chunks:
            texts.append(ch)
            metas.append(md)

    if not texts:
        return {"status": "ok", "upserted": 0}

    result = ingest_to_milvus(
        texts=texts,
        metadatas=metas,
        milvus_conf=rag["milvus"],
        emb_provider=emb_provider,
        emb_model=emb_model,
        provider_key=provider_key,
    )
    return {"status": "ok", **result}