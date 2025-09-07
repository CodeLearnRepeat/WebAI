import asyncio
import time
import logging
from functools import lru_cache
from typing import List, Tuple, Literal, Optional, Callable, AsyncIterator
from sentence_transformers import SentenceTransformer

from .batch_manager import VoyageBatchManager, Batch, create_batch_manager

logger = logging.getLogger(__name__)

EmbProvider = Literal["sentence_transformers", "openai", "voyageai"]

@lru_cache(maxsize=16)
def get_st_model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name)

def _embed_sentence_transformers(texts: List[str], model_name: str) -> Tuple[List[List[float]], int]:
    m = get_st_model(model_name)
    vecs = m.encode(texts, normalize_embeddings=True)
    if hasattr(vecs, "tolist"):
        vecs = vecs.tolist()
    dim = len(vecs[0]) if vecs else 0
    return vecs, dim

def _embed_openai(texts: List[str], model_name: str, api_key: str) -> Tuple[List[List[float]], int]:
    # OpenAI Python SDK v1
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    # Batched call: the SDK accepts a list input
    resp = client.embeddings.create(model=model_name, input=texts)
    vecs = [item.embedding for item in resp.data]
    dim = len(vecs[0]) if vecs else 0
    return vecs, dim

def _embed_voyage(texts: List[str], model_name: str, api_key: str, input_type: Literal["query", "document"]) -> Tuple[List[List[float]], int]:
    # VoyageAI SDK
    import voyageai as vo
    client = vo.Client(api_key=api_key)
    resp = client.embed(texts, model=model_name, input_type=input_type)
    vecs = resp.embeddings
    dim = len(vecs[0]) if vecs else 0
    return vecs, dim


class RobustVoyageEmbedder:
    """VoyageAI embedder with retry logic and error handling."""
    
    def __init__(self, api_key: str, model_name: str):
        """
        Initialize robust VoyageAI embedder.
        
        Args:
            api_key: VoyageAI API key
            model_name: VoyageAI model name
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = 3
        self.base_delay = 1.0
        
        try:
            import voyageai as vo
            self.client = vo.Client(api_key=api_key)
        except ImportError as e:
            logger.error("VoyageAI library not installed")
            raise e
    
    async def embed_with_retry(
        self,
        texts: List[str],
        input_type: str = "document"
    ) -> Tuple[List[List[float]], int]:
        """
        Embed texts with exponential backoff retry.
        
        Args:
            texts: List of texts to embed
            input_type: VoyageAI input type ("document" or "query")
            
        Returns:
            Tuple of (embeddings, dimension)
        """
        if not texts:
            return [], 0
        
        # Validate batch before sending
        self._validate_batch(texts)
        
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                resp = await asyncio.to_thread(
                    self.client.embed,
                    texts,
                    model=self.model_name,
                    input_type=input_type
                )
                
                vecs = resp.embeddings
                dim = len(vecs[0]) if vecs else 0
                return vecs, dim
                
            except Exception as e:
                error_type = type(e).__name__
                last_exception = e
                
                # Check if we should retry
                if attempt < self.max_retries and self._should_retry(e):
                    delay = min(self.base_delay * (2 ** attempt), 60.0)
                    logger.warning(
                        f"VoyageAI API error (attempt {attempt + 1}/{self.max_retries + 1}): "
                        f"{error_type}: {str(e)}. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"VoyageAI API error (final): {error_type}: {str(e)}")
                    break
        
        # All retries exhausted
        raise last_exception
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if exception should trigger a retry."""
        error_str = str(exception).lower()
        error_type = type(exception).__name__
        
        # Retry on rate limits, timeouts, and server errors
        retry_indicators = [
            "rate limit", "timeout", "503", "502", "500",
            "connection", "network", "temporary", "service unavailable",
            "too many requests", "throttled", "quota exceeded"
        ]
        
        # Don't retry on authentication or permission errors
        no_retry_indicators = [
            "unauthorized", "forbidden", "invalid key", "api key",
            "permission denied", "401", "403"
        ]
        
        # Check for no-retry conditions first
        if any(indicator in error_str for indicator in no_retry_indicators):
            return False
        
        return any(indicator in error_str for indicator in retry_indicators)
    
    async def embed_with_checkpoint_support(
        self,
        texts: List[str],
        input_type: str = "document",
        task_id: Optional[str] = None,
        checkpoint_callback: Optional[Callable] = None
    ) -> Tuple[List[List[float]], int]:
        """
        Embed texts with checkpoint support for recovery.
        
        Args:
            texts: List of texts to embed
            input_type: VoyageAI input type
            task_id: Task ID for checkpoint tracking
            checkpoint_callback: Callback for checkpoint creation
            
        Returns:
            Tuple of (embeddings, dimension)
        """
        try:
            result = await self.embed_with_retry(texts, input_type)
            
            # Create checkpoint on success if callback provided
            if checkpoint_callback and task_id:
                await checkpoint_callback(task_id, len(texts), success=True)
            
            return result
            
        except Exception as e:
            # Create error checkpoint if callback provided
            if checkpoint_callback and task_id:
                await checkpoint_callback(task_id, 0, success=False, error=str(e))
            raise
    
    def _validate_batch(self, texts: List[str]):
        """Validate batch meets VoyageAI requirements."""
        if len(texts) > 1000:
            raise ValueError(f"Batch size {len(texts)} exceeds 1000 chunk limit")
        
        # Token validation would be done by batch manager
        # This is a final safety check
        total_chars = sum(len(text) for text in texts)
        estimated_tokens = total_chars * 0.25  # Rough estimate
        
        if estimated_tokens > 10000:
            logger.warning(f"Batch may exceed 10000 token limit (estimated: {estimated_tokens:.0f})")


class BatchEmbeddingService:
    """Service for batch embedding with intelligent batching and retry logic."""
    
    def __init__(self, provider: str, model: str, api_key: Optional[str] = None):
        """
        Initialize batch embedding service.
        
        Args:
            provider: Embedding provider ("sentence_transformers", "openai", "voyageai")
            model: Model name
            api_key: API key for external providers
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        
        if provider == "voyageai":
            if not api_key:
                raise ValueError("VoyageAI requires api_key")
            self.embedder = RobustVoyageEmbedder(api_key, model)
            self.batch_manager = create_batch_manager(model)
        
        logger.info(f"Initialized {provider} embedding service with model {model}")
    
    async def embed_texts_with_batching(
        self,
        texts: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[List[List[float]], int]:
        """
        Embed texts with intelligent batching.
        
        Args:
            texts: List of texts to embed
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (all_embeddings, dimension)
        """
        if not texts:
            return [], 0
        
        if self.provider == "voyageai":
            return await self._embed_voyage_batched(texts, progress_callback)
        else:
            # For other providers, use existing logic
            return await self._embed_non_voyage(texts)
    
    async def _embed_voyage_batched(
        self,
        texts: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[List[List[float]], int]:
        """Embed texts using VoyageAI with intelligent batching."""
        all_embeddings = []
        total_texts = len(texts)
        processed_count = 0
        dimension = 0
        
        # Create batches using batch manager
        for batch in self.batch_manager.create_batches(texts):
            logger.debug(f"Processing batch: {batch.size} items, {batch.total_tokens} tokens")
            
            # Embed batch with retry logic
            batch_embeddings, dim = await self.embedder.embed_with_retry(
                batch.texts,
                input_type="document"
            )
            
            all_embeddings.extend(batch_embeddings)
            processed_count += len(batch.texts)
            
            if dimension == 0:
                dimension = dim
            
            # Progress callback
            if progress_callback:
                try:
                    progress_callback(processed_count, total_texts)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
            
            # Small delay between batches to be respectful to API
            if processed_count < total_texts:
                await asyncio.sleep(0.1)
        
        logger.info(f"Completed embedding {total_texts} texts in {self.batch_manager.stats.batches_created} batches")
        return all_embeddings, dimension
    
    async def _embed_non_voyage(self, texts: List[str]) -> Tuple[List[List[float]], int]:
        """Embed texts using non-VoyageAI providers."""
        # Use existing logic for other providers
        if self.provider == "sentence_transformers":
            return _embed_sentence_transformers(texts, self.model)
        elif self.provider == "openai":
            return _embed_openai(texts, self.model, self.api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def get_batching_stats(self) -> dict:
        """Get batching statistics if available."""
        if hasattr(self, 'batch_manager'):
            stats = self.batch_manager.get_stats()
            return {
                "batches_created": stats.batches_created,
                "total_items_processed": stats.total_items_processed,
                "total_tokens_processed": stats.total_tokens_processed,
                "avg_batch_size": stats.avg_batch_size,
                "avg_tokens_per_batch": stats.avg_tokens_per_batch
            }
        return {}

def embed_texts(
    provider: EmbProvider,
    model_name: str,
    texts: List[str],
    *,
    api_key: Optional[str] = None,
    mode: Literal["query", "document"] = "query",
    use_batching: bool = True
) -> Tuple[List[List[float]], int]:
    """
    Embed texts using specified provider with optional intelligent batching.
    
    Args:
        provider: Embedding provider
        model_name: Model name
        texts: List of texts to embed
        api_key: API key for external providers
        mode: Input type ("query" or "document")
        use_batching: Whether to use intelligent batching for VoyageAI
        
    Returns:
        Tuple of (embeddings, dimension)
    """
    if provider == "sentence_transformers":
        return _embed_sentence_transformers(texts, model_name)
    if provider == "openai":
        if not api_key:
            raise ValueError("OpenAI embedding requires api_key")
        return _embed_openai(texts, model_name, api_key)
    if provider == "voyageai":
        if not api_key:
            raise ValueError("VoyageAI embedding requires api_key")
        
        # Use batching for large inputs or when explicitly requested
        if use_batching and (len(texts) > 100 or sum(len(t) for t in texts) > 50000):
            logger.info(f"Using intelligent batching for {len(texts)} texts")
            
            # Create embedding service and run batching
            service = BatchEmbeddingService(provider, model_name, api_key)
            
            # Run async function in sync context
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If loop is already running, we need to use asyncio.create_task
                # This shouldn't happen in normal sync context, but just in case
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(service.embed_texts_with_batching(texts))
                    )
                    return future.result()
            else:
                return loop.run_until_complete(service.embed_texts_with_batching(texts))
        else:
            # Use original implementation for small batches
            return _embed_voyage(texts, model_name, api_key, input_type=mode)
    
    raise ValueError(f"Unsupported embedding provider: {provider}")


async def embed_texts_async(
    provider: EmbProvider,
    model_name: str,
    texts: List[str],
    *,
    api_key: Optional[str] = None,
    mode: Literal["query", "document"] = "query",
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[List[List[float]], int]:
    """
    Async version of embed_texts with progress callback support.
    
    Args:
        provider: Embedding provider
        model_name: Model name
        texts: List of texts to embed
        api_key: API key for external providers
        mode: Input type ("query" or "document")
        progress_callback: Optional progress callback function
        
    Returns:
        Tuple of (embeddings, dimension)
    """
    if provider == "voyageai":
        if not api_key:
            raise ValueError("VoyageAI embedding requires api_key")
        
        service = BatchEmbeddingService(provider, model_name, api_key)
        return await service.embed_texts_with_batching(texts, progress_callback)
    else:
        # For other providers, run sync version in thread
        return await asyncio.to_thread(
            embed_texts,
            provider,
            model_name,
            texts,
            api_key=api_key,
            mode=mode,
            use_batching=False
        )


def embed_query(provider: EmbProvider, model_name: str, text: str, *, api_key: Optional[str] = None) -> Tuple[List[float], int]:
    """Embed a single query text."""
    vecs, dim = embed_texts(provider, model_name, [text], api_key=api_key, mode="query", use_batching=False)
    return (vecs[0] if vecs else []), dim


async def embed_query_async(provider: EmbProvider, model_name: str, text: str, *, api_key: Optional[str] = None) -> Tuple[List[float], int]:
    """Async version of embed_query."""
    vecs, dim = await embed_texts_async(provider, model_name, [text], api_key=api_key, mode="query")
    return (vecs[0] if vecs else []), dim