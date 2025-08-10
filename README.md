# WebAI Backend (FastAPI)

Multi-tenant FastAPI backend for the WebAI project, supporting:
- Per-tenant configuration, origin validation, and rate limiting
- Chat completions over SSE via OpenRouter
- Self-RAG with Milvus/Zilliz vector store
- Pluggable embeddings: Sentence-Transformers, OpenAI, VoyageAI
- Ingestion API for JSON and file uploads (JSON array or NDJSON) with schema-driven mapping and metadata

This repo is production-ready for Google Cloud Run.

## Contents
- Dockerfile and .dockerignore
- FastAPI app under `app/` with modular routes/services
- SSE streaming chat endpoint
- RAG ingestion endpoints (/rag/ingest, /rag/ingest-file)

## Requirements
- Python 3.11 (built into container)
- Redis for tenant and optional conversation storage
- Milvus or Zilliz Cloud for vector storage (when RAG enabled)

## Environment Variables
Set these in Cloud Run (or locally):
- REDIS_URL: redis://host:port
- CONVERSATION_REDIS_URL: redis://host:port (optional)
- WEBAI_ADMIN_KEY: secure admin key for tenant management
- RATE_LIMIT_PER_MINUTE: default per-tenant minute limit
- RATE_LIMIT_PER_HOUR: default per-tenant hour limit
- OPENROUTER_HTTP_REFERER: your site URL for OpenRouter attribution (e.g., https://web3ai.vercel.app)
- OPENROUTER_X_TITLE: human-readable app name (e.g., “Web3AI Assistant”)

These two are forwarded as headers to OpenRouter on each request (optional but recommended).

Docker (Local)

# Build
docker build -t webai-backend:latest .

# Run
docker run --rm -p 8080:8080 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e WEBAI_ADMIN_KEY=your-admin-key \
  -e OPENROUTER_HTTP_REFERER=https://web3ai.vercel.app \
  -e OPENROUTER_X_TITLE="Web3AI Assistant" \
  webai-backend:latest

Build and Deploy to Cloud Run

gcloud builds submit --tag gcr.io/PROJECT_ID/webai-backend:latest

gcloud run deploy webai-backend \
  --image gcr.io/PROJECT_ID/webai-backend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars REDIS_URL=redis://HOST:6379 \
  --set-env-vars CONVERSATION_REDIS_URL=redis://HOST:6380 \
  --set-env-vars WEBAI_ADMIN_KEY=your-secure-admin-key \
  --set-env-vars RATE_LIMIT_PER_MINUTE=30 \
  --set-env-vars RATE_LIMIT_PER_HOUR=1000 \
  --set-env-vars OPENROUTER_HTTP_REFERER=https://your-website.com \
  --set-env-vars OPENROUTER_X_TITLE="Web3AI Assistant"

## **API Quick Start**

### **1) Register a Tenant (with RAG)**

Voyage embeddings + Zilliz example:

curl -X POST https://YOUR-CLOUD-RUN-URL/register-tenant \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR-ADMIN-KEY" \
  -d '{
    "openrouter_api_key": "YOUR_OPENROUTER_KEY",
    "system_prompt": "You are a helpful AI assistant for Example Inc.",
    "allowed_domains": ["web3ai.vercel.app", "*.vercel.app", "localhost:3000"],
    "model": "anthropic/claude-3.5-sonnet",
    "rate_limit_per_minute": 30,
    "rate_limit_per_hour": 1000,
    "rag": {
      "enabled": true,
      "self_rag_enabled": true,
      "provider": "milvus",
      "top_k": 4,
      "embedding_provider": "voyageai",
      "embedding_model": "voyage-3-lite",
      "provider_keys": { "voyageai": "VX_YOUR_VOYAGE_API_KEY" },
      "milvus": {
        "uri": "https://in03-xxxx.zillizcloud.com",
        "token": "YOUR_ZILLIZ_TOKEN",
        "db_name": "_default",
        "collection": "website_chunks",
        "vector_field": "embedding",
        "text_field": "text",
        "metadata_field": "metadata",
        "metric_type": "IP"
      }
    }
  }'

  OpenAI embeddings example:

  curl -X POST https://YOUR-CLOUD-RUN-URL/register-tenant \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR-ADMIN-KEY" \
  -d '{
    "openrouter_api_key": "YOUR_OPENROUTER_KEY",
    "system_prompt": "You are a helpful AI assistant.",
    "allowed_domains": ["web3ai.vercel.app"],
    "model": "openai/gpt-4o-mini",
    "rag": {
      "enabled": true,
      "self_rag_enabled": true,
      "provider": "milvus",
      "top_k": 5,
      "embedding_provider": "openai",
      "embedding_model": "text-embedding-3-small",
      "provider_keys": { "openai": "sk-your-openai-key" },
      "milvus": {
        "uri": "http://milvus:19530",
        "db_name": "_default",
        "collection": "website_chunks",
        "vector_field": "embedding",
        "text_field": "text",
        "metadata_field": "metadata",
        "metric_type": "COSINE"
      }
    }
  }'

2) Ingest Content (JSON array) via Body

curl -X POST https://YOUR-CLOUD-RUN-URL/rag/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: TENANT_ID_FROM_REGISTRATION" \
  -d '{
    "embedding_provider": "voyageai",
    "embedding_model": "voyage-3-lite",
    "documents": [
      { "text": "Welcome to Example Inc...", "metadata": {"url":"https://example.com/"} },
      { "text": "Pricing details...", "metadata": {"url":"https://example.com/pricing"} }
    ]
  }'

3) Ingest File (JSON array or NDJSON) with Schema Mapping

Supports .json, .ndjson, and gzipped (.gz) variants. You define:

format: json_array | ndjson
validation_schema: optional JSON Schema for robust validation
mapping: content_path and metadata_paths
chunking: simple char-based chunking

curl -X POST https://YOUR-CLOUD-RUN-URL/rag/ingest-file \
  -H "X-Tenant-ID: TENANT_ID_FROM_REGISTRATION" \
  -H "Accept: application/json" \
  -F "file=@/path/site_content.ndjson.gz;type=application/gzip" \
  -F 'schema_json={
    "format": "ndjson",
    "validation_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "required": ["data"],
      "properties": {
        "data": {
          "type": "object",
          "required": ["body", "url"],
          "properties": {
            "body": { "type": "string", "minLength": 1 },
            "url": { "type": "string" },
            "title": { "type": "string" }
          }
        }
      }
    },
    "mapping": {
      "content_path": "data.body",
      "metadata_paths": { "url": "data.url", "title": "data.title" }
    },
    "chunking": { "strategy": "recursive", "max_chars": 1200, "overlap": 150 }
  }' \
  -F "embedding_provider=openai" \
  -F "embedding_model=text-embedding-3-small"

4) Chat (SSE)

Per-request overrides for Self-RAG usage and top_k are supported by the backend:

curl -N -X POST https://YOUR-CLOUD-RUN-URL/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: TENANT_ID_FROM_REGISTRATION" \
  -d '{
    "message": "What are your pricing tiers?",
    "session_id": "session_123",
    "use_redis_conversations": true,
    "use_rag": true,
    "rag_top_k": 4
  }'


HEALTH CHECK

curl https://YOUR-CLOUD-RUN-URL/health

Security Notes

Keep WEBAI_ADMIN_KEY secret and rotate regularly.
For embedding providers, store provider keys inside tenant config via the admin endpoints, or back them with Secret Manager if needed.
Origin allowlist is enforced per tenant; ensure your site (e.g., web3ai.vercel.app) is added.

Dockerfile Best Practices Used:

Layer ordering to leverage cache: install dependencies before copying source, reducing rebuild time when code changes (testdriven.io).

Minimal base image and only essential OS packages, keeping image small (docs.docker.com).

.dockerignore to shrink build context and speed up builds (docs.docker.com).

Simple, production-appropriate CMD with Uvicorn; additional hardening/tuning can follow general guides (dev.to, github.com).
Troubleshooting

Cloud Build Dockerfile parser errors: 

avoid BuildKit-only features (e.g., heredocs) in Dockerfile to ensure compatibility with classic Docker builder in Cloud Build.

Large image size: remove the model pre-download step or switch to a smaller embedding model.

SSE timeouts: ensure Cloud Run request timeout is sufficient and clients properly parse data: lines.

Happy building!