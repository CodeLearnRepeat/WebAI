"""
Progress tracking service for real-time monitoring of large JSON file processing operations.
Provides detailed progress updates, phase tracking, and performance statistics.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class ProcessingPhase(Enum):
    """Processing phases for progress tracking."""
    INITIALIZING = "initializing"
    ANALYZING_FILE = "analyzing_file"
    PARSING_JSON = "parsing_json"
    EXTRACTING_CONTENT = "extracting_content"
    CHUNKING_TEXT = "chunking_text"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    STORING_VECTORS = "storing_vectors"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class PhaseProgress:
    """Progress information for a specific processing phase."""
    phase: str
    items_processed: int = 0
    items_total: Optional[int] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    bytes_processed: int = 0
    errors_encountered: int = 0
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time for this phase."""
        end = self.end_time or time.time()
        return end - self.start_time if self.start_time > 0 else 0.0
    
    @property
    def percentage(self) -> Optional[float]:
        """Calculate completion percentage for this phase."""
        if self.items_total and self.items_total > 0:
            return min(100.0, (self.items_processed / self.items_total) * 100)
        return None
    
    @property
    def items_per_second(self) -> float:
        """Calculate processing rate for this phase."""
        elapsed = self.elapsed_time
        return self.items_processed / elapsed if elapsed > 0 else 0.0


@dataclass
class ProgressStatistics:
    """Comprehensive progress statistics."""
    task_id: str
    tenant_id: str
    total_items_processed: int = 0
    total_items_expected: Optional[int] = None
    total_chunks_created: int = 0
    total_embeddings_generated: int = 0
    total_vectors_stored: int = 0
    total_bytes_processed: int = 0
    total_errors: int = 0
    
    # Phase tracking
    current_phase: str = ProcessingPhase.INITIALIZING.value
    phase_history: List[PhaseProgress] = None
    
    # Timing
    start_time: float = 0.0
    estimated_completion: Optional[float] = None
    last_update: float = 0.0
    
    # Performance metrics
    avg_processing_rate: float = 0.0  # items per second
    peak_processing_rate: float = 0.0
    embedding_batch_stats: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.phase_history is None:
            self.phase_history = []
        if self.embedding_batch_stats is None:
            self.embedding_batch_stats = {}
        if self.start_time == 0.0:
            self.start_time = time.time()
        self.last_update = time.time()
    
    @property
    def overall_percentage(self) -> Optional[float]:
        """Calculate overall completion percentage."""
        if self.total_items_expected and self.total_items_expected > 0:
            return min(100.0, (self.total_items_processed / self.total_items_expected) * 100)
        return None
    
    @property
    def elapsed_time(self) -> float:
        """Calculate total elapsed time."""
        return time.time() - self.start_time if self.start_time > 0 else 0.0
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Estimate remaining processing time."""
        if (self.total_items_expected and self.total_items_processed > 0 
            and self.avg_processing_rate > 0):
            remaining_items = self.total_items_expected - self.total_items_processed
            return remaining_items / self.avg_processing_rate
        return None


class ProgressTracker:
    """Real-time progress tracker for background processing tasks."""
    
    def __init__(self, redis_client=None, update_interval: float = 5.0):
        """
        Initialize progress tracker.
        
        Args:
            redis_client: Redis client instance
            update_interval: Minimum seconds between progress updates
        """
        self.redis = redis_client or get_redis_client()
        self.update_interval = update_interval
        self.active_trackers: Dict[str, ProgressStatistics] = {}
        
        # Redis key patterns
        self.PROGRESS_KEY_PREFIX = "progress:"
        self.PHASE_HISTORY_PREFIX = "phase_history:"
        self.STATS_PREFIX = "stats:"
        
        logger.info(f"Initialized ProgressTracker with update_interval={update_interval}s")
    
    async def start_tracking(
        self,
        task_id: str,
        tenant_id: str,
        total_items_expected: Optional[int] = None
    ) -> ProgressStatistics:
        """
        Start tracking progress for a task.
        
        Args:
            task_id: Task identifier
            tenant_id: Tenant identifier
            total_items_expected: Expected total number of items
            
        Returns:
            ProgressStatistics object for tracking
        """
        progress_stats = ProgressStatistics(
            task_id=task_id,
            tenant_id=tenant_id,
            total_items_expected=total_items_expected
        )
        
        # Store in memory for fast access
        self.active_trackers[task_id] = progress_stats
        
        # Persist to Redis
        await self._store_progress(progress_stats)
        
        logger.info(f"Started progress tracking for task {task_id}")
        return progress_stats
    
    async def update_phase(
        self,
        task_id: str,
        new_phase: ProcessingPhase,
        items_total: Optional[int] = None
    ) -> bool:
        """
        Update the current processing phase.
        
        Args:
            task_id: Task identifier
            new_phase: New processing phase
            items_total: Total items for this phase
            
        Returns:
            True if update was successful
        """
        progress_stats = await self._get_progress_stats(task_id)
        if not progress_stats:
            return False
        
        # End current phase if it exists
        if progress_stats.phase_history:
            current_phase = progress_stats.phase_history[-1]
            if current_phase.end_time is None:
                current_phase.end_time = time.time()
        
        # Start new phase
        new_phase_progress = PhaseProgress(
            phase=new_phase.value,
            start_time=time.time(),
            items_total=items_total
        )
        progress_stats.phase_history.append(new_phase_progress)
        progress_stats.current_phase = new_phase.value
        
        await self._store_progress(progress_stats)
        
        logger.debug(f"Task {task_id} entered phase: {new_phase.value}")
        return True
    
    async def update_progress(
        self,
        task_id: str,
        items_processed: Optional[int] = None,
        chunks_created: Optional[int] = None,
        embeddings_generated: Optional[int] = None,
        vectors_stored: Optional[int] = None,
        bytes_processed: Optional[int] = None,
        errors_encountered: Optional[int] = None,
        force_update: bool = False
    ) -> bool:
        """
        Update progress counters.
        
        Args:
            task_id: Task identifier
            items_processed: Number of items processed
            chunks_created: Number of chunks created
            embeddings_generated: Number of embeddings generated
            vectors_stored: Number of vectors stored
            bytes_processed: Number of bytes processed
            errors_encountered: Number of errors encountered
            force_update: Force update even if interval not reached
            
        Returns:
            True if update was successful
        """
        progress_stats = await self._get_progress_stats(task_id)
        if not progress_stats:
            return False
        
        # Check update interval
        if not force_update and (time.time() - progress_stats.last_update) < self.update_interval:
            return False
        
        # Update counters
        if items_processed is not None:
            progress_stats.total_items_processed = items_processed
        if chunks_created is not None:
            progress_stats.total_chunks_created = chunks_created
        if embeddings_generated is not None:
            progress_stats.total_embeddings_generated = embeddings_generated
        if vectors_stored is not None:
            progress_stats.total_vectors_stored = vectors_stored
        if bytes_processed is not None:
            progress_stats.total_bytes_processed = bytes_processed
        if errors_encountered is not None:
            progress_stats.total_errors = errors_encountered
        
        # Update current phase progress
        if progress_stats.phase_history:
            current_phase = progress_stats.phase_history[-1]
            if items_processed is not None:
                current_phase.items_processed = items_processed
            if bytes_processed is not None:
                current_phase.bytes_processed = bytes_processed
            if errors_encountered is not None:
                current_phase.errors_encountered = errors_encountered
        
        # Update performance metrics
        await self._update_performance_metrics(progress_stats)
        
        # Update estimated completion time
        await self._update_time_estimates(progress_stats)
        
        progress_stats.last_update = time.time()
        await self._store_progress(progress_stats)
        
        return True
    
    async def get_progress(self, task_id: str) -> Optional[ProgressStatistics]:
        """
        Get current progress for a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            ProgressStatistics or None if not found
        """
        return await self._get_progress_stats(task_id)
    
    async def get_detailed_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed progress information including phase breakdown.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Detailed progress dictionary
        """
        progress_stats = await self._get_progress_stats(task_id)
        if not progress_stats:
            return None
        
        # Calculate phase breakdown
        phase_breakdown = []
        for phase in progress_stats.phase_history:
            phase_breakdown.append({
                "phase": phase.phase,
                "items_processed": phase.items_processed,
                "items_total": phase.items_total,
                "percentage": phase.percentage,
                "elapsed_time": phase.elapsed_time,
                "items_per_second": phase.items_per_second,
                "errors": phase.errors_encountered,
                "completed": phase.end_time is not None
            })
        
        # Current phase details
        current_phase_details = None
        if progress_stats.phase_history:
            current_phase = progress_stats.phase_history[-1]
            current_phase_details = {
                "phase": current_phase.phase,
                "items_processed": current_phase.items_processed,
                "items_total": current_phase.items_total,
                "percentage": current_phase.percentage,
                "items_per_second": current_phase.items_per_second
            }
        
        return {
            "task_id": progress_stats.task_id,
            "tenant_id": progress_stats.tenant_id,
            "overall": {
                "items_processed": progress_stats.total_items_processed,
                "items_expected": progress_stats.total_items_expected,
                "percentage": progress_stats.overall_percentage,
                "chunks_created": progress_stats.total_chunks_created,
                "embeddings_generated": progress_stats.total_embeddings_generated,
                "vectors_stored": progress_stats.total_vectors_stored,
                "bytes_processed": progress_stats.total_bytes_processed,
                "errors_total": progress_stats.total_errors
            },
            "timing": {
                "start_time": progress_stats.start_time,
                "elapsed_time": progress_stats.elapsed_time,
                "estimated_completion": progress_stats.estimated_completion,
                "estimated_remaining": progress_stats.estimated_remaining_time,
                "last_update": progress_stats.last_update
            },
            "performance": {
                "avg_processing_rate": progress_stats.avg_processing_rate,
                "peak_processing_rate": progress_stats.peak_processing_rate,
                "embedding_batch_stats": progress_stats.embedding_batch_stats
            },
            "current_phase": current_phase_details,
            "phase_history": phase_breakdown
        }
    
    async def update_embedding_stats(
        self,
        task_id: str,
        batch_stats: Dict[str, Any]
    ) -> bool:
        """
        Update embedding-specific statistics.
        
        Args:
            task_id: Task identifier
            batch_stats: Batch processing statistics
            
        Returns:
            True if update was successful
        """
        progress_stats = await self._get_progress_stats(task_id)
        if not progress_stats:
            return False
        
        # Merge with existing stats
        progress_stats.embedding_batch_stats.update(batch_stats)
        await self._store_progress(progress_stats)
        
        return True
    
    async def finish_tracking(self, task_id: str, success: bool = True) -> bool:
        """
        Finish tracking and clean up.
        
        Args:
            task_id: Task identifier
            success: Whether processing completed successfully
            
        Returns:
            True if cleanup was successful
        """
        progress_stats = await self._get_progress_stats(task_id)
        if not progress_stats:
            return False
        
        # End current phase
        if progress_stats.phase_history:
            current_phase = progress_stats.phase_history[-1]
            if current_phase.end_time is None:
                current_phase.end_time = time.time()
        
        # Set final phase
        final_phase = ProcessingPhase.COMPLETED if success else ProcessingPhase.ERROR
        progress_stats.current_phase = final_phase.value
        
        # Final update
        await self._store_progress(progress_stats)
        
        # Remove from active trackers
        if task_id in self.active_trackers:
            del self.active_trackers[task_id]
        
        logger.info(f"Finished progress tracking for task {task_id} (success={success})")
        return True
    
    async def cleanup_old_progress(self, max_age_hours: int = 48) -> int:
        """
        Clean up old progress data.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of progress records cleaned up
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0
        
        try:
            # Get all progress keys
            progress_keys = await self.redis.keys(f"{self.PROGRESS_KEY_PREFIX}*")
            
            for key in progress_keys:
                data = await self.redis.get(key)
                if not data:
                    continue
                
                try:
                    progress_dict = json.loads(data)
                    start_time = progress_dict.get("start_time", 0)
                    
                    if start_time < cutoff_time:
                        await self.redis.delete(key)
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing progress key {key} during cleanup: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} old progress records")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during progress cleanup: {e}")
            return 0
    
    async def _get_progress_stats(self, task_id: str) -> Optional[ProgressStatistics]:
        """Get progress stats from memory or Redis."""
        # Check memory first
        if task_id in self.active_trackers:
            return self.active_trackers[task_id]
        
        # Load from Redis
        try:
            progress_key = f"{self.PROGRESS_KEY_PREFIX}{task_id}"
            data = await self.redis.get(progress_key)
            
            if not data:
                return None
            
            progress_dict = json.loads(data)
            
            # Convert phase history back to objects
            if 'phase_history' in progress_dict:
                progress_dict['phase_history'] = [
                    PhaseProgress(**phase) for phase in progress_dict['phase_history']
                ]
            
            progress_stats = ProgressStatistics(**progress_dict)
            
            # Store in memory for future access
            self.active_trackers[task_id] = progress_stats
            
            return progress_stats
            
        except Exception as e:
            logger.error(f"Failed to load progress for task {task_id}: {e}")
            return None
    
    async def _store_progress(self, progress_stats: ProgressStatistics):
        """Store progress stats to Redis."""
        try:
            progress_key = f"{self.PROGRESS_KEY_PREFIX}{progress_stats.task_id}"
            
            # Convert to dict for JSON serialization
            data = asdict(progress_stats)
            
            # Set TTL for 7 days
            await self.redis.setex(
                progress_key,
                7 * 24 * 3600,  # 7 days TTL
                json.dumps(data, default=str)
            )
            
        except Exception as e:
            logger.error(f"Failed to store progress for task {progress_stats.task_id}: {e}")
    
    async def _update_performance_metrics(self, progress_stats: ProgressStatistics):
        """Update performance metrics like processing rate."""
        elapsed = progress_stats.elapsed_time
        if elapsed > 0 and progress_stats.total_items_processed > 0:
            # Update average processing rate
            progress_stats.avg_processing_rate = progress_stats.total_items_processed / elapsed
            
            # Update peak rate if current rate is higher
            current_rate = progress_stats.avg_processing_rate
            if current_rate > progress_stats.peak_processing_rate:
                progress_stats.peak_processing_rate = current_rate
    
    async def _update_time_estimates(self, progress_stats: ProgressStatistics):
        """Update estimated completion time."""
        if (progress_stats.total_items_expected and progress_stats.avg_processing_rate > 0 
            and progress_stats.total_items_processed > 0):
            
            remaining_items = progress_stats.total_items_expected - progress_stats.total_items_processed
            remaining_time = remaining_items / progress_stats.avg_processing_rate
            progress_stats.estimated_completion = time.time() + remaining_time


# Global progress tracker instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get global progress tracker instance."""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


async def initialize_progress_tracker(update_interval: float = 5.0):
    """Initialize the global progress tracker."""
    global _progress_tracker
    _progress_tracker = ProgressTracker(update_interval=update_interval)
    return _progress_tracker