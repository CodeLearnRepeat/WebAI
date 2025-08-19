# Large JSON File Processing Architecture Plan
## Intelligent Batching for VoyageAI API Integration

### Executive Summary

This document outlines a comprehensive architectural redesign for handling arbitrarily large JSON files while respecting VoyageAI's API limitations (10,000 token limit and 1,000 chunk limit per batch). The solution introduces streaming processing, intelligent batching, robust error handling, and enhanced user experience features.

**Key Goals:**
- **API Compliance**: Respect VoyageAI's 10,000 token and 1,000 chunk limits
- **Scalability**: Handle arbitrarily large JSON files without memory exhaustion
- **Reliability**: Include robust error handling, retry logic, and progress tracking
- **Performance**: Optimize throughput while staying within API limits

---

## 1. Current Architecture Analysis

### Limitations Identified
From the [`voyageai_implementation_analysis.md`](voyageai_implementation_analysis.md), the current system has critical limitations:

1. **No Batching Logic**: [`_embed_voyage()`](backend/app/services/embeddings.py:29-36) sends entire text list in single API call
2. **No Token Counting**: Character-based chunking doesn't align with token boundaries
3. **Memory Constraints**: Entire JSON files loaded into memory
4. **No Error Handling**: No retry logic or partial failure recovery
5. **Synchronous Processing**: Single-threaded, blocking operations

### Current Data Flow
```
JSON Upload → Parse/Validate → Extract Content → Chunk Text → Embed All Texts → Store in Milvus
     ↓              ↓              ↓             ↓           ↓              ↓
File Upload    JSON/NDJSON     Dot-path      Character   VoyageAI API    Vector Store
 (multipart)    parsing       extraction     splitting    (single call)   (batch insert)
```

---

## 2. Token-Aware Batching System Architecture

### 2.1 Token Counting Component

```python
# New component: backend/app/services/token_counter.py
class VoyageTokenCounter:
    """Token-aware counting for VoyageAI models"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.tokenizer = self._get_tokenizer(model_name)
    
    def count_tokens(self, text: str) -> int:
        """Count actual tokens for given text"""
        return len(self.tokenizer.encode(text))
    
    def estimate_batch_tokens(self, texts: List[str]) -> int:
        """Estimate total tokens for a batch of texts"""
        return sum(self.count_tokens(text) for text in texts)
```

### 2.2 Intelligent Batch Manager

```python
# New component: backend/app/services/batch_manager.py
class VoyageBatchManager:
    """Manages batching with VoyageAI API limits"""
    
    TOKEN_LIMIT = 9500  # Safety margin below 10,000
    CHUNK_LIMIT = 950   # Safety margin below 1,000
    
    def __init__(self, model_name: str):
        self.token_counter = VoyageTokenCounter(model_name)
        self.current_batch = []
        self.current_tokens = 0
    
    def can_add_text(self, text: str) -> bool:
        """Check if text can be added to current batch"""
        text_tokens = self.token_counter.count_tokens(text)
        return (
            len(self.current_batch) < self.CHUNK_LIMIT and
            self.current_tokens + text_tokens <= self.TOKEN_LIMIT
        )
    
    def add_text(self, text: str, metadata: dict = None) -> Optional[List[BatchItem]]:
        """Add text to batch, return completed batch if full"""
        if not self.can_add_text(text):
            # Return current batch and start new one
            completed_batch = self.get_current_batch()
            self.reset_batch()
            self.add_text(text, metadata)  # Add to new batch
            return completed_batch
        
        self.current_batch.append(BatchItem(text, metadata))
        self.current_tokens += self.token_counter.count_tokens(text)
        return None
```

### 2.3 Adaptive Batch Sizing

The system dynamically adjusts batch sizes based on content complexity:

```python
class AdaptiveBatchSizer:
    """Adapts batch sizes based on content analysis"""
    
    def __init__(self):
        self.avg_tokens_per_char = 0.25  # Initial estimate
        self.sample_count = 0
    
    def update_statistics(self, text: str, actual_tokens: int):
        """Update token/character ratio based on real data"""
        char_count = len(text)
        if char_count > 0:
            ratio = actual_tokens / char_count
            self.avg_tokens_per_char = (
                (self.avg_tokens_per_char * self.sample_count + ratio) / 
                (self.sample_count + 1)
            )
            self.sample_count += 1
    
    def estimate_batch_capacity(self, remaining_texts: List[str]) -> int:
        """Estimate how many texts can fit in next batch"""
        estimated_chars = sum(len(text) for text in remaining_texts[:100])  # Sample
        estimated_tokens = estimated_chars * self.avg_tokens_per_char
        
        if estimated_tokens <= VoyageBatchManager.TOKEN_LIMIT:
            return min(len(remaining_texts), VoyageBatchManager.CHUNK_LIMIT)
        
        # Calculate optimal batch size
        return int(VoyageBatchManager.TOKEN_LIMIT / (estimated_tokens / len(remaining_texts[:100])))
```

---

## 3. Streaming Processing Architecture

### 3.1 Streaming JSON Parser

```python
# New component: backend/app/services/streaming_parser.py
class StreamingJSONProcessor:
    """Memory-efficient streaming JSON processing"""
    
    def __init__(self, file_stream: IO, schema_config: dict):
        self.file_stream = file_stream
        self.schema_config = schema_config
        self.format = schema_config.get("format", "json_array")
        
    async def process_stream(self) -> AsyncIterator[ProcessedItem]:
        """Stream process JSON without loading entire file"""
        if self.format == "json_array":
            async for item in self._stream_json_array():
                yield await self._process_item(item)
        else:  # ndjson
            async for item in self._stream_ndjson():
                yield await self._process_item(item)
    
    async def _stream_json_array(self) -> AsyncIterator[dict]:
        """Stream parse JSON array incrementally"""
        parser = ijson.parse(self.file_stream)
        current_item = {}
        item_stack = []
        
        for prefix, event, value in parser:
            if event == 'start_array' and prefix == '':
                continue  # Root array
            elif event == 'start_map':
                # New item starting
                if prefix.count('.') == 0:  # Top-level item
                    current_item = {}
            elif event == 'end_map':
                if prefix.count('.') == 0:  # Top-level item complete
                    yield current_item
                    current_item = {}
            else:
                # Build current item
                self._set_nested_value(current_item, prefix, value)
```

### 3.2 Background Processing Pipeline

```python
# New component: backend/app/services/background_processor.py
class BackgroundFileProcessor:
    """Handles long-running file processing in background"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.task_queue = asyncio.Queue()
        
    async def start_processing_task(
        self, 
        task_id: str,
        file_path: str, 
        tenant_id: str, 
        schema_config: dict
    ) -> str:
        """Start background processing task"""
        task_data = {
            "task_id": task_id,
            "status": "queued",
            "file_path": file_path,
            "tenant_id": tenant_id,
            "schema_config": schema_config,
            "progress": {
                "items_processed": 0,
                "items_total": None,
                "chunks_processed": 0,
                "embeddings_generated": 0,
                "current_phase": "initializing",
                "start_time": time.time(),
                "estimated_completion": None
            }
        }
        
        # Store task metadata in Redis
        await self.redis.setex(
            f"processing_task:{task_id}", 
            3600 * 24,  # 24 hour TTL
            json.dumps(task_data)
        )
        
        # Queue for processing
        await self.task_queue.put(task_data)
        
        return task_id
    
    async def process_file_background(self, task_data: dict):
        """Background file processing with progress updates"""
        task_id = task_data["task_id"]
        
        try:
            await self._update_progress(task_id, {"current_phase": "parsing"})
            
            # Stream process file
            async with aiofiles.open(task_data["file_path"], 'rb') as file:
                processor = StreamingJSONProcessor(file, task_data["schema_config"])
                batch_manager = VoyageBatchManager(task_data["embedding_model"])
                
                items_processed = 0
                async for item in processor.process_stream():
                    # Add to batch
                    completed_batch = batch_manager.add_text(item.text, item.metadata)
                    
                    if completed_batch:
                        # Process completed batch
                        await self._process_batch(task_id, completed_batch)
                        
                    items_processed += 1
                    if items_processed % 100 == 0:
                        await self._update_progress(task_id, {
                            "items_processed": items_processed,
                            "current_phase": "processing"
                        })
                
                # Process final batch
                final_batch = batch_manager.get_current_batch()
                if final_batch:
                    await self._process_batch(task_id, final_batch)
                    
            await self._update_progress(task_id, {
                "status": "completed",
                "current_phase": "finished"
            })
            
        except Exception as e:
            await self._update_progress(task_id, {
                "status": "failed",
                "error": str(e),
                "current_phase": "error"
            })
```

---

## 4. Enhanced Error Handling & Recovery

### 4.1 Retry Logic with Exponential Backoff

```python
# Enhanced: backend/app/services/embeddings.py
class RobustVoyageEmbedder:
    """VoyageAI embedder with retry logic and error handling"""
    
    def __init__(self, api_key: str, model_name: str):
        self.client = voyageai.Client(api_key=api_key)
        self.model_name = model_name
        self.max_retries = 3
        self.base_delay = 1.0
        
    async def embed_with_retry(
        self, 
        texts: List[str], 
        input_type: str = "document"
    ) -> Tuple[List[List[float]], int]:
        """Embed texts with exponential backoff retry"""
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Validate batch before sending
                self._validate_batch(texts)
                
                resp = await asyncio.to_thread(
                    self.client.embed,
                    texts,
                    model=self.model_name,
                    input_type=input_type
                )
                
                vecs = resp.embeddings
                dim = len(vecs[0]) if vecs else 0
                return vecs, dim
                
            except voyageai.RateLimitError as e:
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                raise
                
            except voyageai.APIError as e:
                if e.status_code >= 500 and attempt < self.max_retries:
                    # Server error, retry
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                raise
                
            except Exception as e:
                # Unexpected error, don't retry
                raise
        
        # All retries exhausted
        raise last_exception
    
    def _validate_batch(self, texts: List[str]):
        """Validate batch meets VoyageAI requirements"""
        if len(texts) > 1000:
            raise ValueError(f"Batch size {len(texts)} exceeds 1000 chunk limit")
        
        total_tokens = sum(self._count_tokens(text) for text in texts)
        if total_tokens > 10000:
            raise ValueError(f"Batch tokens {total_tokens} exceeds 10000 token limit")
```

### 4.2 Partial Failure Recovery

```python
class ProcessingStateManager:
    """Manages processing state for recovery"""
    
    def __init__(self, redis_client, task_id: str):
        self.redis = redis_client
        self.task_id = task_id
        self.checkpoint_interval = 100  # Save state every 100 items
        
    async def save_checkpoint(self, state: dict):
        """Save processing checkpoint"""
        checkpoint_key = f"checkpoint:{self.task_id}"
        await self.redis.setex(
            checkpoint_key,
            3600 * 48,  # 48 hour TTL
            json.dumps(state)
        )
    
    async def load_checkpoint(self) -> Optional[dict]:
        """Load last processing checkpoint"""
        checkpoint_key = f"checkpoint:{self.task_id}"
        data = await self.redis.get(checkpoint_key)
        return json.loads(data) if data else None
    
    async def resume_from_checkpoint(self, file_path: str, schema_config: dict):
        """Resume processing from last checkpoint"""
        checkpoint = await self.load_checkpoint()
        if not checkpoint:
            return await self.start_fresh_processing(file_path, schema_config)
        
        # Resume from checkpoint
        last_processed_offset = checkpoint.get("file_offset", 0)
        processed_count = checkpoint.get("items_processed", 0)
        
        async with aiofiles.open(file_path, 'rb') as file:
            await file.seek(last_processed_offset)
            # Continue processing from offset...
```

---

## 5. API Integration Improvements

### 5.1 Rate Limiting and Throttling

```python
# New component: backend/app/services/rate_limiter.py
class VoyageRateLimiter:
    """Rate limiter for VoyageAI API calls"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire rate limit permission"""
        async with self.lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            
            # Check if we can make request
            if len(self.request_times) >= self.requests_per_minute:
                # Calculate wait time
                oldest_request = self.request_times[0]
                wait_time = 60 - (now - oldest_request)
                await asyncio.sleep(wait_time)
                return await self.acquire()  # Recursive call after wait
            
            # Record this request
            self.request_times.append(now)
```

### 5.2 Enhanced Embedding Service

```python
# Enhanced: backend/app/services/embeddings.py
class BatchEmbeddingService:
    """Service for batch embedding with all enhancements"""
    
    def __init__(self, provider: str, model: str, api_key: str = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        
        if provider == "voyageai":
            self.embedder = RobustVoyageEmbedder(api_key, model)
            self.rate_limiter = VoyageRateLimiter()
            self.batch_manager = VoyageBatchManager(model)
    
    async def embed_texts_with_batching(
        self, 
        texts: List[str], 
        progress_callback: Optional[Callable] = None
    ) -> Tuple[List[List[float]], int]:
        """Embed texts with intelligent batching"""
        
        all_embeddings = []
        total_texts = len(texts)
        processed_count = 0
        
        # Process in batches
        for batch in self.batch_manager.create_batches(texts):
            # Rate limiting
            await self.rate_limiter.acquire()
            
            # Embed batch
            batch_embeddings, dim = await self.embedder.embed_with_retry(
                batch.texts, 
                input_type="document"
            )
            
            all_embeddings.extend(batch_embeddings)
            processed_count += len(batch.texts)
            
            # Progress callback
            if progress_callback:
                await progress_callback(processed_count, total_texts)
        
        return all_embeddings, dim
```

---

## 6. User Experience Enhancements

### 6.1 Real-time Progress Updates

```python
# New API endpoint: backend/app/api/routes/rag.py
@router.get("/rag/processing-status/{task_id}")
async def get_processing_status(task_id: str, x_tenant_id: str = Header(None)):
    """Get real-time processing status"""
    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID required")
    
    # Get task data from Redis
    task_data = await redis_client.get(f"processing_task:{task_id}")
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = json.loads(task_data)
    
    # Calculate progress metrics
    progress = task.get("progress", {})
    items_processed = progress.get("items_processed", 0)
    items_total = progress.get("items_total")
    
    response = {
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "current_phase": progress.get("current_phase", "unknown"),
        "progress": {
            "items_processed": items_processed,
            "items_total": items_total,
            "percentage": (items_processed / items_total * 100) if items_total else None,
            "chunks_processed": progress.get("chunks_processed", 0),
            "embeddings_generated": progress.get("embeddings_generated", 0),
        },
        "timing": {
            "start_time": progress.get("start_time"),
            "estimated_completion": progress.get("estimated_completion"),
            "elapsed_time": time.time() - progress.get("start_time", time.time())
        }
    }
    
    if task.get("status") == "failed":
        response["error"] = task.get("error")
    
    return response

@router.post("/rag/pause-processing/{task_id}")
async def pause_processing(task_id: str, x_tenant_id: str = Header(None)):
    """Pause processing task"""
    # Implementation for pausing background tasks
    await background_processor.pause_task(task_id)
    return {"status": "paused"}

@router.post("/rag/resume-processing/{task_id}")
async def resume_processing(task_id: str, x_tenant_id: str = Header(None)):
    """Resume paused processing task"""
    await background_processor.resume_task(task_id)
    return {"status": "resumed"}
```

### 6.2 Enhanced File Upload Endpoint

```python
@router.post("/rag/ingest-file-async")
async def rag_ingest_file_async(
    x_tenant_id: str = Header(None),
    file: UploadFile = File(...),
    schema_json: str = Form(...),
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Async file ingestion for large files"""
    
    # Validation logic (same as before)...
    
    # Generate task ID
    task_id = f"ingest_{uuid.uuid4().hex}"
    
    # Save uploaded file temporarily
    temp_file_path = f"/tmp/{task_id}_{file.filename}"
    async with aiofiles.open(temp_file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Start background processing
    await background_processor.start_processing_task(
        task_id=task_id,
        file_path=temp_file_path,
        tenant_id=x_tenant_id,
        schema_config=schema,
        embedding_provider=emb_provider,
        embedding_model=emb_model
    )
    
    return {
        "task_id": task_id,
        "status": "processing_started",
        "message": "File processing started in background",
        "status_endpoint": f"/rag/processing-status/{task_id}"
    }
```

---

## 7. System Architecture Diagrams

### 7.1 High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   File Upload   │───▶│  Async Processor │───▶│  Progress API   │
│    (Frontend)   │    │    (Background)  │    │   (Real-time)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Streaming JSON  │───▶│ Token-Aware      │───▶│ VoyageAI API    │
│    Parser       │    │ Batch Manager    │    │ (Rate Limited)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Error Recovery  │◀───│ Checkpoint       │───▶│ Milvus Vector   │
│   & Retry       │    │   Manager        │    │     Store       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### 7.2 Processing Pipeline Flow

```
Input JSON File
        │
        ▼
┌───────────────┐
│ File Stream   │ ──┐
│ (Memory-safe) │   │
└───────────────┘   │
        │           │
        ▼           │
┌───────────────┐   │    ┌─────────────────┐
│ JSON Parser   │   │    │ Progress        │
│ (Incremental) │───┼───▶│ Tracking        │
└───────────────┘   │    │ (Redis)         │
        │           │    └─────────────────┘
        ▼           │
┌───────────────┐   │    ┌─────────────────┐
│ Content       │   │    │ Checkpoint      │
│ Extraction    │───┼───▶│ Management      │
└───────────────┘   │    │ (Recovery)      │
        │           │    └─────────────────┘
        ▼           │
┌───────────────┐   │
│ Token-Aware   │   │
│ Chunking      │───┘
└───────────────┘
        │
        ▼
┌───────────────┐    ┌─────────────────┐
│ Batch Manager │───▶│ VoyageAI API    │
│ (Smart Queue) │    │ (Rate Limited)  │
└───────────────┘    └─────────────────┘
        │                      │
        ▼                      ▼
┌───────────────┐    ┌─────────────────┐
│ Retry Logic   │◀───│ Error Handling  │
│ (Exponential  │    │ (Partial Fails) │
│  Backoff)     │    └─────────────────┘
└───────────────┘
        │
        ▼
┌───────────────┐
│ Milvus        │
│ Vector Store  │
└───────────────┘
```

---

## 8. Database Schema Changes

### 8.1 Processing Tasks Table (Redis)

```json
{
  "processing_task:{task_id}": {
    "task_id": "string",
    "tenant_id": "string",
    "status": "queued|processing|paused|completed|failed",
    "file_info": {
      "filename": "string",
      "size_bytes": "number",
      "temp_path": "string"
    },
    "configuration": {
      "schema_config": "object",
      "embedding_provider": "string",
      "embedding_model": "string"
    },
    "progress": {
      "items_processed": "number",
      "items_total": "number|null",
      "chunks_processed": "number",
      "embeddings_generated": "number",
      "current_phase": "string",
      "start_time": "timestamp",
      "estimated_completion": "timestamp|null",
      "last_checkpoint": "timestamp"
    },
    "error_info": {
      "error_message": "string|null",
      "failed_batch_info": "object|null",
      "retry_count": "number"
    },
    "created_at": "timestamp",
    "updated_at": "timestamp"
  }
}
```

### 8.2 Processing Checkpoints (Redis)

```json
{
  "checkpoint:{task_id}": {
    "task_id": "string",
    "file_offset": "number",
    "items_processed": "number",
    "chunks_processed": "number",
    "last_successful_batch": "object",
    "processing_state": "object",
    "created_at": "timestamp"
  }
}
```

### 8.3 Rate Limiting State (Redis)

```json
{
  "rate_limit:voyageai:{tenant_id}": {
    "requests_made": "number",
    "window_start": "timestamp",
    "tokens_used": "number",
    "last_request": "timestamp"
  }
}
```

---

## 9. Implementation Strategy & Phases

### Phase 1: Core Batching Infrastructure (2-3 weeks)
**Priority**: Critical foundation

**Components:**
1. **Token Counter Service**
   - Implement [`VoyageTokenCounter`](backend/app/services/token_counter.py)
   - Add tokenizer integration for VoyageAI models
   - Unit tests for token counting accuracy

2. **Batch Manager**
   - Implement [`VoyageBatchManager`](backend/app/services/batch_manager.py)
   - Dynamic batch sizing with safety margins
   - Adaptive sizing based on content analysis

3. **Enhanced Embedding Service**
   - Modify [`backend/app/services/embeddings.py`](backend/app/services/embeddings.py)
   - Add retry logic with exponential backoff
   - Implement rate limiting

**Deliverables:**
- Working batch processing for VoyageAI API
- Token-aware chunking system
- Basic retry mechanism

**Success Criteria:**
- Process files up to 10,000 tokens without API errors
- Automatic batch splitting for larger files
- 95% success rate with retry logic

### Phase 2: Streaming Processing (3-4 weeks)
**Priority**: High - enables large file processing

**Components:**
1. **Streaming JSON Parser**
   - Implement [`StreamingJSONProcessor`](backend/app/services/streaming_parser.py)
   - Memory-efficient parsing for JSON arrays and NDJSON
   - Incremental content extraction

2. **Background Processing Framework**
   - Implement [`BackgroundFileProcessor`](backend/app/services/background_processor.py)
   - Async task management with Redis
   - Progress tracking and updates

3. **Enhanced API Endpoints**
   - New async ingestion endpoint
   - Progress monitoring API
   - Pause/resume functionality

**Deliverables:**
- Stream processing for arbitrarily large JSON files
- Background task management
- Real-time progress monitoring

**Success Criteria:**
- Process 100MB+ JSON files without memory issues
- Background processing with <1% memory growth
- Real-time progress updates within 5 seconds

### Phase 3: Error Handling & Recovery (2-3 weeks)
**Priority**: High - ensures reliability

**Components:**
1. **Checkpoint Management**
   - Implement [`ProcessingStateManager`](backend/app/services/checkpoint_manager.py)
   - Automatic checkpoint creation
   - Recovery from partial failures

2. **Advanced Error Handling**
   - Comprehensive error classification
   - Partial batch recovery
   - Failed item isolation and retry

3. **Monitoring & Alerting**
   - Processing health metrics
   - Error rate monitoring
   - Admin notification system

**Deliverables:**
- Robust error recovery system
- Checkpoint-based resumption
- Comprehensive error monitoring

**Success Criteria:**
- 99.9% recovery rate from partial failures
- Resume processing within 30 seconds of restart
- Zero data loss during error recovery

### Phase 4: Performance Optimization (2-3 weeks)
**Priority**: Medium - optimization and scalability

**Components:**
1. **Advanced Rate Limiting**
   - Tenant-specific rate limits
   - Dynamic rate adjustment
   - Queue management optimization

2. **Caching Layer**
   - Embedding result caching
   - Tokenization result caching
   - Metadata extraction caching

3. **Parallel Processing**
   - Concurrent batch processing
   - Worker pool management
   - Load balancing across tenants

**Deliverables:**
- Optimized throughput performance
- Intelligent caching system
- Scalable concurrent processing

**Success Criteria:**
- 50% improvement in processing speed
- 90% cache hit rate for repeated content
- Support for 10+ concurrent large file uploads

### Phase 5: User Experience & Management (2 weeks)
**Priority**: Medium - enhanced usability

**Components:**
1. **Enhanced Progress UI**
   - Detailed progress visualization
   - Processing phase indicators
   - Time estimation accuracy

2. **File Management**
   - Processing history
   - Failed upload recovery
   - Bulk file management

3. **Admin Dashboard**
   - System health monitoring
   - Processing statistics
   - Resource usage tracking

**Deliverables:**
- Complete user interface enhancements
- Administrative monitoring tools
- Processing management features

**Success Criteria:**
- <5 second UI update latency
- 95% accuracy in time estimates
- Complete processing visibility for admins

---

## 10. Testing Approach for Large Files

### 10.1 Test Data Strategy

**Small Test Files (< 1MB)**
- Validate basic functionality
- Unit test individual components
- Fast iteration during development

**Medium Test Files (1-50MB)**
- Integration testing
- Performance baseline establishment
- Error handling validation

**Large Test Files (50MB-1GB)**
- Stress testing
- Memory usage validation
- Long-running process testing

**Synthetic Test Generation**
```python
# Test data generator
class TestDataGenerator:
    """Generate synthetic JSON files for testing"""
    
    def generate_large_json(
        self, 
        target_size_mb: int, 
        items_per_mb: int = 1000
    ) -> str:
        """Generate large JSON file with specified characteristics"""
        total_items = target_size_mb * items_per_mb
        
        items = []
        for i in range(total_items):
            item = {
                "id": f"item_{i:08d}",
                "content": self._generate_content(1000),  # ~1KB content
                "metadata": {
                    "category": f"category_{i % 10}",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "tags": [f"tag_{j}" for j in range(i % 5)]
                }
            }
            items.append(item)
        
        return json.dumps(items, indent=2)
```

### 10.2 Performance Test Suite

```python
# Performance testing framework
class PerformanceTestSuite:
    """Comprehensive performance testing for large file processing"""
    
    async def test_memory_usage(self, file_size_mb: int):
        """Test memory usage remains constant during processing"""
        initial_memory = psutil.Process().memory_info().rss
        
        # Process large file
        await self.process_test_file(file_size_mb)
        
        final_memory = psutil.Process().memory_info().rss
        memory_growth = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        assert memory_growth < 100, f"Memory grew by {memory_growth}MB"
    
    async def test_processing_time_scaling(self):
        """Test that processing time scales linearly with file size"""
        file_sizes = [1, 5, 10, 25, 50]  # MB
        processing_times = []
        
        for size in file_sizes:
            start_time = time.time()
            await self.process_test_file(size)
            end_time = time.time()
            processing_times.append(end_time - start_time)
        
        # Verify linear scaling (with some tolerance)
        time_per_mb = [t/s for t, s in zip(processing_times, file_sizes)]
        avg_time_per_mb = sum(time_per_mb) / len(time_per_mb)
        
        for time_per_mb_value in time_per_mb:
            assert abs(time_per_mb_value - avg_time_per_mb) / avg_time_per_mb < 0.5
    
    async def test_error_recovery(self):
        """Test recovery from various error conditions"""
        # Test API timeout recovery
        with mock.patch('voyageai.Client.embed', side_effect=TimeoutError):
            with pytest.raises(TimeoutError):
                await self.process_test_file(1)
        
        # Verify processing can resume
        result = await self.process_test_file(1)
        assert result["status"] == "completed"
```

### 10.3 Load Testing

```python
class LoadTestFramework:
    """Load testing for concurrent file processing"""
    
    async def test_concurrent_processing(self, num_concurrent: int = 10):
        """Test processing multiple large files concurrently"""
        tasks = []
        
        for i in range(num_concurrent):
            task = asyncio.create_task(
                self.process_test_file(
                    size_mb=10,
                    task_id=f"load_test_{i}"
                )
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert result["status"] == "completed"
```

---

## 11. Configuration Management

### 11.1 Enhanced Configuration Schema

```python
# Enhanced: backend/app/core/config.py
class VoyageAIBatchingSettings(BaseSettings):
    """Configuration for VoyageAI batching system"""
    
    # API Limits
    VOYAGE_TOKEN_LIMIT: int = 9500  # Safety margin
    VOYAGE_CHUNK_LIMIT: int = 950   # Safety margin
    VOYAGE_RATE_LIMIT_RPM: int = 60  # Requests per minute
    
    # Processing Settings
    MAX_FILE_SIZE_MB: int = 1000
    CHECKPOINT_INTERVAL: int = 100  # Items between checkpoints
    PROGRESS_UPDATE_INTERVAL: int = 10  # Seconds between progress updates
    
    # Memory Management
    MAX_MEMORY_MB: int = 512  # Maximum memory per processing task
    BATCH_QUEUE_SIZE: int = 1000  # Maximum batches in memory
    
    # Retry Settings
    MAX_RETRIES: int = 3
    RETRY_BASE_DELAY: float = 1.0
    RETRY_MAX_DELAY: float = 60.0
    
    # Background Processing
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT_HOURS: int = 24
    CLEANUP_INTERVAL_HOURS: int = 1
    
    # Redis Configuration
    PROCESSING_TASK_TTL: int = 86400 * 2  # 2 days
    CHECKPOINT_TTL: int = 86400 * 7  # 7 days
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
```

### 11.2 Tenant-Specific Configuration

```python
# Enhanced tenant configuration
{
  "rag": {
    "enabled": true,
    "provider": "milvus",
    "milvus": { /* existing config */ },
    "embedding_provider": "voyageai",
    "embedding_model": "voyage-large-2",
    "provider_keys": {
      "voyageai": "your-api-key"
    },
    "batching": {
      "enabled": true,
      "token_limit": 9500,
      "chunk_limit": 950,
      "rate_limit_rpm": 60,
      "max_file_size_mb": 500,
      "background_processing": true,
      "checkpoint_enabled": true
    },
    "chunking": {
      "strategy": "token_aware",
      "max_tokens": 1000,
      "overlap_tokens": 100,
      "fallback_max_chars": 1200,
      "fallback_overlap": 150
    }
  }
}
```

---

## 12. Monitoring & Observability

### 12.1 Metrics Collection

```python
# New component: backend/app/services/metrics.py
class ProcessingMetrics:
    """Metrics collection for file processing"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def record_processing_start(self, task_id: str, file_size: int):
        """Record processing start metrics"""
        await self.redis.hincrby("metrics:processing", "tasks_started", 1)
        await self.redis.hincrby("metrics:file_sizes", "total_bytes", file_size)
    
    async def record_batch_processed(
        self, 
        task_id: str, 
        batch_size: int, 
        tokens_used: int,
        processing_time: float
    ):
        """Record batch processing metrics"""
        await self.redis.hincrby("metrics:batches", "total_processed", 1)
        await self.redis.hincrby("metrics:batches", "total_chunks", batch_size)
        await self.redis.hincrby("metrics:tokens", "total_used", tokens_used)
        
        # Track average processing time
        await self.redis.lpush(
            "metrics:processing_times", 
            processing_time,
            # Keep only last 1000 measurements
        )
        await self.redis.ltrim("metrics:processing_times", 0, 999)
    
    async def record_error(self, task_id: str, error_type: str, error_message: str):
        """Record error metrics"""
        await self.redis.hincrby("metrics:errors", error_type, 1)
        
        # Store error details for analysis
        error_data = {
            "task_id": task_id,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": time.time()
        }
        await self.redis.lpush("metrics:error_log", json.dumps(error_data))
        await self.redis.ltrim("metrics:error_log", 0, 999)
```

### 12.2 Health Check Endpoints

```python
# New endpoints: backend/app/api/routes/health.py
@router.get("/health/processing")
async def processing_health():
    """Health check for processing system"""
    metrics = ProcessingMetrics(redis_client)
    
    # Get current processing load
    active_tasks = await redis_client.keys("processing_task:*")
    processing_tasks = []
    
    for task_key in active_tasks:
        task_data = await redis_client.get(task_key)
        if task_data:
            task = json.loads(task_data)
            if task.get("status") in ["processing", "queued"]:
                processing_tasks.append(task["task_id"])
    
    # Get error rates
    error_counts = await redis_client.hgetall("metrics:errors")
    total_errors = sum(int(count) for count in error_counts.values())
    
    # Get performance metrics
    processing_times = await redis_client.lrange("metrics:processing_times", 0, -1)
    avg_processing_time = (
        sum(float(t) for t in processing_times) / len(processing_times) 
        if processing_times else 0
    )
    
    return {
        "status": "healthy" if len(processing_tasks) < MAX_CONCURRENT_TASKS else "degraded",
        "active_tasks": len(processing_tasks),
        "max_concurrent_tasks": MAX_CONCURRENT_TASKS,
        "error_rate": {
            "total_errors": total_errors,
            "error_types": error_counts
        },
        "performance": {
            "avg_processing_time_seconds": avg_processing_time,
            "samples": len(processing_times)
        }
    }
```

---

## 13. Security Considerations

### 13.1 File Upload Security

```python
class SecureFileHandler:
    """Secure handling of uploaded files"""
    
    ALLOWED_EXTENSIONS = {'.json', '.jsonl', '.ndjson', '.gz'}
    MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1GB
    
    def validate_file(self, file: UploadFile) -> bool:
        """Validate uploaded file security"""
        # Check file extension
        if not any(file.filename.endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            raise SecurityError("File type not allowed")
        
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise SecurityError("File too large")
        
        # Validate filename
        if any(char in file.filename for char in ['..', '/', '\\']):
            raise SecurityError("Invalid filename")
        
        return True
    
    async def secure_temp_storage(self, file: UploadFile, task_id: str) -> str:
        """Store file securely in temporary location"""
        safe_filename = f"{task_id}_{uuid.uuid4().hex}.json"
        temp_path = Path("/secure/temp") / safe_filename
        
        # Ensure temp directory exists and has correct permissions
        temp_path.parent.mkdir(mode=0o700, exist_ok=True)
        
        # Write file with restricted permissions
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Set file permissions
        os.chmod(temp_path, 0o600)
        
        return str(temp_path)
```

### 13.2 API Key Management

```python
class APIKeyManager:
    """Secure API key management for VoyageAI"""
    
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for storage"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    def validate_api_key_permissions(self, api_key: str) -> bool:
        """Validate API key has required permissions"""
        # This would integrate with VoyageAI's API to check permissions
        # For now, return True if key format is valid
        return len(api_key) > 10 and api_key.startswith('pa-')
```

---

## 14. Conclusion

This comprehensive architecture plan addresses all the limitations identified in the current VoyageAI implementation while providing a robust, scalable solution for processing arbitrarily large JSON files. The design introduces:

### Key Innovations
1. **Token-Aware Batching**: Eliminates API limit violations through intelligent batch management
2. **Streaming Architecture**: Enables processing of files larger than available memory
3. **Robust Error Handling**: Ensures reliable processing with comprehensive recovery mechanisms
4. **Enhanced User Experience**: Provides real-time progress tracking and management capabilities

### Implementation Benefits
- **Zero API Failures**: Intelligent batching ensures all requests stay within VoyageAI limits
- **Unlimited File Size**: Streaming processing removes memory constraints
- **High Reliability**: Checkpoint-based recovery ensures no data loss
- **Excellent UX**: Real-time progress tracking and pause/resume capabilities
- **Production Ready**: Comprehensive monitoring, security, and error handling

### Risk Mitigation
- **Gradual Implementation**: Phased approach allows for incremental testing and validation
- **Backward Compatibility**: New system can coexist with current implementation
- **Comprehensive Testing**: Multi-tier testing approach validates all scenarios
- **Monitoring**: Real-time observability ensures early issue detection

The architecture is designed to be implemented incrementally, allowing for continuous validation and refinement while maintaining system stability. Each phase delivers tangible value and can be deployed independently, reducing implementation risk and enabling faster time-to-value.