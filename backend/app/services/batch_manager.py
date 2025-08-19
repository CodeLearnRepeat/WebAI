"""
Intelligent batch manager for VoyageAI API with token and chunk limits.
Manages batching with safety margins and adaptive sizing.
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Iterator, AsyncIterator
from dataclasses import dataclass, field
from collections import deque

from .token_counter import VoyageTokenCounter, AdaptiveBatchSizer
from .streaming_parser import ProcessedItem

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Individual item in a batch."""
    text: str
    metadata: Dict[str, Any]
    source_index: int
    chunk_index: int
    estimated_tokens: int = 0


@dataclass 
class Batch:
    """Container for a complete batch ready for API processing."""
    items: List[BatchItem]
    total_tokens: int
    batch_id: str
    created_at: float = field(default_factory=time.time)
    
    @property
    def texts(self) -> List[str]:
        """Get list of texts from batch items."""
        return [item.text for item in self.items]
    
    @property
    def metadatas(self) -> List[Dict[str, Any]]:
        """Get list of metadata from batch items."""
        return [item.metadata for item in self.items]
    
    @property
    def size(self) -> int:
        """Get number of items in batch."""
        return len(self.items)


@dataclass
class BatchingStats:
    """Statistics for batch processing."""
    batches_created: int = 0
    total_items_processed: int = 0
    total_tokens_processed: int = 0
    avg_batch_size: float = 0.0
    avg_tokens_per_batch: float = 0.0
    processing_start_time: float = field(default_factory=time.time)


class VoyageBatchManager:
    """Manages batching with VoyageAI API limits and intelligent optimization."""
    
    # API limits with safety margins
    TOKEN_LIMIT = 9500  # Safety margin below 10,000
    CHUNK_LIMIT = 950   # Safety margin below 1,000
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize batch manager for VoyageAI model.
        
        Args:
            model_name: VoyageAI model name (e.g., "voyage-large-2")
            config: Optional configuration overrides
        """
        self.model_name = model_name
        self.token_counter = VoyageTokenCounter(model_name)
        self.adaptive_sizer = AdaptiveBatchSizer()
        
        # Apply configuration overrides
        if config:
            self.TOKEN_LIMIT = config.get("token_limit", self.TOKEN_LIMIT)
            self.CHUNK_LIMIT = config.get("chunk_limit", self.CHUNK_LIMIT)
        
        # Current batch state
        self.current_batch: List[BatchItem] = []
        self.current_tokens = 0
        self.batch_counter = 0
        
        # Statistics
        self.stats = BatchingStats()
        
        logger.info(
            f"Initialized batch manager for {model_name} with limits: "
            f"{self.TOKEN_LIMIT} tokens, {self.CHUNK_LIMIT} chunks"
        )
    
    def can_add_item(self, text: str) -> bool:
        """
        Check if text can be added to current batch.
        
        Args:
            text: Text to check
            
        Returns:
            True if text can be added without exceeding limits
        """
        if not text.strip():
            return False
        
        # Check chunk limit
        if len(self.current_batch) >= self.CHUNK_LIMIT:
            return False
        
        # Check token limit
        text_tokens = self.token_counter.count_tokens(text)
        if self.current_tokens + text_tokens > self.TOKEN_LIMIT:
            return False
        
        return True
    
    def add_item(
        self, 
        text: str, 
        metadata: Dict[str, Any], 
        source_index: int = 0,
        chunk_index: int = 0
    ) -> Optional[Batch]:
        """
        Add item to current batch. Returns completed batch if full.
        
        Args:
            text: Text content
            metadata: Associated metadata
            source_index: Index in source data
            chunk_index: Index within source item chunks
            
        Returns:
            Completed batch if current batch is full, None otherwise
        """
        if not text.strip():
            return None
        
        # Count tokens for this text
        text_tokens = self.token_counter.count_tokens(text)
        
        # Update adaptive sizer statistics
        self.adaptive_sizer.update_statistics(text, text_tokens)
        
        # Check if we need to complete current batch
        if not self.can_add_item(text):
            completed_batch = self._complete_current_batch()
            # Start new batch with this item
            self._add_to_current_batch(text, metadata, source_index, chunk_index, text_tokens)
            return completed_batch
        
        # Add to current batch
        self._add_to_current_batch(text, metadata, source_index, chunk_index, text_tokens)
        return None
    
    def add_processed_item(self, item: ProcessedItem) -> Optional[Batch]:
        """
        Add ProcessedItem to batch.
        
        Args:
            item: ProcessedItem from streaming parser
            
        Returns:
            Completed batch if current batch is full, None otherwise
        """
        return self.add_item(
            text=item.text,
            metadata=item.metadata,
            source_index=item.source_index,
            chunk_index=item.chunk_index
        )
    
    def _add_to_current_batch(
        self, 
        text: str, 
        metadata: Dict[str, Any], 
        source_index: int,
        chunk_index: int,
        text_tokens: int
    ):
        """Add item to current batch without validation."""
        batch_item = BatchItem(
            text=text,
            metadata=metadata,
            source_index=source_index,
            chunk_index=chunk_index,
            estimated_tokens=text_tokens
        )
        
        self.current_batch.append(batch_item)
        self.current_tokens += text_tokens
        self.stats.total_items_processed += 1
    
    def _complete_current_batch(self) -> Optional[Batch]:
        """Complete and return current batch."""
        if not self.current_batch:
            return None
        
        # Validate batch before completion
        actual_tokens = self.token_counter.estimate_batch_tokens([item.text for item in self.current_batch])
        
        batch = Batch(
            items=self.current_batch.copy(),
            total_tokens=actual_tokens,
            batch_id=f"batch_{self.batch_counter:06d}"
        )
        
        # Update statistics
        self.stats.batches_created += 1
        self.stats.total_tokens_processed += actual_tokens
        self._update_avg_stats()
        
        # Reset current batch
        self.current_batch = []
        self.current_tokens = 0
        self.batch_counter += 1
        
        logger.debug(
            f"Completed batch {batch.batch_id}: {batch.size} items, "
            f"{batch.total_tokens} tokens"
        )
        
        return batch
    
    def get_current_batch(self) -> Optional[Batch]:
        """Get current batch without completing it."""
        return self._complete_current_batch()
    
    def finalize_batches(self) -> Optional[Batch]:
        """Finalize processing and return any remaining batch."""
        return self._complete_current_batch()
    
    def create_batches(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> Iterator[Batch]:
        """
        Create batches from list of texts (convenience method).
        
        Args:
            texts: List of text strings
            metadatas: Optional list of metadata dicts
            
        Yields:
            Batch: Completed batches
        """
        if metadatas is None:
            metadatas = [{}] * len(texts)
        
        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            completed_batch = self.add_item(text, metadata, source_index=i)
            if completed_batch:
                yield completed_batch
        
        # Yield final batch if any
        final_batch = self.finalize_batches()
        if final_batch:
            yield final_batch
    
    def estimate_batches_needed(self, texts: List[str]) -> int:
        """
        Estimate number of batches needed for list of texts.
        
        Args:
            texts: List of texts to batch
            
        Returns:
            Estimated number of batches
        """
        if not texts:
            return 0
        
        # Use adaptive sizer for estimation
        estimated_capacity = self.adaptive_sizer.estimate_batch_capacity(
            texts, self.TOKEN_LIMIT, self.CHUNK_LIMIT
        )
        
        if estimated_capacity <= 0:
            estimated_capacity = 1
        
        return max(1, (len(texts) + estimated_capacity - 1) // estimated_capacity)
    
    def validate_batch(self, batch: Batch) -> Tuple[bool, List[str]]:
        """
        Validate batch meets VoyageAI requirements.
        
        Args:
            batch: Batch to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check chunk limit
        if batch.size > 1000:
            errors.append(f"Batch size {batch.size} exceeds 1000 chunk limit")
        
        # Check token limit
        actual_tokens = self.token_counter.estimate_batch_tokens(batch.texts)
        if actual_tokens > 10000:
            errors.append(f"Batch tokens {actual_tokens} exceeds 10000 token limit")
        
        # Check for empty texts
        empty_count = sum(1 for text in batch.texts if not text.strip())
        if empty_count > 0:
            errors.append(f"Batch contains {empty_count} empty texts")
        
        # Warn about safety margins
        if batch.size > self.CHUNK_LIMIT:
            errors.append(f"Batch size {batch.size} exceeds safety margin {self.CHUNK_LIMIT}")
        
        if actual_tokens > self.TOKEN_LIMIT:
            errors.append(f"Batch tokens {actual_tokens} exceeds safety margin {self.TOKEN_LIMIT}")
        
        return len(errors) == 0, errors
    
    def optimize_batch_order(self, items: List[BatchItem]) -> List[BatchItem]:
        """
        Optimize batch item order for better packing.
        
        Args:
            items: List of batch items
            
        Returns:
            Optimized list of batch items
        """
        # Sort by token count (largest first) for better bin packing
        return sorted(items, key=lambda x: x.estimated_tokens, reverse=True)
    
    def _update_avg_stats(self):
        """Update running average statistics."""
        if self.stats.batches_created > 0:
            self.stats.avg_batch_size = (
                self.stats.total_items_processed / self.stats.batches_created
            )
            self.stats.avg_tokens_per_batch = (
                self.stats.total_tokens_processed / self.stats.batches_created
            )
    
    def get_stats(self) -> BatchingStats:
        """Get current batching statistics."""
        return self.stats
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = BatchingStats()
    
    @property
    def current_batch_info(self) -> Dict[str, Any]:
        """Get information about current batch."""
        return {
            "items_count": len(self.current_batch),
            "current_tokens": self.current_tokens,
            "available_tokens": self.TOKEN_LIMIT - self.current_tokens,
            "available_chunks": self.CHUNK_LIMIT - len(self.current_batch),
            "can_add_more": len(self.current_batch) < self.CHUNK_LIMIT and self.current_tokens < self.TOKEN_LIMIT
        }


class BatchProcessor:
    """High-level processor that combines streaming and batching."""
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize batch processor.
        
        Args:
            model_name: VoyageAI model name
            config: Optional configuration
        """
        self.model_name = model_name
        self.config = config or {}
        self.batch_manager = VoyageBatchManager(model_name, config)
    
    async def process_stream_to_batches(
        self, 
        items_stream: AsyncIterator[ProcessedItem]
    ) -> AsyncIterator[Batch]:
        """
        Process stream of items into batches.
        
        Args:
            items_stream: Async iterator of ProcessedItem
            
        Yields:
            Batch: Completed batches ready for API processing
        """
        async for item in items_stream:
            completed_batch = self.batch_manager.add_processed_item(item)
            if completed_batch:
                # Validate batch before yielding
                is_valid, errors = self.batch_manager.validate_batch(completed_batch)
                if not is_valid:
                    logger.warning(f"Batch validation failed: {errors}")
                    # Could implement batch splitting logic here
                
                yield completed_batch
        
        # Yield final batch
        final_batch = self.batch_manager.finalize_batches()
        if final_batch:
            is_valid, errors = self.batch_manager.validate_batch(final_batch)
            if not is_valid:
                logger.warning(f"Final batch validation failed: {errors}")
            yield final_batch
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        batch_stats = self.batch_manager.get_stats()
        
        return {
            "batches_created": batch_stats.batches_created,
            "total_items_processed": batch_stats.total_items_processed,
            "total_tokens_processed": batch_stats.total_tokens_processed,
            "avg_batch_size": batch_stats.avg_batch_size,
            "avg_tokens_per_batch": batch_stats.avg_tokens_per_batch,
            "processing_time": time.time() - batch_stats.processing_start_time,
            "current_batch_info": self.batch_manager.current_batch_info,
            "limits": {
                "token_limit": self.batch_manager.TOKEN_LIMIT,
                "chunk_limit": self.batch_manager.CHUNK_LIMIT
            }
        }


# Rate limiting support
class RateLimitedBatchProcessor(BatchProcessor):
    """Batch processor with rate limiting for API calls."""
    
    def __init__(
        self, 
        model_name: str, 
        config: Optional[Dict[str, Any]] = None,
        requests_per_minute: int = 60
    ):
        """
        Initialize rate-limited batch processor.
        
        Args:
            model_name: VoyageAI model name
            config: Optional configuration
            requests_per_minute: Rate limit for API calls
        """
        super().__init__(model_name, config)
        self.requests_per_minute = requests_per_minute
        self.request_times: deque = deque()
        self.rate_limit_lock = asyncio.Lock()
    
    async def acquire_rate_limit(self):
        """Acquire permission to make API request."""
        async with self.rate_limit_lock:
            now = time.time()
            
            # Remove requests older than 1 minute
            while self.request_times and self.request_times[0] < now - 60:
                self.request_times.popleft()
            
            # Check if we can make request
            if len(self.request_times) >= self.requests_per_minute:
                # Calculate wait time
                oldest_request = self.request_times[0]
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    return await self.acquire_rate_limit()  # Recursive call after wait
            
            # Record this request
            self.request_times.append(now)


# Convenience functions
def create_batch_manager(model_name: str, config: Optional[Dict[str, Any]] = None) -> VoyageBatchManager:
    """Create a configured batch manager instance."""
    return VoyageBatchManager(model_name, config)


def create_batch_processor(
    model_name: str, 
    config: Optional[Dict[str, Any]] = None,
    rate_limited: bool = True,
    requests_per_minute: int = 60
) -> BatchProcessor:
    """Create a configured batch processor instance."""
    if rate_limited:
        return RateLimitedBatchProcessor(model_name, config, requests_per_minute)
    return BatchProcessor(model_name, config)