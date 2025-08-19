"""
Checkpoint and recovery system for handling partial failures in large JSON file processing.
Provides reliable state persistence and recovery mechanisms.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from pathlib import Path

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Checkpoint data structure for processing state."""
    task_id: str
    file_path: str
    file_offset: int = 0
    items_processed: int = 0
    chunks_processed: int = 0
    embeddings_generated: int = 0
    last_successful_batch: Optional[Dict[str, Any]] = None
    processing_state: Optional[Dict[str, Any]] = None
    error_recovery_info: Optional[Dict[str, Any]] = None
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class RecoveryContext:
    """Recovery context for resuming failed processing."""
    checkpoint: CheckpointData
    should_retry_last_batch: bool = False
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def can_retry(self) -> bool:
        """Check if retry is allowed."""
        return self.retry_count < self.max_retries


class CheckpointManager:
    """Manages checkpoints and recovery for background processing tasks."""
    
    def __init__(self, redis_client=None, checkpoint_interval: int = 100):
        """
        Initialize checkpoint manager.
        
        Args:
            redis_client: Redis client instance
            checkpoint_interval: Number of items between automatic checkpoints
        """
        self.redis = redis_client or get_redis_client()
        self.checkpoint_interval = checkpoint_interval
        
        # Redis key patterns
        self.CHECKPOINT_KEY_PREFIX = "checkpoint:"
        self.RECOVERY_KEY_PREFIX = "recovery:"
        self.FAILED_BATCH_PREFIX = "failed_batch:"
        
        logger.info(f"Initialized CheckpointManager with interval={checkpoint_interval}")
    
    async def save_checkpoint(
        self,
        task_id: str,
        file_path: str,
        file_offset: int = 0,
        items_processed: int = 0,
        chunks_processed: int = 0,
        embeddings_generated: int = 0,
        processing_state: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Save processing checkpoint.
        
        Args:
            task_id: Task identifier
            file_path: Path to file being processed
            file_offset: Current file offset (for resuming)
            items_processed: Number of items processed
            chunks_processed: Number of chunks processed
            embeddings_generated: Number of embeddings generated
            processing_state: Additional processing state
            force: Force save even if interval not reached
            
        Returns:
            True if checkpoint was saved
        """
        # Check if we should save based on interval
        if not force and items_processed % self.checkpoint_interval != 0:
            return False
        
        checkpoint = CheckpointData(
            task_id=task_id,
            file_path=file_path,
            file_offset=file_offset,
            items_processed=items_processed,
            chunks_processed=chunks_processed,
            embeddings_generated=embeddings_generated,
            processing_state=processing_state or {}
        )
        
        try:
            # Store checkpoint in Redis with 7-day TTL
            checkpoint_key = f"{self.CHECKPOINT_KEY_PREFIX}{task_id}"
            await self.redis.setex(
                checkpoint_key,
                7 * 24 * 3600,  # 7 days TTL
                json.dumps(asdict(checkpoint), default=str)
            )
            
            logger.debug(f"Saved checkpoint for task {task_id}: {items_processed} items")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint for task {task_id}: {e}")
            return False
    
    async def load_checkpoint(self, task_id: str) -> Optional[CheckpointData]:
        """
        Load checkpoint for task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            CheckpointData if found, None otherwise
        """
        try:
            checkpoint_key = f"{self.CHECKPOINT_KEY_PREFIX}{task_id}"
            data = await self.redis.get(checkpoint_key)
            
            if not data:
                return None
            
            checkpoint_dict = json.loads(data)
            return CheckpointData(**checkpoint_dict)
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint for task {task_id}: {e}")
            return None
    
    async def delete_checkpoint(self, task_id: str) -> bool:
        """
        Delete checkpoint after successful completion.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            checkpoint_key = f"{self.CHECKPOINT_KEY_PREFIX}{task_id}"
            result = await self.redis.delete(checkpoint_key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete checkpoint for task {task_id}: {e}")
            return False
    
    async def save_failed_batch(
        self,
        task_id: str,
        batch_data: Dict[str, Any],
        error_info: Dict[str, Any]
    ) -> str:
        """
        Save failed batch for later retry.
        
        Args:
            task_id: Task identifier
            batch_data: Batch data that failed
            error_info: Error information
            
        Returns:
            Failed batch ID
        """
        failed_batch_id = f"{task_id}_{int(time.time())}"
        
        failed_batch = {
            "task_id": task_id,
            "batch_id": failed_batch_id,
            "batch_data": batch_data,
            "error_info": error_info,
            "created_at": time.time(),
            "retry_count": 0
        }
        
        try:
            failed_batch_key = f"{self.FAILED_BATCH_PREFIX}{failed_batch_id}"
            await self.redis.setex(
                failed_batch_key,
                24 * 3600,  # 24 hours TTL
                json.dumps(failed_batch, default=str)
            )
            
            logger.warning(f"Saved failed batch {failed_batch_id} for task {task_id}")
            return failed_batch_id
            
        except Exception as e:
            logger.error(f"Failed to save failed batch for task {task_id}: {e}")
            return ""
    
    async def get_failed_batches(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get failed batches for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            List of failed batch information
        """
        try:
            pattern = f"{self.FAILED_BATCH_PREFIX}{task_id}_*"
            keys = await self.redis.keys(pattern)
            
            failed_batches = []
            for key in keys:
                data = await self.redis.get(key)
                if data:
                    failed_batches.append(json.loads(data))
            
            return failed_batches
            
        except Exception as e:
            logger.error(f"Failed to get failed batches for task {task_id}: {e}")
            return []
    
    async def retry_failed_batch(
        self,
        failed_batch_id: str,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Attempt to retry a failed batch.
        
        Args:
            failed_batch_id: Failed batch identifier
            max_retries: Maximum retry attempts
            
        Returns:
            Batch data if retry should proceed, None if exhausted
        """
        try:
            failed_batch_key = f"{self.FAILED_BATCH_PREFIX}{failed_batch_id}"
            data = await self.redis.get(failed_batch_key)
            
            if not data:
                return None
            
            failed_batch = json.loads(data)
            retry_count = failed_batch.get("retry_count", 0)
            
            if retry_count >= max_retries:
                logger.warning(f"Failed batch {failed_batch_id} exceeded max retries")
                return None
            
            # Increment retry count
            failed_batch["retry_count"] = retry_count + 1
            failed_batch["last_retry_at"] = time.time()
            
            # Update in Redis
            await self.redis.setex(
                failed_batch_key,
                24 * 3600,  # Reset TTL
                json.dumps(failed_batch, default=str)
            )
            
            logger.info(f"Retrying failed batch {failed_batch_id} (attempt {retry_count + 1})")
            return failed_batch["batch_data"]
            
        except Exception as e:
            logger.error(f"Failed to retry batch {failed_batch_id}: {e}")
            return None
    
    async def mark_batch_recovered(self, failed_batch_id: str) -> bool:
        """
        Mark a failed batch as successfully recovered.
        
        Args:
            failed_batch_id: Failed batch identifier
            
        Returns:
            True if marked successfully
        """
        try:
            failed_batch_key = f"{self.FAILED_BATCH_PREFIX}{failed_batch_id}"
            result = await self.redis.delete(failed_batch_key)
            
            if result > 0:
                logger.info(f"Marked failed batch {failed_batch_id} as recovered")
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to mark batch {failed_batch_id} as recovered: {e}")
            return False
    
    async def create_recovery_context(self, task_id: str) -> Optional[RecoveryContext]:
        """
        Create recovery context for resuming a failed task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            RecoveryContext if recovery is possible, None otherwise
        """
        checkpoint = await self.load_checkpoint(task_id)
        if not checkpoint:
            logger.info(f"No checkpoint found for task {task_id}, starting fresh")
            return None
        
        # Check for failed batches
        failed_batches = await self.get_failed_batches(task_id)
        should_retry = len(failed_batches) > 0
        
        recovery_context = RecoveryContext(
            checkpoint=checkpoint,
            should_retry_last_batch=should_retry
        )
        
        logger.info(
            f"Created recovery context for task {task_id}: "
            f"items_processed={checkpoint.items_processed}, "
            f"failed_batches={len(failed_batches)}"
        )
        
        return recovery_context
    
    async def estimate_recovery_progress(self, task_id: str) -> Dict[str, Any]:
        """
        Estimate recovery progress and provide recovery statistics.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Recovery statistics
        """
        checkpoint = await self.load_checkpoint(task_id)
        failed_batches = await self.get_failed_batches(task_id)
        
        if not checkpoint:
            return {
                "recoverable": False,
                "reason": "No checkpoint found"
            }
        
        # Calculate recovery metrics
        total_failed_items = sum(
            len(batch.get("batch_data", {}).get("texts", []))
            for batch in failed_batches
        )
        
        recovery_stats = {
            "recoverable": True,
            "checkpoint_age_hours": (time.time() - checkpoint.created_at) / 3600,
            "items_processed": checkpoint.items_processed,
            "chunks_processed": checkpoint.chunks_processed,
            "embeddings_generated": checkpoint.embeddings_generated,
            "failed_batches_count": len(failed_batches),
            "failed_items_count": total_failed_items,
            "estimated_remaining_work": {
                "failed_batches": len(failed_batches),
                "failed_items": total_failed_items
            }
        }
        
        return recovery_stats
    
    async def cleanup_old_checkpoints(self, max_age_hours: int = 168) -> int:
        """
        Clean up old checkpoints (default: 7 days).
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of checkpoints cleaned up
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0
        
        try:
            # Get all checkpoint keys
            checkpoint_keys = await self.redis.keys(f"{self.CHECKPOINT_KEY_PREFIX}*")
            
            for key in checkpoint_keys:
                data = await self.redis.get(key)
                if not data:
                    continue
                
                try:
                    checkpoint_dict = json.loads(data)
                    created_at = checkpoint_dict.get("created_at", 0)
                    
                    if created_at < cutoff_time:
                        await self.redis.delete(key)
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing checkpoint key {key} during cleanup: {e}")
            
            # Also cleanup old failed batches
            failed_batch_keys = await self.redis.keys(f"{self.FAILED_BATCH_PREFIX}*")
            for key in failed_batch_keys:
                data = await self.redis.get(key)
                if not data:
                    continue
                
                try:
                    batch_dict = json.loads(data)
                    created_at = batch_dict.get("created_at", 0)
                    
                    if created_at < cutoff_time:
                        await self.redis.delete(key)
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing failed batch key {key} during cleanup: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old checkpoints and failed batches")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during checkpoint cleanup: {e}")
            return 0


# Global checkpoint manager instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager


async def initialize_checkpoint_manager(checkpoint_interval: int = 100):
    """Initialize the global checkpoint manager."""
    global _checkpoint_manager
    _checkpoint_manager = CheckpointManager(checkpoint_interval=checkpoint_interval)
    return _checkpoint_manager


# Checkpoint decorator for automatic checkpoint creation
def checkpoint_every(interval: int = 100):
    """
    Decorator to automatically create checkpoints during processing.
    
    Args:
        interval: Number of items between checkpoints
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            checkpoint_manager = get_checkpoint_manager()
            
            # Extract task_id and other parameters from function arguments
            # This would need to be customized based on function signature
            task_id = kwargs.get('task_id') or (args[0] if args else None)
            
            try:
                result = await func(*args, **kwargs)
                
                # Auto-save checkpoint if processing successful
                if hasattr(result, 'items_processed'):
                    await checkpoint_manager.save_checkpoint(
                        task_id=task_id,
                        file_path=kwargs.get('file_path', ''),
                        items_processed=result.items_processed,
                        force=True
                    )
                
                return result
                
            except Exception as e:
                # Save error state
                logger.error(f"Error in {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator