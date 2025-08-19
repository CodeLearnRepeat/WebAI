import asyncio
import tempfile
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
import json, gzip, io, re
from jsonschema import Draft7Validator, ValidationError

from app.services.tenants import get_tenant_config
from app.services.rag_ingest import (
    ingest_to_milvus,
    ingest_to_milvus_async,
    ingest_json_file_streaming,
    create_enhanced_chunking_config,
    estimate_processing_time
)
from app.services.streaming_parser import get_file_stats
from app.services.background_tasks import get_task_manager, TaskStatus
from app.services.checkpoint_manager import get_checkpoint_manager
from app.services.progress_tracker import get_progress_tracker

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
        use_batching=True  # Enable intelligent batching
    )
    return {"status": "ok", **result}


@router.post("/rag/ingest-file-streaming")
async def rag_ingest_file_streaming(
    x_tenant_id: str = Header(None),
    file: UploadFile = File(...),
    schema_json: str = Form(...),
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    enable_chunking_enhancement: bool = Form(True),
    max_tokens_per_chunk: int = Form(1000)
):
    """
    Streaming ingestion endpoint for large JSON files.
    Uses memory-efficient streaming processing with token-aware batching.
    
    Schema JSON structure (same as ingest-file):
    {
      "format": "json_array" | "ndjson",
      "validation_schema": { ... JSON Schema Draft-07 ... },  // optional
      "mapping": {
        "content_path": "path.to.field",
        "metadata_paths": { "url": "path.to.url", "title": "meta.title", ... }
      },
      "chunking": { "strategy": "token_aware", "max_tokens": 1000, "overlap_tokens": 100 } // optional
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

    # Validate and enhance schema configuration
    fmt = (schema.get("format") or "json_array").lower()
    if fmt not in ("json_array", "ndjson"):
        raise HTTPException(status_code=400, detail="schema_json.format must be 'json_array' or 'ndjson'")

    mapping = schema.get("mapping") or {}
    content_path = mapping.get("content_path")
    if not content_path:
        raise HTTPException(status_code=400, detail="schema_json.mapping.content_path is required")

    # Embedding provider selection
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

    # Enhance chunking configuration for token-aware processing
    if enable_chunking_enhancement and emb_provider == "voyageai":
        schema = create_enhanced_chunking_config(
            schema,
            model_name=emb_model,
            max_tokens=max_tokens_per_chunk
        )

    # Save uploaded file temporarily
    temp_file_path = None
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)

        # Process file with streaming ingestion
        result = await ingest_json_file_streaming(
            file_path=temp_file_path,
            schema_config=schema,
            milvus_conf=rag["milvus"],
            emb_provider=emb_provider,
            emb_model=emb_model,
            provider_key=provider_key
        )

        return {"status": "ok", **result}

    finally:
        # Cleanup temporary file
        if temp_file_path and Path(temp_file_path).exists():
            Path(temp_file_path).unlink()


@router.post("/rag/analyze-file")
async def rag_analyze_file(
    x_tenant_id: str = Header(None),
    file: UploadFile = File(...)
):
    """
    Analyze JSON file to get statistics and estimates without processing.
    Useful for determining processing approach and time estimates.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    cfg = get_tenant_config(x_tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Tenant not found")

    rag = (cfg.get("rag") or {})
    if not rag.get("enabled"):
        raise HTTPException(status_code=400, detail="RAG not enabled for tenant")

    # Save file temporarily for analysis
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)

        # Get file statistics
        file_stats = await get_file_stats(temp_file_path)
        
        # Get processing estimates
        emb_provider = rag.get("embedding_provider", "sentence_transformers")
        time_estimates = estimate_processing_time(
            file_stats["file_size_bytes"],
            file_stats["estimated_items"],
            emb_provider
        )
        
        # Determine recommended processing approach
        size_mb = file_stats["file_size_bytes"] / (1024 * 1024)
        recommended_approach = "standard"
        
        if size_mb > 10:  # Files larger than 10MB
            recommended_approach = "streaming"
        elif file_stats["estimated_items"] > 1000:  # Many items
            recommended_approach = "streaming"
        
        # Determine if batching would be beneficial
        use_batching = emb_provider == "voyageai" and (
            file_stats["estimated_items"] > 100 or size_mb > 1
        )

        return {
            "status": "ok",
            "file_analysis": file_stats,
            "processing_estimates": time_estimates,
            "recommendations": {
                "approach": recommended_approach,
                "use_batching": use_batching,
                "enable_token_aware_chunking": emb_provider == "voyageai",
                "estimated_embedding_cost": {
                    "note": "Estimate based on file size and provider",
                    "provider": emb_provider,
                    "estimated_api_calls": max(1, file_stats["estimated_items"] // 100) if emb_provider != "sentence_transformers" else 0
                }
            }
        }

    finally:
        # Cleanup temporary file
        if temp_file_path and Path(temp_file_path).exists():
            Path(temp_file_path).unlink()


@router.get("/rag/processing-capabilities")
async def get_processing_capabilities(x_tenant_id: str = Header(None)):
    """
    Get information about available processing capabilities for this tenant.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    cfg = get_tenant_config(x_tenant_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Tenant not found")

    rag = (cfg.get("rag") or {})
    if not rag.get("enabled"):
        raise HTTPException(status_code=400, detail="RAG not enabled for tenant")

    # Get available providers and their capabilities
    provider_keys = rag.get("provider_keys", {})
    available_providers = ["sentence_transformers"]  # Always available
    
    if provider_keys.get("openai"):
        available_providers.append("openai")
    if provider_keys.get("voyageai"):
        available_providers.append("voyageai")
    
    capabilities = {
        "providers": available_providers,
        "features": {
            "streaming_processing": True,
            "token_aware_chunking": "voyageai" in available_providers,
            "intelligent_batching": "voyageai" in available_providers,
            "progress_tracking": True,
            "large_file_support": True,
            "compression_support": ["gzip"],
            "formats_supported": ["json_array", "ndjson"]
        },
        "limits": {
            "max_file_size_mb": 1000,  # Configurable limit
            "max_tokens_per_chunk": 2000,
            "max_chunks_per_batch": 950,  # VoyageAI safety margin
            "max_tokens_per_batch": 9500  # VoyageAI safety margin
        },
        "default_settings": {
            "embedding_provider": rag.get("embedding_provider", "sentence_transformers"),
            "embedding_model": rag.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
            "chunking_strategy": "token_aware" if "voyageai" in available_providers else "recursive",
            "max_tokens_per_chunk": 1000,
            "chunk_overlap_tokens": 100
        }
    }
    
    return {"status": "ok", "capabilities": capabilities}


@router.post("/rag/ingest-file-async")
async def rag_ingest_file_async(
    x_tenant_id: str = Header(None),
    file: UploadFile = File(...),
    schema_json: str = Form(...),
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    enable_chunking_enhancement: bool = Form(True),
    max_tokens_per_chunk: int = Form(1000)
):
    """
    Async file ingestion endpoint for large files with background processing.
    Returns a task ID for monitoring progress.
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

    # Validate schema configuration
    fmt = (schema.get("format") or "json_array").lower()
    if fmt not in ("json_array", "ndjson"):
        raise HTTPException(status_code=400, detail="schema_json.format must be 'json_array' or 'ndjson'")

    mapping = schema.get("mapping") or {}
    content_path = mapping.get("content_path")
    if not content_path:
        raise HTTPException(status_code=400, detail="schema_json.mapping.content_path is required")

    # Embedding provider selection
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

    # Enhance chunking configuration for token-aware processing
    if enable_chunking_enhancement and emb_provider == "voyageai":
        schema = create_enhanced_chunking_config(
            schema,
            model_name=emb_model,
            max_tokens=max_tokens_per_chunk
        )

    # Save uploaded file temporarily
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
            file_size = len(content)

        # Start background task
        task_manager = get_task_manager()
        task_id = await task_manager.start_task(
            tenant_id=x_tenant_id,
            file_path=temp_file_path,
            file_size=file_size,
            schema_config=schema,
            embedding_provider=emb_provider,
            embedding_model=emb_model,
            provider_key=provider_key
        )

        return {
            "status": "processing_started",
            "task_id": task_id,
            "message": "File processing started in background",
            "endpoints": {
                "status": f"/rag/task-status/{task_id}",
                "control": f"/rag/task-control/{task_id}"
            }
        }

    except Exception as e:
        # Cleanup temp file on error
        if temp_file_path and Path(temp_file_path).exists():
            Path(temp_file_path).unlink()
        raise HTTPException(status_code=500, detail=f"Failed to start background processing: {str(e)}")


@router.get("/rag/task-status/{task_id}")
async def get_task_status(task_id: str, x_tenant_id: str = Header(None)):
    """
    Get real-time processing status and progress for a task.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    task_manager = get_task_manager()
    progress_tracker = get_progress_tracker()
    
    # Get task info
    task_info = await task_manager.get_task_status(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify tenant access
    if task_info.tenant_id != x_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get detailed progress
    detailed_progress = await progress_tracker.get_detailed_progress(task_id)
    
    # Build response
    response = {
        "task_id": task_id,
        "status": task_info.status,
        "file_info": task_info.file_info,
        "configuration": {
            "embedding_provider": task_info.configuration.get("embedding_provider"),
            "embedding_model": task_info.configuration.get("embedding_model"),
            "schema_format": task_info.configuration.get("schema_config", {}).get("format")
        },
        "progress": {
            "items_processed": task_info.progress.items_processed,
            "items_total": task_info.progress.items_total,
            "percentage": task_info.progress.percentage,
            "chunks_processed": task_info.progress.chunks_processed,
            "embeddings_generated": task_info.progress.embeddings_generated,
            "current_phase": task_info.progress.current_phase,
            "error_count": task_info.progress.error_count
        },
        "timing": {
            "start_time": task_info.progress.start_time,
            "elapsed_time": task_info.progress.elapsed_time,
            "estimated_completion": task_info.progress.estimated_completion,
            "last_update": task_info.updated_at
        }
    }
    
    # Add detailed progress if available
    if detailed_progress:
        response["detailed_progress"] = detailed_progress
    
    # Add error info if task failed
    if task_info.status == TaskStatus.FAILED.value and task_info.error_info:
        response["error"] = task_info.error_info
    
    # Add results if completed
    if task_info.status == TaskStatus.COMPLETED.value:
        results = task_info.configuration.get("results", {})
        response["results"] = {
            "upserted_count": results.get("upserted", 0),
            "dimension": results.get("dim", 0),
            "statistics": results.get("statistics", {})
        }
    
    return response


@router.post("/rag/task-control/{task_id}")
async def control_task(
    task_id: str,
    action: str,
    x_tenant_id: str = Header(None)
):
    """
    Control task execution (pause, resume, cancel).
    
    Supported actions:
    - pause: Pause the running task
    - resume: Resume a paused task
    - cancel: Cancel the task completely
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    if action not in ["pause", "resume", "cancel"]:
        raise HTTPException(status_code=400, detail="Action must be 'pause', 'resume', or 'cancel'")
    
    task_manager = get_task_manager()
    
    # Verify task exists and tenant access
    task_info = await task_manager.get_task_status(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_info.tenant_id != x_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Execute action
    success = False
    message = ""
    
    if action == "pause":
        success = await task_manager.pause_task(task_id)
        message = "Task paused successfully" if success else "Failed to pause task"
    elif action == "resume":
        success = await task_manager.resume_task(task_id)
        message = "Task resumed successfully" if success else "Failed to resume task"
    elif action == "cancel":
        success = await task_manager.cancel_task(task_id)
        message = "Task cancelled successfully" if success else "Failed to cancel task"
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "status": "ok",
        "action": action,
        "task_id": task_id,
        "message": message
    }


@router.get("/rag/task-recovery/{task_id}")
async def get_task_recovery_info(task_id: str, x_tenant_id: str = Header(None)):
    """
    Get recovery information for a failed task.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    task_manager = get_task_manager()
    checkpoint_manager = get_checkpoint_manager()
    
    # Verify task exists and tenant access
    task_info = await task_manager.get_task_status(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task_info.tenant_id != x_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get recovery statistics
    recovery_stats = await checkpoint_manager.estimate_recovery_progress(task_id)
    
    return {
        "status": "ok",
        "task_id": task_id,
        "task_status": task_info.status,
        "recovery_info": recovery_stats
    }


@router.get("/rag/active-tasks")
async def get_active_tasks(x_tenant_id: str = Header(None)):
    """
    Get list of active tasks for the tenant.
    """
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    task_manager = get_task_manager()
    active_task_ids = await task_manager.get_active_tasks()
    
    # Filter by tenant and get task info
    tenant_tasks = []
    for task_id in active_task_ids:
        task_info = await task_manager.get_task_status(task_id)
        if task_info and task_info.tenant_id == x_tenant_id:
            tenant_tasks.append({
                "task_id": task_id,
                "status": task_info.status,
                "file_name": task_info.file_info.get("filename", "unknown"),
                "file_size": task_info.file_info.get("file_size", 0),
                "items_processed": task_info.progress.items_processed,
                "items_total": task_info.progress.items_total,
                "current_phase": task_info.progress.current_phase,
                "start_time": task_info.progress.start_time,
                "elapsed_time": task_info.progress.elapsed_time
            })
    
    return {
        "status": "ok",
        "active_tasks": tenant_tasks,
        "total_count": len(tenant_tasks)
    }