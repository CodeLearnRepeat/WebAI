"""
Background task management system for long-running JSON file processing operations.
Uses Redis for task queue management and status tracking.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from app.core.redis import get_redis_client
from app.services.rag_ingest import ingest_json_file_streaming
from app.services.streaming_parser import get_file_stats
from app.services.checkpoint_manager import get_checkpoint_manager
from app.services.progress_tracker import get_progress_tracker, ProcessingPhase

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Use ProcessingPhase from progress_tracker to avoid conflicts


@dataclass
class TaskProgress:
    """Progress tracking for background tasks."""
    items_processed: int = 0
    items_total: Optional[int] = None
    chunks_processed: int = 0
    embeddings_generated: int = 0
    bytes_processed: int = 0
    current_phase: str = ProcessingPhase.INITIALIZING.value
    start_time: float = 0.0
    estimated_completion: Optional[float] = None
    last_checkpoint: Optional[float] = None
    error_count: int = 0
    
    @property
    def percentage(self) -> Optional[float]:
        """Calculate completion percentage."""
        if self.items_total and self.items_total > 0:
            return min(100.0, (self.items_processed / self.items_total) * 100)
        return None
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time if self.start_time > 0 else 0.0


@dataclass
class TaskInfo:
    """Complete task information."""
    task_id: str
    tenant_id: str
    status: str = TaskStatus.QUEUED.value
    file_info: Dict[str, Any] = None
    configuration: Dict[str, Any] = None
    progress: TaskProgress = None
    error_info: Optional[Dict[str, Any]] = None
    created_at: float = 0.0
    updated_at: float = 0.0
    
    def __post_init__(self):
        if self.progress is None:
            self.progress = TaskProgress()
        if self.file_info is None:
            self.file_info = {}
        if self.configuration is None:
            self.configuration = {}
        if self.created_at == 0.0:
            self.created_at = time.time()
        self.updated_at = time.time()


class BackgroundTaskManager:
    """Manages background processing tasks with Redis-based queue."""
    
    def __init__(self, redis_client=None, max_concurrent_tasks: int = 5):
        """
        Initialize background task manager.
        
        Args:
            redis_client: Redis client instance
            max_concurrent_tasks: Maximum concurrent processing tasks
        """
        self.redis = redis_client or get_redis_client()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._shutdown = False
        
        # Redis key patterns
        self.TASK_KEY_PREFIX = "processing_task:"
        self.QUEUE_KEY = "task_queue"
        self.ACTIVE_TASKS_KEY = "active_tasks"
        
        logger.info(f"Initialized BackgroundTaskManager with max_concurrent_tasks={max_concurrent_tasks}")
    
    async def start_task(
        self,
        tenant_id: str,
        file_path: str,
        file_size: int,
        schema_config: Dict[str, Any],
        embedding_provider: str,
        embedding_model: str,
        provider_key: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Start a new background processing task.
        
        Args:
            tenant_id: Tenant identifier
            file_path: Path to file to process
            file_size: File size in bytes
            schema_config: Schema configuration for processing
            embedding_provider: Embedding provider name
            embedding_model: Embedding model name
            provider_key: API key for provider
            task_id: Optional custom task ID
            
        Returns:
            Task ID for tracking
        """
        if task_id is None:
            task_id = f"ingest_{uuid.uuid4().hex}"
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            tenant_id=tenant_id,
            file_info={
                "file_path": file_path,
                "file_size": file_size,
                "filename": Path(file_path).name
            },
            configuration={
                "schema_config": schema_config,
                "embedding_provider": embedding_provider,
                "embedding_model": embedding_model,
                "provider_key": provider_key
            }
        )
        
        # Store in Redis
        await self._store_task_info(task_info)
        
        # Add to queue
        await self.redis.lpush(self.QUEUE_KEY, task_id)
        
        # Start processing if capacity available
        await self._process_queue()
        
        logger.info(f"Started background task {task_id} for tenant {tenant_id}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get current task status and progress.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskInfo object or None if not found
        """
        task_data = await self.redis.get(f"{self.TASK_KEY_PREFIX}{task_id}")
        if not task_data:
            return None
        
        try:
            data = json.loads(task_data)
            # Convert progress dict back to TaskProgress object
            if 'progress' in data and isinstance(data['progress'], dict):
                data['progress'] = TaskProgress(**data['progress'])
            return TaskInfo(**data)
        except Exception as e:
            logger.error(f"Error deserializing task {task_id}: {e}")
            return None
    
    async def pause_task(self, task_id: str) -> bool:
        """
        Pause a running task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was paused, False otherwise
        """
        task_info = await self.get_task_status(task_id)
        if not task_info or task_info.status != TaskStatus.RUNNING.value:
            return False
        
        # Update status
        task_info.status = TaskStatus.PAUSED.value
        task_info.updated_at = time.time()
        await self._store_task_info(task_info)
        
        # Cancel the running task
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        logger.info(f"Paused task {task_id}")
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """
        Resume a paused task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was resumed, False otherwise
        """
        task_info = await self.get_task_status(task_id)
        if not task_info or task_info.status != TaskStatus.PAUSED.value:
            return False
        
        # Update status and re-queue
        task_info.status = TaskStatus.QUEUED.value
        task_info.updated_at = time.time()
        await self._store_task_info(task_info)
        
        # Add back to queue
        await self.redis.lpush(self.QUEUE_KEY, task_id)
        await self._process_queue()
        
        logger.info(f"Resumed task {task_id}")
        return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False otherwise
        """
        task_info = await self.get_task_status(task_id)
        if not task_info:
            return False
        
        # Update status
        task_info.status = TaskStatus.CANCELLED.value
        task_info.updated_at = time.time()
        await self._store_task_info(task_info)
        
        # Cancel running task if it exists
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            del self.running_tasks[task_id]
        
        # Remove from queue
        await self.redis.lrem(self.QUEUE_KEY, 0, task_id)
        
        logger.info(f"Cancelled task {task_id}")
        return True
    
    async def get_active_tasks(self) -> List[str]:
        """Get list of active task IDs."""
        active_tasks = await self.redis.smembers(self.ACTIVE_TASKS_KEY)
        return [task.decode() if isinstance(task, bytes) else task for task in active_tasks]
    
    async def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """
        Clean up completed tasks older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours for completed tasks
            
        Returns:
            Number of tasks cleaned up
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0
        
        # Get all task keys
        task_keys = await self.redis.keys(f"{self.TASK_KEY_PREFIX}*")
        
        for key in task_keys:
            task_data = await self.redis.get(key)
            if not task_data:
                continue
            
            try:
                data = json.loads(task_data)
                status = data.get('status')
                updated_at = data.get('updated_at', 0)
                
                # Remove old completed, failed, or cancelled tasks
                if (status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value] 
                    and updated_at < cutoff_time):
                    await self.redis.delete(key)
                    cleaned_count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing task key {key} during cleanup: {e}")
        
        logger.info(f"Cleaned up {cleaned_count} old tasks")
        return cleaned_count
    
    async def _process_queue(self):
        """Process the task queue if capacity is available."""
        active_count = len(self.running_tasks)
        
        while active_count < self.max_concurrent_tasks:
            # Get next task from queue
            task_id = await self.redis.rpop(self.QUEUE_KEY)
            if not task_id:
                break
            
            if isinstance(task_id, bytes):
                task_id = task_id.decode()
            
            # Start processing task
            task = asyncio.create_task(self._process_task(task_id))
            self.running_tasks[task_id] = task
            
            # Add to active tasks set
            await self.redis.sadd(self.ACTIVE_TASKS_KEY, task_id)
            
            active_count += 1
    
    async def _process_task(self, task_id: str):
        """
        Process a single task with enhanced error handling and checkpoint support.
        
        Args:
            task_id: Task identifier
        """
        checkpoint_manager = get_checkpoint_manager()
        progress_tracker = get_progress_tracker()
        
        try:
            # Get task info
            task_info = await self.get_task_status(task_id)
            if not task_info:
                logger.error(f"Task {task_id} not found")
                return
            
            # Check for existing checkpoint and recovery
            recovery_context = await checkpoint_manager.create_recovery_context(task_id)
            
            # Start progress tracking
            await progress_tracker.start_tracking(
                task_id=task_id,
                tenant_id=task_info.tenant_id
            )
            
            # Update status to running
            task_info.status = TaskStatus.RUNNING.value
            task_info.progress.start_time = time.time()
            await self._store_task_info(task_info)
            
            # Phase 1: Initialize and analyze
            await progress_tracker.update_phase(task_id, ProcessingPhase.ANALYZING_FILE)
            task_info.progress.current_phase = ProcessingPhase.ANALYZING_FILE.value
            await self._store_task_info(task_info)
            
            file_stats = await get_file_stats(task_info.file_info["file_path"])
            estimated_items = file_stats["estimated_items"]
            
            await progress_tracker.update_progress(
                task_id=task_id,
                items_processed=0,
                force_update=True
            )
            
            # Create enhanced progress callback with checkpoint support
            async def enhanced_progress_callback(processed: int, total: Optional[int] = None):
                # Update task info
                task_info.progress.items_processed = processed
                if total is not None:
                    task_info.progress.items_total = total
                task_info.updated_at = time.time()
                await self._store_task_info(task_info)
                
                # Update progress tracker
                await progress_tracker.update_progress(
                    task_id=task_id,
                    items_processed=processed
                )
                
                # Create checkpoint periodically
                if processed % 100 == 0:  # Every 100 items
                    await checkpoint_manager.save_checkpoint(
                        task_id=task_id,
                        file_path=task_info.file_info["file_path"],
                        items_processed=processed,
                        chunks_processed=task_info.progress.chunks_processed,
                        embeddings_generated=task_info.progress.embeddings_generated
                    )
            
            # Apply recovery if available
            items_already_processed = 0
            if recovery_context:
                items_already_processed = recovery_context.checkpoint.items_processed
                logger.info(f"Resuming task {task_id} from checkpoint: {items_already_processed} items processed")
                
                # Update progress with recovered state
                await progress_tracker.update_progress(
                    task_id=task_id,
                    items_processed=items_already_processed,
                    force_update=True
                )
            
            # Phase 2: Start processing with retry logic
            await progress_tracker.update_phase(task_id, ProcessingPhase.PARSING_JSON)
            
            # Process file with streaming ingestion and enhanced error handling
            max_retries = 3
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    result = await ingest_json_file_streaming(
                        file_path=task_info.file_info["file_path"],
                        schema_config=task_info.configuration["schema_config"],
                        milvus_conf=task_info.configuration.get("milvus_conf", {}),
                        emb_provider=task_info.configuration["embedding_provider"],
                        emb_model=task_info.configuration["embedding_model"],
                        provider_key=task_info.configuration.get("provider_key"),
                        progress_callback=enhanced_progress_callback
                    )
                    
                    # Success - break retry loop
                    break
                    
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Task {task_id} failed (attempt {retry_count}/{max_retries + 1}): {e}")
                    
                    if retry_count <= max_retries and await self._is_error_recoverable(e):
                        # Save checkpoint before retry
                        await checkpoint_manager.save_checkpoint(
                            task_id=task_id,
                            file_path=task_info.file_info["file_path"],
                            items_processed=task_info.progress.items_processed,
                            processing_state={"retry_count": retry_count, "last_error": str(e)},
                            force=True
                        )
                        
                        # Exponential backoff
                        delay = min(60.0, 2.0 ** retry_count)
                        logger.info(f"Retrying task {task_id} in {delay} seconds...")
                        await asyncio.sleep(delay)
                    else:
                        # Max retries exhausted or non-recoverable error
                        raise
            
            # Phase 3: Finalization
            await progress_tracker.update_phase(task_id, ProcessingPhase.FINALIZING)
            
            # Update final status
            task_info.status = TaskStatus.COMPLETED.value
            task_info.progress.current_phase = ProcessingPhase.COMPLETED.value
            task_info.progress.items_processed = result.get("upserted", 0)
            task_info.progress.embeddings_generated = result.get("upserted", 0)
            task_info.updated_at = time.time()
            
            # Store final results
            task_info.configuration["results"] = result
            await self._store_task_info(task_info)
            
            # Final progress update
            await progress_tracker.finish_tracking(task_id, success=True)
            
            # Clean up checkpoint after successful completion
            await checkpoint_manager.delete_checkpoint(task_id)
            
            logger.info(f"Completed task {task_id}: {result}")
            
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
            await progress_tracker.finish_tracking(task_id, success=False)
            # Don't update status here - it was already set by pause/cancel
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Update error status
            task_info = await self.get_task_status(task_id)
            if task_info:
                task_info.status = TaskStatus.FAILED.value
                task_info.progress.current_phase = ProcessingPhase.ERROR.value
                task_info.progress.error_count += 1
                task_info.error_info = {
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": time.time(),
                    "recoverable": await self._is_error_recoverable(e)
                }
                task_info.updated_at = time.time()
                await self._store_task_info(task_info)
            
            # Finish progress tracking with error
            await progress_tracker.finish_tracking(task_id, success=False)
            
            # Save final checkpoint for potential recovery
            await checkpoint_manager.save_checkpoint(
                task_id=task_id,
                file_path=task_info.file_info["file_path"] if task_info else "",
                items_processed=task_info.progress.items_processed if task_info else 0,
                processing_state={"final_error": str(e), "error_type": type(e).__name__},
                force=True
            )
        
        finally:
            # Cleanup
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            await self.redis.srem(self.ACTIVE_TASKS_KEY, task_id)
            
            # Process next task in queue
            await self._process_queue()
    
    async def _is_error_recoverable(self, error: Exception) -> bool:
        """Determine if an error is recoverable for future retry."""
        error_str = str(error).lower()
        
        # Non-recoverable errors
        non_recoverable = [
            "file not found", "permission denied", "invalid json",
            "schema validation", "authentication", "unauthorized",
            "invalid key", "api key", "forbidden"
        ]
        
        return not any(indicator in error_str for indicator in non_recoverable)
    
    async def _store_task_info(self, task_info: TaskInfo):
        """Store task info in Redis."""
        # Convert to dict for JSON serialization
        data = asdict(task_info)
        
        # Set TTL for 48 hours
        await self.redis.setex(
            f"{self.TASK_KEY_PREFIX}{task_info.task_id}",
            48 * 3600,  # 48 hours
            json.dumps(data, default=str)
        )
    
    async def shutdown(self):
        """Shutdown the task manager gracefully."""
        self._shutdown = True
        
        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            logger.info(f"Cancelling task {task_id} during shutdown")
            task.cancel()
        
        # Wait for tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        logger.info("Background task manager shutdown complete")


# Global task manager instance
_task_manager: Optional[BackgroundTaskManager] = None


def get_task_manager() -> BackgroundTaskManager:
    """Get global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = BackgroundTaskManager()
    return _task_manager


async def initialize_task_manager(max_concurrent_tasks: int = 5):
    """Initialize the global task manager."""
    global _task_manager
    _task_manager = BackgroundTaskManager(max_concurrent_tasks=max_concurrent_tasks)
    return _task_manager


async def shutdown_task_manager():
    """Shutdown the global task manager."""
    global _task_manager
    if _task_manager:
        await _task_manager.shutdown()
        _task_manager = None