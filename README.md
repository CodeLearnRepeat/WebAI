# WebAI Backend (FastAPI)

A sophisticated multi-tenant FastAPI backend for the WebAI project with comprehensive RAG (Retrieval Augmented Generation) capabilities, featuring advanced streaming processing, intelligent batching, and enterprise-grade reliability.

## 🏗️ Architecture Overview

The WebAI backend is built with a modern, scalable architecture:

- **Multi-tenant RAG Implementation** - Isolated configurations per tenant with custom embeddings and vector stores
- **Self-RAG Pipeline** - 6-step processing with retrieval, relevance checking, and response generation
- **Memory-Efficient Streaming** - Process large JSON files without memory overflow using ijson streaming
- **Intelligent Batching** - VoyageAI-optimized batching system respecting token and chunk limits
- **Vector Store Integration** - Milvus/Zilliz Cloud support with configurable metrics and collections
- **External API Integrations** - OpenRouter for LLMs, VoyageAI for embeddings,
- **Redis Infrastructure** - Caching, rate limiting, conversation storage, and task management
- **Comprehensive Testing** - Full test suite covering performance, recovery, and integration scenarios
- **Docker Containerization** - Production-ready containers optimized for Google Cloud Run

## 📋 Backend Prerequisites & Dependencies

### System Requirements
- **Python 3.11+** (built into container)
- **Redis** for caching, rate limiting, and conversation storage
- **Milvus or Zilliz Cloud** for vector storage (when RAG enabled)
- **Docker** (optional, for containerized deployment)

### Core Dependencies

Based on [`backend/requirements.txt`](backend/requirements.txt):

```txt
# Web Framework & Server
fastapi                 # Modern async web framework
uvicorn[standard]       # ASGI server with performance optimizations

# HTTP & Networking
httpx                   # Async HTTP client for external APIs

# Data Validation & Serialization
pydantic<2              # Data validation and settings management

# Database & Caching
redis                   # Redis client for caching and rate limiting
pymilvus>=2.4.4        # Milvus vector database client

# ML & Embeddings
sentence-transformers>=3.0.0  # Local sentence embeddings
numpy                          # Numerical computations

# External API Clients
voyageai>=0.2.3        # VoyageAI embeddings client

# JSON Processing & Validation
jsonschema>=4.22.0     # JSON schema validation
ijson>=3.2.0           # Streaming JSON parser for large files

# File Handling & Utilities
python-multipart       # Form data handling for file uploads
tiktoken>=0.5.0        # Token counting for various models
aiofiles>=23.0.0       # Async file operations
```

### Optional Dependencies for Development
```bash
# Testing & Development
pytest>=7.0.0
pytest-asyncio
httpx[test]
pytest-cov

# Code Quality
black
flake8
mypy
```

## ⚙️ Environment Configuration

### Required Environment Variables

The backend uses the following environment variables defined in [`backend/app/core/config.py`](backend/app/core/config.py):

#### Redis Configuration
```bash
# Primary Redis instance for tenant storage and rate limiting
REDIS_URL="redis://localhost:6379"

# Optional: Separate Redis instance for conversation storage
CONVERSATION_REDIS_URL="redis://localhost:6380"  # Optional
```

#### Administrative Access
```bash
# Secure admin key for tenant management operations
WEBAI_ADMIN_KEY="your-secure-admin-key-here"
```

#### Rate Limiting Defaults
```bash
# Default rate limits (can be overridden per tenant)
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=1000
```

#### OpenRouter Integration
```bash
# Optional: Attribution headers sent to OpenRouter
OPENROUTER_HTTP_REFERER="https://your-website.com"
OPENROUTER_X_TITLE="Your App Name"
```

### Environment Variables Examples

#### Local Development (.env)
```bash
REDIS_URL=redis://localhost:6379
CONVERSATION_REDIS_URL=redis://localhost:6380
WEBAI_ADMIN_KEY=dev-admin-key-12345
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000
OPENROUTER_HTTP_REFERER=http://localhost:3000
OPENROUTER_X_TITLE="WebAI Local Dev"
```

#### Production (.env.production)
```bash
REDIS_URL=redis://your-redis-host:6379
CONVERSATION_REDIS_URL=redis://your-redis-host:6380
WEBAI_ADMIN_KEY=super-secure-production-key
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=1000
OPENROUTER_HTTP_REFERER=https://your-production-site.com
OPENROUTER_X_TITLE="Your Production App"
```

## 🚀 Local Development Setup

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd webai-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit with your configuration
nano backend/.env
```

### 3. Start Development Server
```bash
# Navigate to backend directory
cd backend

# Start FastAPI development server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at:
- **API Base**: http://localhost:8080
- **Interactive Docs**: http://localhost:8080/docs
- **OpenAPI Schema**: http://localhost:8080/openapi.json

### 4. Verify Installation
```bash
# Test health endpoint
curl http://localhost:8080/health

# Expected response:
# {"status":"healthy","redis_config":true,"redis_conversations":false}
```

## 🗄️ Database Setup

### Redis Setup

#### Local Redis Installation
```bash
# macOS (using Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Docker (alternative)
docker run --name redis-webai -p 6379:6379 -d redis:7-alpine
```

#### Redis Configuration
```bash
# Test Redis connection
redis-cli ping
# Expected: PONG

# Optional: Set up conversation Redis on different port
redis-server --port 6380 --daemonize yes
```

### Milvus/Zilliz Setup

#### Option 1: Zilliz Cloud (Recommended for Production)
1. **Sign up** at [Zilliz Cloud](https://cloud.zilliz.com)
2. **Create a cluster** with your preferred region
3. **Note the connection details**:
   ```bash
   URI: https://in03-xxxx.zillizcloud.com
   Token: your-cluster-token
   ```

#### Option 2: Local Milvus (Development)
```bash
# Using Docker Compose
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
bash standalone_embed.sh start

# Or using Docker directly
docker run -d \
  --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  -v $(pwd)/volumes/milvus:/var/lib/milvus \
  milvusdb/milvus:latest
```

#### Option 3: Milvus Lite (Lightweight)
```bash
# Install Milvus Lite for development
pip install milvus[lite]

# No additional setup required - embedded database
```

### Database Verification
```bash
# Test Milvus connection (adjust URI as needed)
python -c "
from pymilvus import connections
connections.connect('default', host='localhost', port='19530')
print('✅ Milvus connection successful')
"
```

## 🐳 Docker Deployment

### Local Docker Build
```bash
# Build the Docker image
docker build -t webai-backend:latest ./backend

# Run locally with environment variables
docker run --rm -p 8080:8080 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e WEBAI_ADMIN_KEY=your-admin-key \
  -e OPENROUTER_HTTP_REFERER=https://your-site.com \
  -e OPENROUTER_X_TITLE="Your App Name" \
  webai-backend:latest
```

### Google Cloud Run Deployment
```bash
# Build and submit to Google Cloud Build
gcloud builds submit --tag gcr.io/PROJECT_ID/webai-backend:latest ./backend

# Deploy to Cloud Run
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
  --set-env-vars OPENROUTER_X_TITLE="Your App Name"
```

## 📡 API Documentation

### Core Endpoints

#### Health Check
```bash
GET /health
```
**Description**: Check backend health and Redis connectivity
**Response**:
```json
{
  "status": "healthy",
  "redis_config": true,
  "redis_conversations": false
}
```

#### Tenant Management

##### Register Tenant
```bash
POST /register-tenant
Headers: X-Admin-Key: YOUR-ADMIN-KEY
Content-Type: application/json
```

**VoyageAI + Zilliz Example**:
```bash
curl -X POST https://YOUR-API-URL/register-tenant \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR-ADMIN-KEY" \
  -d '{
    "openrouter_api_key": "sk-or-your-key",
    "system_prompt": "You are a helpful AI assistant for Example Inc.",
    "allowed_domains": ["your-domain.com", "*.vercel.app", "localhost:3000"],
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
      "provider_keys": { "voyageai": "pa-your-voyage-key" },
      "milvus": {
        "uri": "https://in03-xxxx.zillizcloud.com",
        "token": "your-zilliz-token",
        "db_name": "_default",
        "collection": "website_chunks",
        "vector_field": "embedding",
        "text_field": "text",
        "metadata_field": "metadata",
        "metric_type": "IP"
      }
    }
  }'
```

**OpenAI + Local Milvus Example**:
```bash
curl -X POST https://YOUR-API-URL/register-tenant \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR-ADMIN-KEY" \
  -d '{
    "openrouter_api_key": "sk-or-your-key",
    "system_prompt": "You are a helpful AI assistant.",
    "allowed_domains": ["your-domain.com"],
    "model": "openai/gpt-4o-mini",
    "rag": {
      "enabled": true,
      "self_rag_enabled": true,
      "provider": "milvus",
      "top_k": 5,
      "embedding_provider": "voyageai",
      "embedding_model": "text-embedding-3-small",
      "provider_keys": { "voyageai": "your-voyage-api-key" },
      "milvus": {
        "uri": "http://localhost:19530",
        "db_name": "_default",
        "collection": "website_chunks",
        "vector_field": "embedding",
        "text_field": "text",
        "metadata_field": "metadata",
        "metric_type": "COSINE"
      }
    }
  }'
```

##### Update Tenant
```bash
PUT /update-tenant/{tenant_id}
Headers: X-Admin-Key: YOUR-ADMIN-KEY
```

#### RAG Ingestion Endpoints

##### Simple Document Ingestion
```bash
POST /rag/ingest
Headers: X-Tenant-ID: TENANT_ID
Content-Type: application/json
```

**Example**:
```bash
curl -X POST https://YOUR-API-URL/rag/ingest \
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
```

##### File Upload Ingestion
```bash
POST /rag/ingest-file
Headers: X-Tenant-ID: TENANT_ID
Content-Type: multipart/form-data
```

**Example with Schema Mapping**:
```bash
curl -X POST https://YOUR-API-URL/rag/ingest-file \
  -H "X-Tenant-ID: TENANT_ID" \
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
  -F "embedding_provider=voyageai" \
  -F "embedding_model=voyage-3-lite"
```

##### Streaming File Ingestion (Large Files)
```bash
POST /rag/ingest-file-streaming
Headers: X-Tenant-ID: TENANT_ID
```

**Features**:
- Memory-efficient processing for files up to 1GB+
- Token-aware chunking for VoyageAI optimization
- Real-time progress tracking
- Intelligent batching with safety margins

##### Async File Processing
```bash
POST /rag/ingest-file-async
Headers: X-Tenant-ID: TENANT_ID
```

**Response**:
```json
{
  "status": "processing_started",
  "task_id": "task_abc123",
  "message": "File processing started in background",
  "endpoints": {
    "status": "/rag/task-status/task_abc123",
    "control": "/rag/task-control/task_abc123"
  }
}
```

##### File Analysis
```bash
POST /rag/analyze-file
Headers: X-Tenant-ID: TENANT_ID
```

**Purpose**: Analyze files before processing to get size estimates and recommendations.

##### Task Management
```bash
# Get task status
GET /rag/task-status/{task_id}
Headers: X-Tenant-ID: TENANT_ID

# Control task (pause/resume/cancel)
POST /rag/task-control/{task_id}
Headers: X-Tenant-ID: TENANT_ID
Body: {"action": "pause|resume|cancel"}

# Get active tasks
GET /rag/active-tasks
Headers: X-Tenant-ID: TENANT_ID
```

#### Chat Endpoints

##### Streaming Chat
```bash
POST /chat/stream
Headers: X-Tenant-ID: TENANT_ID
Content-Type: application/json
```

**Example with RAG**:
```bash
curl -N -X POST https://YOUR-API-URL/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: TENANT_ID" \
  -d '{
    "message": "What are your pricing tiers?",
    "session_id": "session_123",
    "use_redis_conversations": true,
    "use_rag": true,
    "rag_top_k": 4
  }'
```

**Response**: Server-Sent Events (SSE) stream with OpenAI-compatible format.

## 🧪 Backend Testing

### Comprehensive Test Suite

The backend includes a sophisticated testing framework covering all aspects of the system:

#### Test Categories

1. **Core Integration Tests** ([`backend/test_core_integration.py`](backend/test_core_integration.py))
   - Token counting and batch management
   - JSON parsing and chunking
   - End-to-end workflow validation

2. **Large File Processing** ([`backend/test_large_file_processing.py`](backend/test_large_file_processing.py))
   - Multi-format file support (JSON array, NDJSON, compressed)
   - Memory usage validation
   - Performance benchmarking

3. **Batching Validation** ([`backend/test_batching_validation.py`](backend/test_batching_validation.py))
   - VoyageAI token limit compliance
   - Chunk size optimization
   - Safety margin verification

4. **Recovery & Error Handling** ([`backend/test_recovery_error_handling.py`](backend/test_recovery_error_handling.py))
   - Checkpoint system validation
   - Error recovery mechanisms
   - Data integrity verification

5. **Performance & Scale** ([`backend/test_performance_scale.py`](backend/test_performance_scale.py))
   - Memory efficiency analysis
   - Processing speed benchmarks
   - Scalability validation

6. **API Endpoints** ([`backend/test_api_endpoints.py`](backend/test_api_endpoints.py))
   - All endpoint functionality
   - Task management workflows
   - Error condition handling

### Running Tests

#### Individual Test Modules
```bash
cd backend

# Core integration tests
python test_core_integration.py

# Large file processing tests
python test_large_file_processing.py

# API endpoint tests
python test_api_endpoints.py
```

#### Comprehensive Test Suite
```bash
cd backend

# Run all tests with detailed reporting
python run_comprehensive_tests.py
```

**Features**:
- Automatic test execution across all modules
- Detailed performance metrics
- Critical validation checklist
- Final assessment and recommendations
- JSON report generation

#### Expected Test Output
```
📊 TEST EXECUTION SUMMARY:
   Total Modules: 6
   Passed: 6
   Failed: 0
   Success Rate: 100.0%
   Total Time: 45.2s

🎯 ORIGINAL PROBLEM VALIDATION:
   voyageai_token_limit_respected: ✅ SOLVED
   large_files_processed_successfully: ✅ SOLVED
   memory_usage_bounded: ✅ SOLVED
   processing_scalable: ✅ SOLVED

🟢 OVERALL RESULT: COMPREHENSIVE SUCCESS
   The VoyageAI batching system solution is validated and ready for production!
```

### Test Configuration

#### Environment Setup for Testing
```bash
# Set up test environment variables
export REDIS_URL=redis://localhost:6379
export WEBAI_ADMIN_KEY=test-admin-key
export TEST_MODE=true

# Optional: Use separate Redis instance for testing
export CONVERSATION_REDIS_URL=redis://localhost:6380
```

#### Mock External Services
The test suite includes comprehensive mocking for:
- VoyageAI API calls
- OpenRouter API interactions
- Milvus/Zilliz operations
- Redis operations (when needed)

## 🔧 Advanced Configuration

### Self-RAG Pipeline Configuration

The Self-RAG system supports advanced configuration options:

```json
{
  "rag": {
    "enabled": true,
    "self_rag_enabled": true,
    "provider": "milvus",
    "top_k": 4,
    "embedding_provider": "voyageai",
    "embedding_model": "voyage-3-lite",
    "retrieval_confidence_threshold": 0.7,
    "relevance_check_enabled": true,
    "response_quality_threshold": 0.8,
    "fallback_to_llm": true
  }
}
```

### Embedding Provider Configuration

#### VoyageAI (Recommended for Production)
```json
{
  "embedding_provider": "voyageai",
  "embedding_model": "voyage-3-lite",
  "provider_keys": {
    "voyageai": "pa-your-api-key"
  }
}
```

**Supported Models**:
- `voyage-3-lite` (1536 dimensions, cost-effective)
- `voyage-3` (1024 dimensions, high quality)
- `voyage-large-2-instruct` (16k context, specialized)


```

#### Sentence Transformers (Local, No API Key Required)
```json
{
  "embedding_provider": "sentence_transformers",
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
}
```

### Advanced Chunking Strategies

#### Token-Aware Chunking (VoyageAI Optimized)
```json
{
  "chunking": {
    "strategy": "token_aware",
    "max_tokens": 1000,
    "overlap_tokens": 100,
    "respect_sentence_boundaries": true,
    "min_chunk_tokens": 50
  }
}
```

#### Recursive Character Chunking
```json
{
  "chunking": {
    "strategy": "recursive",
    "max_chars": 1200,
    "overlap": 150,
    "separators": ["\n\n", "\n", ". ", " "]
  }
}
```

### Performance Tuning

#### Batch Configuration
```json
{
  "batching": {
    "max_chunks_per_batch": 950,
    "max_tokens_per_batch": 9500,
    "safety_margin": 0.05,
    "adaptive_sizing": true
  }
}
```

#### Memory Management
```json
{
  "memory": {
    "streaming_threshold_mb": 10,
    "max_file_size_mb": 1000,
    "checkpoint_interval": 1000,
    "cleanup_temp_files": true
  }
}
```

## 🔒 Security & Best Practices

### API Key Management
- Store API keys securely in tenant configurations
- Use environment variables for admin keys
- Rotate keys regularly
- Consider using Google Secret Manager for production

### Rate Limiting
- Per-tenant rate limits enforced
- Configurable per-minute and per-hour limits
- Redis-based distributed rate limiting
- Automatic rate limit headers in responses

### Origin Validation
- Strict origin checking per tenant
- Support for wildcard domains (*.example.com)
- CORS handling for web clients
- Referrer validation for additional security

### Data Privacy
- No persistent storage of user conversations (optional Redis)
- Tenant data isolation
- Configurable data retention policies
- GDPR compliance considerations

## 🚨 Troubleshooting

### Common Issues

#### Redis Connection Issues
```bash
# Check Redis connectivity
redis-cli ping

# Common solutions:
# 1. Start Redis service
brew services start redis  # macOS
sudo systemctl start redis  # Linux

# 2. Check Redis configuration
redis-cli config get bind
redis-cli config get port
```

#### Milvus Connection Issues
```bash
# Check Milvus status
docker ps | grep milvus

# Restart Milvus
docker restart milvus

# Check logs
docker logs milvus
```

#### Large File Processing Issues
- **Memory Issues**: Use streaming endpoints for files >10MB
- **Timeout Issues**: Use async processing for large files
- **Token Limit Issues**: Enable intelligent batching for VoyageAI

#### API Limit Violations
- **VoyageAI**: System automatically respects 1000 chunk and 10k token limits
- **OpenRouter**: Configure appropriate rate limits per tenant
- **OpenAI**: Monitor usage through OpenAI dashboard

### Debug Mode
```bash
# Enable debug logging
uvicorn app.main:app --log-level debug

# Environment variable for additional debugging
export DEBUG=true
```

### Health Checks
```bash
# Basic health check
curl http://localhost:8080/health

# Check specific components
curl http://localhost:8080/debug/redis-status
curl http://localhost:8080/debug/milvus-status
```

## 📈 Monitoring & Observability

### Metrics Endpoints
- `/health` - Basic health status
- `/metrics` - Prometheus metrics (if enabled)
- `/debug/*` - Debug information endpoints

### Logging
- Structured JSON logging in production
- Request/response logging with correlation IDs
- Performance metrics for embedding operations
- Error tracking with full stack traces

### Performance Monitoring
- Request latency tracking
- Memory usage monitoring
- Redis connection pool metrics
- Milvus operation timing

This comprehensive backend setup provides enterprise-grade RAG capabilities with advanced streaming processing, intelligent batching, and robust error handling. The system is designed to handle production workloads while maintaining high performance and reliability.

---

# WebAI Frontend (Next.js)

A sophisticated Next.js frontend application providing chat interface, tenant setup wizard, and iframe widget capabilities for seamless integration with the WebAI FastAPI backend.

## 🏗️ Frontend Architecture Overview

The WebAI frontend is built with modern React and Next.js technologies:

- **Next.js 13.4** with Pages Router for optimal compatibility and performance
- **TypeScript Integration** for type safety and enhanced developer experience
- **Real-time Chat Interface** with streaming responses and markdown support
- **5-Step Setup Wizard** for comprehensive tenant configuration
- **Iframe Widget System** for embeddable chat deployment
- **WebAI API Client** with streaming, file processing, and tenant management
- **Responsive Design** optimized for desktop and mobile devices
- **Component Architecture** with modular, reusable UI components

## 📋 Frontend Prerequisites & Dependencies

### System Requirements
- **Node.js 18.0+** (specified in [`frontend-chatgpt-iframe/chatgpt-next-web-webai/package.json`](frontend-chatgpt-iframe/chatgpt-next-web-webai/package.json))
- **npm or yarn** for package management
- **Modern Browser** with ES2020+ support

### Core Dependencies

Based on [`frontend-chatgpt-iframe/chatgpt-next-web-webai/package.json`](frontend-chatgpt-iframe/chatgpt-next-web-webai/package.json):

#### Framework & Core
```json
{
  "next": "^13.4.19",
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "@next/font": "^13.4.19"
}
```

#### TypeScript & Development
```json
{
  "typescript": "^5.2.2",
  "@types/node": "^20.5.7",
  "@types/react": "^18.2.21",
  "@types/react-dom": "^18.2.7"
}
```

#### UI & Styling
```json
{
  "tailwindcss": "^3.3.3",
  "sass": "^1.66.1",
  "autoprefixer": "^10.4.15",
  "postcss": "^8.4.28"
}
```

#### Content Processing & Rendering
```json
{
  "react-markdown": "^8.0.7",
  "remark-gfm": "^3.0.1",
  "remark-math": "^5.1.1",
  "rehype-katex": "^6.0.3",
  "rehype-highlight": "^6.0.0",
  "katex": "^0.16.8",
  "mermaid": "^10.4.0",
  "prismjs": "^1.29.0",
  "marked": "^5.1.1",
  "dompurify": "^3.0.5"
}
```

#### State Management & Utilities
```json
{
  "zustand": "^4.4.1",
  "use-debounce": "^9.0.4",
  "nanoid": "^4.0.2"
}
```

#### Analytics & Monitoring
```json
{
  "@vercel/analytics": "^1.0.2"
}
```

## ⚙️ Frontend Environment Configuration

### Environment Variables

The frontend uses environment variables defined in [`frontend-chatgpt-iframe/chatgpt-next-web-webai/.env.local`](frontend-chatgpt-iframe/chatgpt-next-web-webai/.env.local):

#### WebAI Backend Integration
```bash
# Required: WebAI FastAPI backend URL
NEXT_PUBLIC_WEBAI_API_URL=https://web3ai-backend-v34-api-180395924844.us-central1.run.app

# Optional: Debug mode for development
NEXT_PUBLIC_WEBAI_DEBUG=false
```

#### Application Configuration
```bash
# App branding and metadata
NEXT_PUBLIC_APP_NAME="WebAI Chat"
NEXT_PUBLIC_APP_DESCRIPTION="AI Chat Assistant powered by WebAI"

# Development environment
NODE_ENV=development
```

### Environment Examples

#### Local Development (.env.local)
```bash
NEXT_PUBLIC_WEBAI_API_URL=http://localhost:8080
NEXT_PUBLIC_WEBAI_DEBUG=true
NEXT_PUBLIC_APP_NAME="WebAI Chat - Dev"
NEXT_PUBLIC_APP_DESCRIPTION="AI Chat Assistant powered by WebAI"
NODE_ENV=development
```

#### Production (.env.production)
```bash
NEXT_PUBLIC_WEBAI_API_URL=https://your-webai-backend.run.app
NEXT_PUBLIC_WEBAI_DEBUG=false
NEXT_PUBLIC_APP_NAME="WebAI Chat"
NEXT_PUBLIC_APP_DESCRIPTION="AI Chat Assistant powered by WebAI"
NODE_ENV=production
```

#### Staging (.env.staging)
```bash
NEXT_PUBLIC_WEBAI_API_URL=https://staging-webai-backend.run.app
NEXT_PUBLIC_WEBAI_DEBUG=true
NEXT_PUBLIC_APP_NAME="WebAI Chat - Staging"
NEXT_PUBLIC_APP_DESCRIPTION="AI Chat Assistant powered by WebAI"
NODE_ENV=staging
```

## 🚀 Frontend Installation & Setup

### 1. Navigate to Frontend Directory
```bash
# Navigate to the frontend application
cd frontend-chatgpt-iframe/chatgpt-next-web-webai
```

### 2. Install Dependencies
```bash
# Install all dependencies
npm install

# Or with yarn
yarn install

# Or with pnpm (faster)
pnpm install
```

### 3. Environment Configuration
```bash
# Copy environment template (if exists)
cp .env.example .env.local

# Or create new environment file
touch .env.local
```

Edit `.env.local` with your configuration:
```bash
NEXT_PUBLIC_WEBAI_API_URL=http://localhost:8080
NEXT_PUBLIC_WEBAI_DEBUG=true
NEXT_PUBLIC_APP_NAME="WebAI Chat - Local"
```

### 4. Start Development Server
```bash
# Start Next.js development server
npm run dev

# Or with yarn
yarn dev

# Or with pnpm
pnpm dev
```

The frontend will be available at:
- **Main Application**: http://localhost:3000
- **Embedded Chat**: http://localhost:3000/embedded/chat?embedded=true&tenant=demo&session=demo
- **Setup Wizard**: http://localhost:3000/setup

### 5. Verify Installation
```bash
# Check application health
curl http://localhost:3000

# Test embedded chat endpoint
curl http://localhost:3000/embedded/chat
```

## 🏛️ Frontend Component Architecture

### Core Pages Structure

#### Root Pages
- [`pages/index.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/index.tsx) - Landing page with iframe detection
- [`pages/_app.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/_app.tsx) - Next.js app wrapper
- [`pages/_document.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/_document.tsx) - HTML document structure

#### Embedded Chat System
- [`pages/embedded/chat.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/embedded/chat.tsx) - Main iframe chat interface
  - **Streaming Chat**: Real-time message streaming
  - **WebAI Integration**: Direct backend communication
  - **Responsive Design**: Mobile and desktop optimized
  - **Event Handling**: Parent-child iframe communication

#### Setup Wizard Pages
- [`pages/setup/index.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/setup/index.tsx) - Setup entry point
- [`pages/setup/step1.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/setup/step1.tsx) - Welcome and introduction
- [`pages/setup/step2.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/setup/step2.tsx) - Tenant registration
- [`pages/setup/step3.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/setup/step3.tsx) - System capabilities review
- [`pages/setup/step4.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/setup/step4.tsx) - File analysis and upload
- [`pages/setup/step5.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/pages/setup/step5.tsx) - Processing configuration

### Component Library

#### Core Components
- [`components/ChatHeader.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/components/ChatHeader.tsx) - Chat interface header
- [`components/ChatInput.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/components/ChatInput.tsx) - Message input field
- [`components/ChatMessages.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/components/ChatMessages.tsx) - Message display area
- [`components/LoadingSpinner.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/components/LoadingSpinner.tsx) - Loading indicators
- [`components/ErrorMessage.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/components/ErrorMessage.tsx) - Error handling display

#### Setup Wizard Components
- [`components/setup/WizardLayout.tsx`](frontend-chatgpt-iframe/chatgpt-next-web-webai/components/setup/WizardLayout.tsx) - Setup wizard shell
  - **Progress Tracking**: Visual step progression
  - **Navigation**: Previous/Next/Cancel controls
  - **Responsive Design**: Mobile-optimized layout
  - **State Management**: Step completion tracking

### API Integration Layer

#### WebAI API Client
[`lib/webai-api.ts`](frontend-chatgpt-iframe/chatgpt-next-web-webai/lib/webai-api.ts) provides comprehensive backend integration:

**Core Features**:
- **Streaming Chat**: `WebAIApi.chat()` for real-time messaging
- **Tenant Management**: Registration, configuration, validation
- **File Processing**: Upload, analysis, streaming ingestion
- **Connection Management**: Health checks, error handling
- **Configuration**: Dynamic tenant settings

**Usage Example**:
```typescript
import { WebAIApi } from '@/lib/webai-api';

const api = new WebAIApi({
  apiUrl: process.env.NEXT_PUBLIC_WEBAI_API_URL,
  tenantId: 'your-tenant-id',
  sessionId: 'session-123',
  useRAG: true,
  ragTopK: 4,
  debug: true
});

// Stream chat messages
for await (const response of api.chat(messages)) {
  if (response.delta) {
    console.log('Received:', response.content);
  }
}
```

#### Custom Hooks
- [`hooks/use-webai.ts`](frontend-chatgpt-iframe/chatgpt-next-web-webai/hooks/use-webai.ts) - WebAI integration hooks
  - **useWebAIChat()**: Chat functionality hook
  - **useWebAIEvents()**: Event handling hook

## 🎮 Widget Integration & Iframe Embedding

### Widget Deployment

The frontend includes a sophisticated iframe widget system for seamless website integration.

#### Widget Script
[`public/webai-widget-iframe.js`](frontend-chatgpt-iframe/chatgpt-next-web-webai/public/webai-widget-iframe.js) provides:

- **Responsive Design**: Desktop (420x650px) and mobile (fullscreen) layouts
- **Cross-Origin Communication**: Secure parent-child messaging
- **Keyboard Shortcuts**: Ctrl/Cmd+Shift+K to toggle
- **Analytics Integration**: Google Analytics event tracking
- **Performance Optimization**: Lazy loading and efficient rendering

#### Basic Widget Integration

```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Website</title>
</head>
<body>
    <!-- Your website content -->
    
    <!-- WebAI Widget Configuration -->
    <script>
        window.WEBAI_CHATUI_URL = "https://your-frontend.vercel.app";
        window.WEBAI_TENANT_ID = "your-tenant-id";
        window.WEBAI_USE_RAG = true;
        window.WEBAI_RAG_TOP_K = 4;
        window.WEBAI_TITLE = "AI Assistant";
        window.WEBAI_DEBUG = false;
    </script>
    
    <!-- Load WebAI Widget -->
    <script src="https://your-frontend.vercel.app/webai-widget-iframe.js" defer></script>
</body>
</html>
```

#### Advanced Widget Configuration

```html
<script>
    // Required Configuration
    window.WEBAI_CHATUI_URL = "https://chatgpt-next-web-webai.vercel.app";
    window.WEBAI_TENANT_ID = "company-123";
    
    // Optional RAG Configuration
    window.WEBAI_USE_RAG = true;
    window.WEBAI_RAG_TOP_K = 5;
    
    // Optional Customization
    window.WEBAI_TITLE = "Customer Support";
    window.WEBAI_DEBUG = false;
</script>
<script src="https://storage.googleapis.com/your-bucket/webai-widget-iframe.js" defer></script>
```

#### Programmatic Widget Control

```javascript
// Widget API (available after script loads)
window.WebAIWidget.open();           // Open widget
window.WebAIWidget.close();          // Close widget
window.WebAIWidget.toggle();         // Toggle widget
window.WebAIWidget.isOpen();         // Check if open
window.WebAIWidget.sendMessage("Hello"); // Send message
window.WebAIWidget.configure({       // Update config
    tenantId: "new-tenant",
    useRAG: false
});
```

### Direct Iframe Integration

For custom implementations without the widget wrapper:

```html
<iframe
    src="https://your-frontend.vercel.app/embedded/chat?embedded=true&tenant=your-tenant&session=user-123&rag=true&rag_top_k=4"
    width="420"
    height="650"
    frameborder="0"
    allow="clipboard-read; clipboard-write"
    sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
    title="AI Chat Assistant">
</iframe>
```

#### Iframe Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `embedded` | boolean | Enable embedded mode | `false` |
| `tenant` | string | Tenant identifier | `"default"` |
| `session` | string | Session identifier | `"default"` |
| `rag` | boolean | Enable RAG functionality | `false` |
| `rag_top_k` | number | RAG results count | `4` |
| `title` | string | Chat title | `"AI Assistant"` |
| `debug` | boolean | Enable debug mode | `false` |

### Next.js Configuration for Iframe Embedding

The [`next.config.js`](frontend-chatgpt-iframe/chatgpt-next-web-webai/next.config.js) is optimized for iframe usage:

```javascript
module.exports = {
  // Enable iframe embedding
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'ALLOWALL', // Allow iframe embedding
          },
          {
            key: 'Content-Security-Policy',
            value: 'frame-ancestors *; ...' // Flexible CSP
          }
        ],
      }
    ];
  },
  
  // Redirect embedded requests
  async redirects() {
    return [
      {
        source: '/chat',
        has: [{ type: 'query', key: 'embedded', value: 'true' }],
        destination: '/embedded/chat',
        permanent: false,
      },
    ];
  }
};
```

## 🏗️ Build & Deployment Process

### Development Build
```bash
cd frontend-chatgpt-iframe/chatgpt-next-web-webai

# Start development server with hot reload
npm run dev

# Type checking during development
npm run type-check

# Linting
npm run lint
```

### Production Build
```bash
# Build for production
npm run build

# Start production server
npm start

# Export static files (if needed)
npm run export

# Combined build and export
npm run deploy
```

### Build Configuration

The application is configured for optimal production deployment:

#### Next.js Configuration
```javascript
// next.config.js
module.exports = {
  output: 'standalone',      // Optimized for containerization
  compress: true,            // Enable gzip compression
  poweredByHeader: false,    // Remove X-Powered-By header
  swcMinify: true,          // Fast Rust-based minification
  reactStrictMode: true,     // Enable React strict mode
  telemetry: false,         // Disable telemetry
};
```

#### TypeScript Configuration
```json
{
  "compilerOptions": {
    "target": "es2020",
    "lib": ["dom", "dom.iterable", "es2020"],
    "strict": false,
    "skipLibCheck": true,
    "incremental": true
  }
}
```

### Deployment Options

#### Vercel Deployment (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
vercel

# Production deployment
vercel --prod
```

**Vercel Configuration** (vercel.json):
```json
{
  "buildCommand": "cd frontend-chatgpt-iframe/chatgpt-next-web-webai && npm run build",
  "outputDirectory": "frontend-chatgpt-iframe/chatgpt-next-web-webai/.next",
  "installCommand": "cd frontend-chatgpt-iframe/chatgpt-next-web-webai && npm install"
}
```

#### Docker Deployment
```bash
# Build Docker image
docker build -t webai-frontend:latest ./frontend-chatgpt-iframe/chatgpt-next-web-webai

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_WEBAI_API_URL=https://your-backend.run.app \
  -e NEXT_PUBLIC_WEBAI_DEBUG=false \
  webai-frontend:latest
```

#### Static Export (for CDN)
```bash
# Build and export static files
npm run deploy

# Deploy to CDN/Cloud Storage
# Upload .next/out/* to your CDN
```

### Environment-Specific Deployments

#### Production Environment Variables
```bash
# Vercel environment variables
vercel env add NEXT_PUBLIC_WEBAI_API_URL production
vercel env add NEXT_PUBLIC_WEBAI_DEBUG production
vercel env add NEXT_PUBLIC_APP_NAME production
```

#### Google Cloud Run Deployment
```bash
# Build and submit
gcloud builds submit --tag gcr.io/PROJECT_ID/webai-frontend

# Deploy to Cloud Run
gcloud run deploy webai-frontend \
  --image gcr.io/PROJECT_ID/webai-frontend \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars NEXT_PUBLIC_WEBAI_API_URL=https://your-backend.run.app
```

## 🧪 Frontend Testing

### Testing Strategy

#### Unit Testing
```bash
# Install testing dependencies
npm install --save-dev jest @testing-library/react @testing-library/jest-dom

# Run unit tests
npm run test

# Run tests with coverage
npm run test:coverage
```

#### Integration Testing
```bash
# Install Cypress for e2e testing
npm install --save-dev cypress

# Run Cypress tests
npm run cypress:open
```

#### Component Testing
```javascript
// Example component test
import { render, screen } from '@testing-library/react';
import ChatInput from '@/components/ChatInput';

test('renders chat input with placeholder', () => {
  render(<ChatInput placeholder="Type a message..." />);
  expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
});
```

#### API Integration Testing
```javascript
// Example API test
import { WebAIApi } from '@/lib/webai-api';

test('WebAI API connection test', async () => {
  const api = new WebAIApi({
    apiUrl: 'http://localhost:8080',
    tenantId: 'test-tenant',
    sessionId: 'test-session',
    useRAG: false,
    ragTopK: 4
  });
  
  const isConnected = await api.testConnection();
  expect(isConnected).toBe(true);
});
```

### Manual Testing Procedures

#### Chat Interface Testing
1. **Basic Chat Flow**
   ```bash
   # Navigate to embedded chat
   open http://localhost:3000/embedded/chat?embedded=true&tenant=test&session=test
   
   # Test message sending
   # Test streaming responses
   # Test error handling
   ```

2. **Setup Wizard Testing**
   ```bash
   # Navigate to setup wizard
   open http://localhost:3000/setup
   
   # Test step progression
   # Test form validation
   # Test API integration
   ```

3. **Widget Integration Testing**
   ```html
   <!-- Create test HTML file -->
   <!DOCTYPE html>
   <html>
   <head><title>Widget Test</title></head>
   <body>
       <h1>Test Page</h1>
       <script>
           window.WEBAI_CHATUI_URL = "http://localhost:3000";
           window.WEBAI_TENANT_ID = "test-tenant";
       </script>
       <script src="http://localhost:3000/webai-widget-iframe.js"></script>
   </body>
   </html>
   ```

#### Performance Testing
```bash
# Lighthouse audit
npx lighthouse http://localhost:3000 --view

# Bundle analysis
npm run analyze

# Load testing with artillery
npm install -g artillery
artillery quick --count 10 --num 3 http://localhost:3000
```

### Testing Checklist

#### Functionality Testing
- [ ] Chat message sending and receiving
- [ ] Streaming response handling
- [ ] Error state management
- [ ] Conversation history loading
- [ ] Setup wizard completion
- [ ] File upload and processing
- [ ] Widget toggle functionality
- [ ] Cross-origin communication

#### Compatibility Testing
- [ ] Chrome/Chromium browsers
- [ ] Firefox browser
- [ ] Safari browser
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)
- [ ] Iframe embedding in various websites
- [ ] Different viewport sizes

#### Performance Testing
- [ ] Initial page load time < 3s
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 5s
- [ ] Bundle size optimization
- [ ] Image optimization
- [ ] Memory usage monitoring

This comprehensive frontend setup provides a production-ready Next.js application with sophisticated chat capabilities, tenant management, and seamless iframe widget integration. The architecture is designed for scalability, maintainability, and optimal user experience across all devices and deployment scenarios.

---

# 🚀 WebAI Deployment Guide

Comprehensive deployment instructions for all environments covering both backend (FastAPI) and frontend (Next.js) components with multi-cloud support, Docker containerization, and advanced deployment strategies.

## 📋 Deployment Overview

The WebAI application consists of:
- **Backend**: FastAPI with Redis, Milvus/Zilliz, external API integrations
- **Frontend**: Next.js application with widget embedding capabilities
- **Databases**: Redis for caching/sessions, Milvus/Zilliz for vector storage
- **Widget**: Iframe-embeddable chat widget for website integration

### Deployment Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Databases     │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│ Redis + Milvus  │
│                 │    │                 │    │                 │
│ • Vercel        │    │ • Cloud Run     │    │ • Cloud Redis   │
│ • Static CDN    │    │ • AWS ECS       │    │ • Zilliz Cloud  │
│ • Self-hosted   │    │ • Self-hosted   │    │ • Self-hosted   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🏠 Development Environment Deployment

### Docker Compose Full Stack Setup

Create a complete local development environment with all services:

#### 1. Create Docker Compose Configuration

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # Redis for caching and rate limiting
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Optional: Separate Redis for conversations
  redis-conversations:
    image: redis:7-alpine
    ports:
      - "6380:6380"
    volumes:
      - redis_conversations_data:/data
    command: redis-server --port 6380 --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "-p", "6380", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Milvus for vector storage
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
      - "9091:9091"
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - milvus_data:/var/lib/milvus
    depends_on:
      - etcd
      - minio
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Etcd for Milvus metadata
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: 1000
      ETCD_QUOTA_BACKEND_BYTES: 4294967296
      ETCD_SNAPSHOT_COUNT: 50000
    volumes:
      - etcd_data:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  # MinIO for Milvus object storage
  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    command: minio server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # WebAI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379
      - CONVERSATION_REDIS_URL=redis://redis-conversations:6380
      - WEBAI_ADMIN_KEY=dev-admin-key-12345
      - RATE_LIMIT_PER_MINUTE=100
      - RATE_LIMIT_PER_HOUR=5000
      - OPENROUTER_HTTP_REFERER=http://localhost:3000
      - OPENROUTER_X_TITLE=WebAI Local Dev
      - PYTHONPATH=/app
    volumes:
      - ./backend/app:/app/app
    depends_on:
      redis:
        condition: service_healthy
      milvus:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  # WebAI Frontend
  frontend:
    build:
      context: ./frontend-chatgpt-iframe/chatgpt-next-web-webai
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_WEBAI_API_URL=http://localhost:8080
      - NEXT_PUBLIC_WEBAI_DEBUG=true
      - NEXT_PUBLIC_APP_NAME=WebAI Chat - Dev
    volumes:
      - ./frontend-chatgpt-iframe/chatgpt-next-web-webai:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      backend:
        condition: service_healthy
    command: npm run dev
    restart: unless-stopped

volumes:
  redis_data:
  redis_conversations_data:
  milvus_data:
  etcd_data:
  minio_data:

networks:
  default:
    driver: bridge
```

#### 2. Create Frontend Development Dockerfile

```dockerfile
# frontend-chatgpt-iframe/chatgpt-next-web-webai/Dockerfile.dev
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "run", "dev"]
```

#### 3. Development Environment Setup

```bash
# Start the complete development stack
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Reset all data (clean slate)
docker-compose -f docker-compose.dev.yml down -v
```

### Alternative: Manual Development Setup

#### 1. Prerequisites Installation

```bash
# Install Redis
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# Install Milvus (using Docker)
curl -sfL https://raw.githubusercontent.com/milvus-io/milvus/master/scripts/standalone_embed.sh -o standalone_embed.sh
bash standalone_embed.sh start
```

#### 2. Backend Development Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment variables
cat << EOF > .env
REDIS_URL=redis://localhost:6379
CONVERSATION_REDIS_URL=redis://localhost:6380
WEBAI_ADMIN_KEY=dev-admin-key-12345
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000
OPENROUTER_HTTP_REFERER=http://localhost:3000
OPENROUTER_X_TITLE="WebAI Local Dev"
EOF

# Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

#### 3. Frontend Development Setup

```bash
# Navigate to frontend directory
cd frontend-chatgpt-iframe/chatgpt-next-web-webai

# Install dependencies
npm install

# Set up environment variables
cat << EOF > .env.local
NEXT_PUBLIC_WEBAI_API_URL=http://localhost:8080
NEXT_PUBLIC_WEBAI_DEBUG=true
NEXT_PUBLIC_APP_NAME="WebAI Chat - Local"
EOF

# Start development server
npm run dev
```

### Development Environment Verification

```bash
# Check all services
curl http://localhost:8080/health  # Backend health
curl http://localhost:3000         # Frontend
curl http://localhost:3000/embedded/chat?embedded=true&tenant=test  # Widget

# Test Redis
redis-cli ping

# Test Milvus
python -c "from pymilvus import connections; connections.connect('default', host='localhost', port='19530'); print('✅ Milvus connected')"
```

## 🧪 Staging Environment Deployment

### Cloud-Based Staging Setup

Staging environment mirrors production but with relaxed security and monitoring for testing purposes.

#### Google Cloud Staging Deployment

```bash
# Set up staging project
gcloud config set project webai-staging

# 1. Deploy Redis (Cloud Memorystore)
gcloud redis instances create webai-staging-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0

# 2. Deploy backend to Cloud Run
gcloud builds submit --tag gcr.io/webai-staging/webai-backend:staging ./backend

gcloud run deploy webai-backend-staging \
  --image gcr.io/webai-staging/webai-backend:staging \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 1000 \
  --max-instances 10 \
  --set-env-vars REDIS_URL="redis://$(gcloud redis instances describe webai-staging-redis --region=us-central1 --format='value(host)'):6379" \
  --set-env-vars WEBAI_ADMIN_KEY="staging-admin-key-$(openssl rand -hex 16)" \
  --set-env-vars RATE_LIMIT_PER_MINUTE=60 \
  --set-env-vars RATE_LIMIT_PER_HOUR=2000 \
  --set-env-vars OPENROUTER_HTTP_REFERER="https://webai-frontend-staging.vercel.app"

# 3. Deploy frontend to Vercel (staging)
cd frontend-chatgpt-iframe/chatgpt-next-web-webai

vercel --prod --env NEXT_PUBLIC_WEBAI_API_URL="$(gcloud run services describe webai-backend-staging --region=us-central1 --format='value(status.url)')" \
  --env NEXT_PUBLIC_WEBAI_DEBUG=true \
  --env NEXT_PUBLIC_APP_NAME="WebAI Chat - Staging"
```

#### AWS Staging Deployment

```bash
# 1. Create staging ECS cluster
aws ecs create-cluster --cluster-name webai-staging

# 2. Deploy Redis (ElastiCache)
aws elasticache create-replication-group \
  --replication-group-id webai-staging-redis \
  --description "WebAI Staging Redis" \
  --num-cache-clusters 1 \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0

# 3. Build and push backend image
aws ecr create-repository --repository-name webai-backend-staging
docker build -t webai-backend-staging ./backend
docker tag webai-backend-staging:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/webai-backend-staging:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/webai-backend-staging:latest

# 4. Deploy via ECS service (task definition required)
aws ecs create-service \
  --cluster webai-staging \
  --service-name webai-backend-staging \
  --task-definition webai-backend-staging:1 \
  --desired-count 2

# 5. Deploy frontend to AWS Amplify or S3 + CloudFront
aws amplify create-app --name webai-frontend-staging
```

### Staging Environment Testing

#### Automated Testing Pipeline

```bash
#!/bin/bash
# staging-test.sh

BACKEND_URL="https://webai-backend-staging-xyz.run.app"
FRONTEND_URL="https://webai-frontend-staging.vercel.app"

echo "🧪 Testing Staging Environment..."

# Test backend health
echo "Testing backend health..."
if curl -f "$BACKEND_URL/health"; then
  echo "✅ Backend health check passed"
else
  echo "❌ Backend health check failed"
  exit 1
fi

# Test frontend loading
echo "Testing frontend loading..."
if curl -f "$FRONTEND_URL"; then
  echo "✅ Frontend loading passed"
else
  echo "❌ Frontend loading failed"
  exit 1
fi

# Test widget embedding
echo "Testing widget embedding..."
if curl -f "$FRONTEND_URL/embedded/chat?embedded=true&tenant=test"; then
  echo "✅ Widget embedding passed"
else
  echo "❌ Widget embedding failed"
  exit 1
fi

# Test API endpoints
echo "Testing API endpoints..."
TENANT_RESPONSE=$(curl -s -X POST "$BACKEND_URL/register-tenant" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: staging-admin-key" \
  -d '{
    "openrouter_api_key": "test-key",
    "system_prompt": "Test assistant",
    "allowed_domains": ["staging-test.com"],
    "model": "openai/gpt-4o-mini"
  }')

if echo "$TENANT_RESPONSE" | grep -q "tenant_id"; then
  echo "✅ Tenant registration passed"
else
  echo "❌ Tenant registration failed"
  exit 1
fi

echo "🎉 All staging tests passed!"
```

### Environment Isolation

#### Staging-Specific Configurations

```yaml
# staging-config.yml
environment: staging
debug: true
monitoring:
  metrics_enabled: true
  logging_level: debug
  error_tracking: enabled
  
database:
  redis:
    max_connections: 50
    timeout: 5
  milvus:
    collection_prefix: staging_
    cleanup_on_restart: true

security:
  rate_limits:
    relaxed: true
    per_minute: 100
    per_hour: 5000
  cors:
    allow_all_origins: true
  
performance:
  cache_ttl: 300  # 5 minutes (shorter for testing)
  max_file_size: 100MB
  batch_size: 500
```

## 🌐 Production Deployment Options

### Google Cloud Platform Deployment

#### Complete GCP Production Setup

```bash
#!/bin/bash
# gcp-production-deploy.sh

PROJECT_ID="webai-production"
REGION="us-central1"
ZONE="us-central1-a"

# Set up project
gcloud config set project $PROJECT_ID

echo "🚀 Deploying WebAI to Google Cloud Platform..."

# 1. Enable required APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com

# 2. Create secrets
echo "Creating secrets..."
gcloud secrets create webai-admin-key --data-file=<(openssl rand -hex 32)
gcloud secrets create openrouter-api-key --data-file=<(echo "your-openrouter-key")
gcloud secrets create voyageai-api-key --data-file=<(echo "your-voyageai-key")

# 3. Deploy Redis (Production-grade)
echo "Deploying Redis..."
gcloud redis instances create webai-prod-redis \
  --size=5 \
  --region=$REGION \
  --redis-version=redis_7_0 \
  --maintenance-policy-day=SUNDAY \
  --maintenance-policy-start-time="02:00" \
  --auth-enabled \
  --transit-encryption-mode=SERVER_CLIENT

# Optional: Separate Redis for conversations
gcloud redis instances create webai-prod-redis-conversations \
  --size=3 \
  --region=$REGION \
  --redis-version=redis_7_0 \
  --auth-enabled

# 4. Build and deploy backend
echo "Building backend..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/webai-backend:latest ./backend

echo "Deploying backend to Cloud Run..."
gcloud run deploy webai-backend \
  --image gcr.io/$PROJECT_ID/webai-backend:latest \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --concurrency 1000 \
  --max-instances 100 \
  --min-instances 2 \
  --cpu-throttling \
  --set-env-vars REDIS_URL="redis://$(gcloud redis instances describe webai-prod-redis --region=$REGION --format='value(host)'):6379" \
  --set-env-vars CONVERSATION_REDIS_URL="redis://$(gcloud redis instances describe webai-prod-redis-conversations --region=$REGION --format='value(host)'):6379" \
  --set-env-vars WEBAI_ADMIN_KEY="$(gcloud secrets versions access latest --secret=webai-admin-key)" \
  --set-env-vars RATE_LIMIT_PER_MINUTE=30 \
  --set-env-vars RATE_LIMIT_PER_HOUR=1000 \
  --set-env-vars OPENROUTER_HTTP_REFERER="https://chat.yourdomain.com"

# 5. Set up custom domain (optional)
gcloud run domain-mappings create \
  --service webai-backend \
  --domain api.yourdomain.com \
  --region $REGION

echo "✅ Backend deployed successfully!"
echo "Backend URL: $(gcloud run services describe webai-backend --region=$REGION --format='value(status.url)')"
```

### Vercel Frontend Production Deployment

#### Production Vercel Configuration

```json
{
  "version": 2,
  "name": "webai-frontend-production",
  "builds": [
    {
      "src": "frontend-chatgpt-iframe/chatgpt-next-web-webai/package.json",
      "use": "@vercel/next"
    }
  ],
  "env": {
    "NEXT_PUBLIC_WEBAI_API_URL": "https://api.yourdomain.com",
    "NEXT_PUBLIC_WEBAI_DEBUG": "false",
    "NEXT_PUBLIC_APP_NAME": "WebAI Chat"
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Frame-Options",
          "value": "ALLOWALL"
        },
        {
          "key": "Strict-Transport-Security",
          "value": "max-age=31536000; includeSubDomains"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        }
      ]
    }
  ],
  "functions": {
    "pages/api/**/*.js": {
      "maxDuration": 30
    }
  },
  "regions": ["iad1", "sfo1"]
}
```

#### Production Deployment Commands

```bash
# Deploy to Vercel production
cd frontend-chatgpt-iframe/chatgpt-next-web-webai

# Set production environment variables
vercel env add NEXT_PUBLIC_WEBAI_API_URL production
vercel env add NEXT_PUBLIC_WEBAI_DEBUG production
vercel env add NEXT_PUBLIC_APP_NAME production

# Deploy
vercel --prod

# Set up custom domain
vercel domains add chat.yourdomain.com
```

### AWS Production Deployment

#### ECS Fargate Backend Deployment

```yaml
# aws-backend-task-definition.json
{
  "family": "webai-backend-prod",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "webai-backend",
      "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/webai-backend:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "REDIS_URL",
          "value": "redis://webai-prod.redis.cache.amazonaws.com:6379"
        },
        {
          "name": "RATE_LIMIT_PER_MINUTE",
          "value": "30"
        },
        {
          "name": "RATE_LIMIT_PER_HOUR",
          "value": "1000"
        }
      ],
      "secrets": [
        {
          "name": "WEBAI_ADMIN_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:webai/admin-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/webai-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### AWS Deployment Script

```bash
#!/bin/bash
# aws-production-deploy.sh

CLUSTER_NAME="webai-production"
SERVICE_NAME="webai-backend"
REGION="us-east-1"

echo "🚀 Deploying WebAI to AWS..."

# 1. Create ECS cluster
aws ecs create-cluster --cluster-name $CLUSTER_NAME

# 2. Create ElastiCache Redis
aws elasticache create-replication-group \
  --replication-group-id webai-prod-redis \
  --description "WebAI Production Redis" \
  --num-cache-clusters 3 \
  --cache-node-type cache.r7g.large \
  --engine redis \
  --engine-version 7.0 \
  --automatic-failover-enabled \
  --multi-az-enabled

# 3. Build and push Docker image
aws ecr create-repository --repository-name webai-backend
docker build -t webai-backend ./backend
docker tag webai-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/webai-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/webai-backend:latest

# 4. Register task definition
aws ecs register-task-definition --cli-input-json file://aws-backend-task-definition.json

# 5. Create ECS service
aws ecs create-service \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --task-definition webai-backend-prod:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-abcdef],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:$REGION:$AWS_ACCOUNT_ID:targetgroup/webai-backend/abc123,containerName=webai-backend,containerPort=8080

echo "✅ AWS deployment completed!"
```

## ⚙️ CI/CD Pipeline Configuration

### GitHub Actions Workflows

#### Complete CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: WebAI CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE_NAME: webai/backend
  FRONTEND_IMAGE_NAME: webai/frontend

jobs:
  # Test and Build Backend
  backend-test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd backend
          pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        env:
          REDIS_URL: redis://localhost:6379
          WEBAI_ADMIN_KEY: test-admin-key
        run: |
          cd backend
          python -m pytest tests/ -v
          python run_comprehensive_tests.py

      - name: Build backend Docker image
        run: |
          docker build -t ${{ env.REGISTRY }}/${{ env.BACKEND_IMAGE_NAME }}:${{ github.sha }} ./backend

  # Test and Build Frontend
  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: 'frontend-chatgpt-iframe/chatgpt-next-web-webai/package-lock.json'

      - name: Install dependencies
        run: |
          cd frontend-chatgpt-iframe/chatgpt-next-web-webai
          npm ci

      - name: Type check
        run: |
          cd frontend-chatgpt-iframe/chatgpt-next-web-webai
          npm run type-check

      - name: Lint
        run: |
          cd frontend-chatgpt-iframe/chatgpt-next-web-webai
          npm run lint

      - name: Build
        env:
          NEXT_PUBLIC_WEBAI_API_URL: https://api-test.example.com
          NEXT_PUBLIC_WEBAI_DEBUG: false
        run: |
          cd frontend-chatgpt-iframe/chatgpt-next-web-webai
          npm run build

  # Deploy to Staging
  deploy-staging:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    if: github.ref == 'refs/heads/develop'
    environment: staging
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure Google Cloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY_STAGING }}
          project_id: ${{ secrets.GCP_PROJECT_ID_STAGING }}

      - name: Deploy backend to Cloud Run
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID_STAGING }}/webai-backend:${{ github.sha }} ./backend
          gcloud run deploy webai-backend-staging \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID_STAGING }}/webai-backend:${{ github.sha }} \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated

      - name: Deploy frontend to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID_STAGING }}
          working-directory: frontend-chatgpt-iframe/chatgpt-next-web-webai

  # Deploy to Production
  deploy-production:
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure Google Cloud
        uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY_PRODUCTION }}
          project_id: ${{ secrets.GCP_PROJECT_ID_PRODUCTION }}

      - name: Deploy backend to Cloud Run (Blue-Green)
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID_PRODUCTION }}/webai-backend:${{ github.sha }} ./backend
          gcloud run deploy webai-backend \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID_PRODUCTION }}/webai-backend:${{ github.sha }} \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated \
            --no-traffic \
            --tag candidate

          # Gradual traffic migration
          gcloud run services update-traffic webai-backend \
            --to-tags candidate=10 \
            --region us-central1

          # Wait and monitor
          sleep 300

          # Full traffic migration if successful
          gcloud run services update-traffic webai-backend \
            --to-tags candidate=100 \
            --region us-central1

      - name: Deploy frontend to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID_PRODUCTION }}
          working-directory: frontend-chatgpt-iframe/chatgpt-next-web-webai
          vercel-args: '--prod'
```

## 🗄️ Database Deployment

### Redis Deployment Options

#### Cloud Redis (Recommended for Production)

##### Google Cloud Memorystore

```bash
# Production Redis with high availability
gcloud redis instances create webai-prod-redis \
  --size=5 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=STANDARD_HA \
  --auth-enabled \
  --transit-encryption-mode=SERVER_CLIENT \
  --maintenance-policy-day=SUNDAY \
  --maintenance-policy-start-time="02:00"

# Staging Redis (smaller, basic tier)
gcloud redis instances create webai-staging-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0 \
  --tier=BASIC

# Get connection details
gcloud redis instances describe webai-prod-redis --region=us-central1
```

##### AWS ElastiCache

```bash
# Production Redis cluster
aws elasticache create-replication-group \
  --replication-group-id webai-prod-redis \
  --description "WebAI Production Redis" \
  --num-cache-clusters 3 \
  --cache-node-type cache.r7g.large \
  --engine redis \
  --engine-version 7.0 \
  --port 6379 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token $(openssl rand -base64 32)

# Create subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name webai-redis-subnet \
  --cache-subnet-group-description "WebAI Redis Subnet Group" \
  --subnet-ids subnet-12345 subnet-67890
```

#### Self-Hosted Redis Cluster

```yaml
# redis-cluster.yml
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 2gb --maxmemory-policy allkeys-lru
    environment:
      - REDIS_REPLICATION_MODE=master
    volumes:
      - redis_master_data:/data
    ports:
      - "6379:6379"
    networks:
      - redis_cluster

  redis-replica-1:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379 --requirepass ${REDIS_PASSWORD} --masterauth ${REDIS_PASSWORD}
    depends_on:
      - redis-master
    volumes:
      - redis_replica1_data:/data
    networks:
      - redis_cluster

  redis-replica-2:
    image: redis:7-alpine
    command: redis-server --replicaof redis-master 6379 --requirepass ${REDIS_PASSWORD} --masterauth ${REDIS_PASSWORD}
    depends_on:
      - redis-master
    volumes:
      - redis_replica2_data:/data
    networks:
      - redis_cluster

  redis-sentinel-1:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    configs:
      - source: sentinel_config
        target: /etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - redis_cluster

  redis-sentinel-2:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    configs:
      - source: sentinel_config
        target: /etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - redis_cluster

  redis-sentinel-3:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    configs:
      - source: sentinel_config
        target: /etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - redis_cluster

volumes:
  redis_master_data:
  redis_replica1_data:
  redis_replica2_data:

networks:
  redis_cluster:
    driver: overlay

configs:
  sentinel_config:
    content: |
      port 26379
      sentinel monitor webai-master redis-master 6379 2
      sentinel down-after-milliseconds webai-master 5000
      sentinel failover-timeout webai-master 10000
      sentinel auth-pass webai-master ${REDIS_PASSWORD}
```

### Milvus/Zilliz Deployment Options

#### Zilliz Cloud (Recommended for Production)

```bash
# 1. Sign up at https://cloud.zilliz.com
# 2. Create a cluster through the web interface
# 3. Note the connection details:

# Example connection configuration
MILVUS_URI="https://in03-xxxx.zillizcloud.com"
MILVUS_TOKEN="your-cluster-token"
MILVUS_DB_NAME="_default"

# Test connection
python -c "
from pymilvus import connections
connections.connect(
    alias='default',
    uri='$MILVUS_URI',
    token='$MILVUS_TOKEN'
)
print('✅ Zilliz Cloud connected successfully')
"
```

#### Self-Hosted Milvus Production Setup

```yaml
# milvus-production.yml
version: '3.8'

services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd_data:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    command: minio server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus:
    image: milvusdb/milvus:v2.3.4
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
    volumes:
      - milvus_data:/var/lib/milvus
      - ./milvus.yaml:/milvus/configs/milvus.yaml
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      etcd:
        condition: service_healthy
      minio:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      timeout: 20s
      retries: 5

volumes:
  etcd_data:
  minio_data:
  milvus_data:
```

#### Milvus Production Configuration

```yaml
# milvus.yaml
etcd:
  endpoints:
    - etcd:2379

minio:
  address: minio
  port: 9000
  accessKeyID: ${MINIO_ACCESS_KEY}
  secretAccessKey: ${MINIO_SECRET_KEY}
  useSSL: false
  bucketName: milvus-bucket

common:
  defaultPartitionName: _default
  defaultIndexName: _default_idx

storage:
  path: /var/lib/milvus/data
  
log:
  level: info
  file:
    rootPath: /var/lib/milvus/logs

metrics:
  enabled: true
  address: 0.0.0.0
  port: 9091
```

### Database Migration and Backup Procedures

#### Redis Backup and Restore

```bash
# Backup Redis data
redis-cli --rdb /backup/dump.rdb

# Scheduled backup script
#!/bin/bash
# redis-backup.sh
BACKUP_DIR="/backup/redis"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/dump_$DATE.rdb"

mkdir -p $BACKUP_DIR
redis-cli --rdb $BACKUP_FILE
gzip $BACKUP_FILE

# Upload to cloud storage
gsutil cp $BACKUP_FILE.gz gs://webai-backups/redis/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.rdb.gz" -mtime +30 -delete
```

#### Milvus Backup and Restore

```bash
# Backup Milvus collections
python << EOF
from pymilvus import Collection, connections

connections.connect("default", host="localhost", port="19530")

# List all collections
collections = Collection.list()
print(f"Found collections: {collections}")

# Export each collection
for collection_name in collections:
    collection = Collection(collection_name)
    # Backup logic here
    print(f"Backing up {collection_name}")
EOF

# Backup Milvus data directory
tar -czf milvus_backup_$(date +%Y%m%d).tar.gz /var/lib/milvus/data
```

## 📊 Monitoring and Health Checks

### Application Monitoring

#### Health Check Endpoints

```python
# Enhanced health check implementation
from fastapi import APIRouter, HTTPException
from app.core.redis import get_redis_client
from pymilvus import connections
import asyncio
import time

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check for all services"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check Redis connectivity
    try:
        redis = get_redis_client()
        await redis.ping()
        health_status["services"]["redis"] = {
            "status": "healthy",
            "response_time_ms": 0
        }
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Milvus connectivity
    try:
        connections.connect("health_check", host="localhost", port="19530")
        connections.disconnect("health_check")
        health_status["services"]["milvus"] = {
            "status": "healthy"
        }
    except Exception as e:
        health_status["services"]["milvus"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check API dependencies
    health_status["services"]["openrouter"] = await check_external_api("https://openrouter.ai/api/v1/models")
    health_status["services"]["voyageai"] = await check_external_api("https://api.voyageai.com/v1/models")
    
    return health_status

@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    # Quick checks for service readiness
    try:
        redis = get_redis_client()
        await redis.ping()
        return {"status": "ready"}
    except:
        raise HTTPException(status_code=503, detail="Service not ready")

@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}

async def check_external_api(url: str) -> dict:
    """Check external API availability"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            start_time = time.time()
            response = await client.get(url)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2)
                }
            else:
                return {
                    "status": "unhealthy",
                    "status_code": response.status_code
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
```

#### Monitoring Dashboard Configuration

```yaml
# monitoring/docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources

  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://redis:6379
    depends_on:
      - redis

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'

volumes:
  prometheus_data:
  grafana_data:
```

#### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'webai-backend'
    static_configs:
      - targets: ['backend:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Alerting Configuration

#### Alert Rules

```yaml
# monitoring/alert_rules.yml
groups:
  - name: webai-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is {{ $value }} seconds"

      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis has been down for more than 1 minute"

      - alert: BackendDown
        expr: up{job="webai-backend"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Backend is down"
          description: "WebAI backend has been down for more than 1 minute"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: DiskSpaceLow
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk usage is {{ $value | humanizePercentage }}"
```

### Logging Configuration

#### Structured Logging Setup

```python
# app/core/logging.py
import logging
import json
import time
from typing import Any, Dict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        handler = logging.StreamHandler()
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": time.time(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add any extra fields
        if hasattr(record, 'tenant_id'):
            log_data['tenant_id'] = record.tenant_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
            
        return json.dumps(log_data)

class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = StructuredLogger("webai.requests")
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = f"{int(start_time * 1000)}-{hash(request)}"
        
        # Log request
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers)
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        duration = time.time() - start_time
        self.logger.info(
            "Request completed",
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )
        
        return response
```

## 🔄 Rollback and Recovery Procedures

### Automated Rollback Strategies

#### Blue-Green Deployment with Rollback

```bash
#!/bin/bash
# rollback-production.sh

PROJECT_ID="webai-production"
REGION="us-central1"
SERVICE_NAME="webai-backend"

echo "🔄 Starting rollback procedure..."

# Get current revision
CURRENT_REVISION=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.latestReadyRevisionName)")

echo "Current revision: $CURRENT_REVISION"

# Get previous revision
PREVIOUS_REVISION=$(gcloud run revisions list \
  --service=$SERVICE_NAME \
  --region=$REGION \
  --limit=2 \
  --format="value(metadata.name)" | tail -n 1)

echo "Rolling back to: $PREVIOUS_REVISION"

# Confirm rollback
read -p "Confirm rollback to $PREVIOUS_REVISION? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
  echo "Rollback cancelled"
  exit 0
fi

# Perform rollback
echo "Performing rollback..."
gcloud run services update-traffic $SERVICE_NAME \
  --to-revisions=$PREVIOUS_REVISION=100 \
  --region=$REGION

# Verify rollback
sleep 30
NEW_CURRENT=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.latestReadyRevisionName)")

if [[ "$NEW_CURRENT" == "$PREVIOUS_REVISION" ]]; then
  echo "✅ Rollback successful!"
  
  # Run health checks
  BACKEND_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)")
  
  if curl -f "$BACKEND_URL/health"; then
    echo "✅ Health check passed"
  else
    echo "❌ Health check failed - manual intervention required"
    exit 1
  fi
else
  echo "❌ Rollback failed - manual intervention required"
  exit 1
fi

# Notify team
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H 'Content-type: application/json' \
  --data "{\"text\":\"🔄 WebAI Production Rollback Completed: $CURRENT_REVISION → $PREVIOUS_REVISION\"}"

echo "🎉 Rollback completed successfully!"
```

#### Database Recovery Procedures

```bash
#!/bin/bash
# database-recovery.sh

ENVIRONMENT=${1:-production}
BACKUP_DATE=${2:-latest}

echo "🔄 Starting database recovery for $ENVIRONMENT..."

case $ENVIRONMENT in
  "production")
    REDIS_HOST="webai-prod-redis.region.cache.amazonaws.com"
    BACKUP_BUCKET="webai-prod-backups"
    ;;
  "staging")
    REDIS_HOST="webai-staging-redis.region.cache.amazonaws.com"
    BACKUP_BUCKET="webai-staging-backups"
    ;;
  *)
    echo "Invalid environment: $ENVIRONMENT"
    exit 1
    ;;
esac

# 1. Stop application instances
echo "Stopping application instances..."
if [[ $ENVIRONMENT == "production" ]]; then
  gcloud run services update webai-backend \
    --region=us-central1 \
    --min-instances=0 \
    --max-instances=0
else
  gcloud run services update webai-backend-staging \
    --region=us-central1 \
    --min-instances=0 \
    --max-instances=0
fi

# 2. Backup current state
echo "Creating backup of current state..."
redis-cli -h $REDIS_HOST --rdb /tmp/pre_recovery_backup.rdb
aws s3 cp /tmp/pre_recovery_backup.rdb s3://$BACKUP_BUCKET/recovery/

# 3. Download backup
echo "Downloading backup from $BACKUP_DATE..."
if [[ $BACKUP_DATE == "latest" ]]; then
  BACKUP_FILE=$(aws s3 ls s3://$BACKUP_BUCKET/redis/ | sort | tail -n 1 | awk '{print $4}')
else
  BACKUP_FILE="dump_$BACKUP_DATE.rdb.gz"
fi

aws s3 cp s3://$BACKUP_BUCKET/redis/$BACKUP_FILE /tmp/
gunzip /tmp/$BACKUP_FILE

# 4. Restore Redis data
echo "Restoring Redis data..."
redis-cli -h $REDIS_HOST FLUSHALL
redis-cli -h $REDIS_HOST --pipe < /tmp/${BACKUP_FILE%.gz}

# 5. Restore application instances
echo "Restoring application instances..."
if [[ $ENVIRONMENT == "production" ]]; then
  gcloud run services update webai-backend \
    --region=us-central1 \
    --min-instances=2 \
    --max-instances=100
else
  gcloud run services update webai-backend-staging \
    --region=us-central1 \
    --min-instances=0 \
    --max-instances=10
fi

# 6. Verify recovery
echo "Verifying recovery..."
sleep 60

BACKEND_URL=$(gcloud run services describe webai-backend${ENVIRONMENT:+-$ENVIRONMENT} \
  --region=us-central1 \
  --format="value(status.url)")

if curl -f "$BACKEND_URL/health"; then
  echo "✅ Recovery successful!"
else
  echo "❌ Recovery verification failed"
  exit 1
fi

echo "🎉 Database recovery completed!"
```

### Disaster Recovery Plan

#### Complete System Recovery

```bash
#!/bin/bash
# disaster-recovery.sh

RECOVERY_REGION=${1:-us-east-1}
BACKUP_DATE=${2:-latest}

echo "🚨 Starting disaster recovery procedure..."
echo "Recovery region: $RECOVERY_REGION"
echo "Backup date: $BACKUP_DATE"

# 1. Deploy infrastructure in recovery region
echo "Deploying infrastructure in recovery region..."

# Deploy Redis
aws elasticache create-replication-group \
  --replication-group-id webai-dr-redis \
  --description "WebAI Disaster Recovery Redis" \
  --num-cache-clusters 2 \
  --cache-node-type cache.r7g.large \
  --engine redis \
  --engine-version 7.0

# Deploy backend infrastructure
aws ecs create-cluster --cluster-name webai-dr

# 2. Restore data
echo "Restoring data from backups..."
./database-recovery.sh production $BACKUP_DATE

# 3. Deploy applications
echo "Deploying applications..."

# Build and deploy backend
docker build -t webai-backend-dr ./backend
docker tag webai-backend-dr:latest $AWS_ACCOUNT_ID.dkr.ecr.$RECOVERY_REGION.amazonaws.com/webai-backend-dr:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$RECOVERY_REGION.amazonaws.com/webai-backend-dr:latest

# Deploy to ECS
aws ecs create-service \
  --cluster webai-dr \
  --service-name webai-backend-dr \
  --task-definition webai-backend-dr:1 \
  --desired-count 3

# 4. Update DNS to point to recovery region
echo "Updating DNS records..."
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch file://dns-failover.json

# 5. Verify system functionality
echo "Verifying system functionality..."
sleep 120

if curl -f "https://api.yourdomain.com/health"; then
  echo "✅ Disaster recovery successful!"
  
  # Notify team
  curl -X POST "$SLACK_WEBHOOK_URL" \
    -H 'Content-type: application/json' \
    --data '{"text":"🚨 WebAI Disaster Recovery Completed Successfully"}'
else
  echo "❌ Disaster recovery failed"
  exit 1
fi

echo "🎉 System recovered and operational!"
```

This comprehensive deployment guide covers all aspects of deploying the WebAI application across different environments and platforms. It includes detailed instructions for development setup, staging deployment, production deployment options, CI/CD pipelines, database deployment, monitoring, and recovery procedures.

The documentation provides multiple deployment strategies to accommodate different infrastructure preferences and requirements, from simple Docker Compose setups for development to enterprise-grade cloud deployments with full monitoring and disaster recovery capabilities.
