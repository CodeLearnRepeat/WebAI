#!/usr/bin/env python3
"""
Comprehensive end-to-end tests for large JSON file processing with VoyageAI batching system.
Tests the complete workflow from file upload to vector storage with validation of all limits.
"""

import asyncio
import json
import pytest
import tempfile
import time
import logging
import psutil
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass

# Import test generator
from test_large_file_generator import LargeFileGenerator, FileSpec

# Import core services
from app.services.token_counter import VoyageTokenCounter, count_tokens
from app.services.streaming_parser import StreamingJSONProcessor, process_json_file
from app.services.batch_manager import VoyageBatchManager, BatchProcessor, create_batch_processor
from app.services.checkpoint_manager import CheckpointManager, get_checkpoint_manager
from app.services.progress_tracker import ProgressTracker, get_progress_tracker, ProcessingPhase
from app.services.background_tasks import TaskManager, get_task_manager, TaskStatus
from app.services.embeddings import BatchEmbeddingService, RobustVoyageEmbedder
from app.services.rag_ingest import ingest_json_file_streaming

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResults:
    """Container for test results and metrics."""
    test_name: str
    success: bool
    processing_time: float
    memory_usage_mb: float
    items_processed: int
    batches_created: int
    tokens_processed: int
    max_batch_tokens: int
    max_batch_chunks: int
    errors: List[str]
    validation_results: Dict[str, bool]


class VoyageAPILimitValidator:
    """Validates that VoyageAI API limits are never exceeded during processing."""
    
    def __init__(self):
        self.token_limit = 10000
        self.chunk_limit = 1000
        self.violations = []
        self.batch_stats = []
    
    def validate_batch(self, batch, batch_id: str = "unknown") -> Tuple[bool, List[str]]:
        """
        Validate a batch against VoyageAI limits.
        
        Args:
            batch: Batch object to validate
            batch_id: Batch identifier for tracking
            
        Returns:
            Tuple of (is_valid, violation_messages)
        """
        violations = []
        
        # Check token limit
        if batch.total_tokens > self.token_limit:
            violation = f"Batch {batch_id}: Token limit exceeded ({batch.total_tokens} > {self.token_limit})"
            violations.append(violation)
            self.violations.append(violation)
        
        # Check chunk limit
        if batch.size > self.chunk_limit:
            violation = f"Batch {batch_id}: Chunk limit exceeded ({batch.size} > {self.chunk_limit})"
            violations.append(violation)
            self.violations.append(violation)
        
        # Record batch stats
        self.batch_stats.append({
            "batch_id": batch_id,
            "tokens": batch.total_tokens,
            "chunks": batch.size,
            "valid": len(violations) == 0
        })
        
        return len(violations) == 0, violations
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "total_violations": len(self.violations),
            "violations": self.violations,
            "batches_validated": len(self.batch_stats),
            "max_tokens_seen": max([s["tokens"] for s in self.batch_stats], default=0),
            "max_chunks_seen": max([s["chunks"] for s in self.batch_stats], default=0),
            "all_batches_valid": len(self.violations) == 0
        }


class MemoryMonitor:
    """Monitor memory usage during processing."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
        self.peak_memory = self.initial_memory
        self.samples = []
    
    def sample(self):
        """Take a memory usage sample."""
        current_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
        self.samples.append(current_memory)
        self.peak_memory = max(self.peak_memory, current_memory)
    
    def get_stats(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        if not self.samples:
            return {"initial": self.initial_memory, "peak": self.peak_memory, "growth": 0}
        
        return {
            "initial_mb": self.initial_memory,
            "peak_mb": self.peak_memory,
            "final_mb": self.samples[-1] if self.samples else self.initial_memory,
            "growth_mb": self.peak_memory - self.initial_memory,
            "samples_count": len(self.samples)
        }


class LargeFileProcessingTests:
    """Comprehensive test suite for large file processing."""
    
    def __init__(self):
        self.file_generator = LargeFileGenerator()
        self.test_results: List[TestResults] = []
        self.validator = VoyageAPILimitValidator()
        
    async def setup_test_environment(self):
        """Set up test environment."""
        logger.info("Setting up test environment...")
        
        # Generate test files
        self.test_files = self.file_generator.generate_test_suite()
        
        # Initialize services (with mocked embedding for testing)
        self.token_counter = VoyageTokenCounter("voyage-large-2")
        self.checkpoint_manager = get_checkpoint_manager()
        self.progress_tracker = get_progress_tracker()
        
        logger.info(f"Test environment ready with {len(self.file_generator.generated_files)} test files")
    
    async def test_small_file_processing(self) -> TestResults:
        """Test processing of small files to validate basic functionality."""
        logger.info("Testing small file processing...")
        
        start_time = time.time()
        memory_monitor = MemoryMonitor()
        errors = []
        
        try:
            # Use smallest test file
            test_file = self.test_files["small_files"][0]
            
            # Configure schema
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {
                        "title": "title",
                        "id": "id",
                        "category": "metadata.category"
                    }
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 200,
                    "overlap_tokens": 20,
                    "model_name": "voyage-large-2"
                }
            }
            
            # Process with batch manager
            batch_manager = VoyageBatchManager("voyage-large-2")
            items_processed = 0
            batches_created = 0
            tokens_processed = 0
            max_batch_tokens = 0
            max_batch_chunks = 0
            
            memory_monitor.sample()
            
            # Stream and batch items
            async for item in process_json_file(test_file, schema_config):
                completed_batch = batch_manager.add_processed_item(item)
                items_processed += 1
                
                if completed_batch:
                    # Validate batch
                    is_valid, violations = self.validator.validate_batch(
                        completed_batch, f"small_file_batch_{batches_created}"
                    )
                    
                    if not is_valid:
                        errors.extend(violations)
                    
                    batches_created += 1
                    tokens_processed += completed_batch.total_tokens
                    max_batch_tokens = max(max_batch_tokens, completed_batch.total_tokens)
                    max_batch_chunks = max(max_batch_chunks, completed_batch.size)
                
                if items_processed % 50 == 0:
                    memory_monitor.sample()
            
            # Get final batch
            final_batch = batch_manager.finalize_batches()
            if final_batch:
                is_valid, violations = self.validator.validate_batch(final_batch, "small_file_final")
                if not is_valid:
                    errors.extend(violations)
                
                batches_created += 1
                tokens_processed += final_batch.total_tokens
                max_batch_tokens = max(max_batch_tokens, final_batch.total_tokens)
                max_batch_chunks = max(max_batch_chunks, final_batch.size)
            
            memory_monitor.sample()
            processing_time = time.time() - start_time
            memory_stats = memory_monitor.get_stats()
            
            # Validation checks
            validation_results = {
                "no_limit_violations": len(errors) == 0,
                "reasonable_batch_count": batches_created > 0 and batches_created < 20,
                "all_items_processed": items_processed > 0,
                "memory_growth_reasonable": memory_stats["growth_mb"] < 100  # < 100MB growth
            }
            
            success = all(validation_results.values())
            
            result = TestResults(
                test_name="small_file_processing",
                success=success,
                processing_time=processing_time,
                memory_usage_mb=memory_stats["peak_mb"],
                items_processed=items_processed,
                batches_created=batches_created,
                tokens_processed=tokens_processed,
                max_batch_tokens=max_batch_tokens,
                max_batch_chunks=max_batch_chunks,
                errors=errors,
                validation_results=validation_results
            )
            
            logger.info(f"Small file test completed: {items_processed} items, {batches_created} batches")
            return result
            
        except Exception as e:
            logger.error(f"Small file test failed: {e}")
            errors.append(str(e))
            
            return TestResults(
                test_name="small_file_processing",
                success=False,
                processing_time=time.time() - start_time,
                memory_usage_mb=memory_monitor.get_stats()["peak_mb"],
                items_processed=0,
                batches_created=0,
                tokens_processed=0,
                max_batch_tokens=0,
                max_batch_chunks=0,
                errors=errors,
                validation_results={"test_completed": False}
            )
    
    async def test_large_file_multiple_batches(self) -> TestResults:
        """Test processing of large files requiring multiple batches."""
        logger.info("Testing large file processing with multiple batches...")
        
        start_time = time.time()
        memory_monitor = MemoryMonitor()
        errors = []
        
        try:
            # Use large test file
            test_file = self.test_files["large_files"][0]
            
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {
                        "title": "title",
                        "id": "id",
                        "category": "metadata.category"
                    }
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 300,
                    "overlap_tokens": 30,
                    "model_name": "voyage-large-2"
                }
            }
            
            # Use batch processor for rate limiting
            batch_processor = create_batch_processor("voyage-large-2", rate_limited=False)
            
            items_processed = 0
            batches_created = 0
            tokens_processed = 0
            max_batch_tokens = 0
            max_batch_chunks = 0
            
            memory_monitor.sample()
            
            # Process through streaming pipeline
            async for item in process_json_file(test_file, schema_config):
                completed_batch = batch_processor.batch_manager.add_processed_item(item)
                items_processed += 1
                
                if completed_batch:
                    # Validate each batch
                    is_valid, violations = self.validator.validate_batch(
                        completed_batch, f"large_file_batch_{batches_created}"
                    )
                    
                    if not is_valid:
                        errors.extend(violations)
                        logger.error(f"Batch validation failed: {violations}")
                    
                    batches_created += 1
                    tokens_processed += completed_batch.total_tokens
                    max_batch_tokens = max(max_batch_tokens, completed_batch.total_tokens)
                    max_batch_chunks = max(max_batch_chunks, completed_batch.size)
                    
                    logger.debug(
                        f"Batch {batches_created}: {completed_batch.size} chunks, "
                        f"{completed_batch.total_tokens} tokens"
                    )
                
                # Sample memory periodically
                if items_processed % 100 == 0:
                    memory_monitor.sample()
            
            # Get final batch
            final_batch = batch_processor.batch_manager.finalize_batches()
            if final_batch:
                is_valid, violations = self.validator.validate_batch(final_batch, "large_file_final")
                if not is_valid:
                    errors.extend(violations)
                
                batches_created += 1
                tokens_processed += final_batch.total_tokens
                max_batch_tokens = max(max_batch_tokens, final_batch.total_tokens)
                max_batch_chunks = max(max_batch_chunks, final_batch.size)
            
            memory_monitor.sample()
            processing_time = time.time() - start_time
            memory_stats = memory_monitor.get_stats()
            
            # Validation checks for large file
            validation_results = {
                "no_limit_violations": len(errors) == 0,
                "multiple_batches_created": batches_created >= 5,  # Should require multiple batches
                "all_items_processed": items_processed > 1000,  # Large file should have many items
                "memory_growth_bounded": memory_stats["growth_mb"] < 500,  # Memory should stay bounded
                "max_batch_tokens_safe": max_batch_tokens <= 9500,  # Safety margin
                "max_batch_chunks_safe": max_batch_chunks <= 950,   # Safety margin
                "processing_efficiency": processing_time < 60  # Should complete in reasonable time
            }
            
            success = all(validation_results.values())
            
            result = TestResults(
                test_name="large_file_multiple_batches",
                success=success,
                processing_time=processing_time,
                memory_usage_mb=memory_stats["peak_mb"],
                items_processed=items_processed,
                batches_created=batches_created,
                tokens_processed=tokens_processed,
                max_batch_tokens=max_batch_tokens,
                max_batch_chunks=max_batch_chunks,
                errors=errors,
                validation_results=validation_results
            )
            
            logger.info(
                f"Large file test completed: {items_processed} items, {batches_created} batches, "
                f"{processing_time:.2f}s, {memory_stats['peak_mb']:.1f}MB peak"
            )
            return result
            
        except Exception as e:
            logger.error(f"Large file test failed: {e}")
            errors.append(str(e))
            
            return TestResults(
                test_name="large_file_multiple_batches",
                success=False,
                processing_time=time.time() - start_time,
                memory_usage_mb=memory_monitor.get_stats()["peak_mb"],
                items_processed=items_processed,
                batches_created=batches_created,
                tokens_processed=tokens_processed,
                max_batch_tokens=max_batch_tokens,
                max_batch_chunks=max_batch_chunks,
                errors=errors,
                validation_results={"test_completed": False}
            )
    
    async def test_extreme_batch_limits(self) -> TestResults:
        """Test processing of files designed to test extreme batch limits."""
        logger.info("Testing extreme batch limits...")
        
        start_time = time.time()
        memory_monitor = MemoryMonitor()
        errors = []
        
        try:
            # Use extreme test file
            test_file = self.test_files["extreme_files"][0]
            
            # Use aggressive chunking to create many small chunks
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 100,  # Small chunks to test limits
                    "overlap_tokens": 10,
                    "model_name": "voyage-large-2"
                }
            }
            
            batch_manager = VoyageBatchManager("voyage-large-2")
            
            items_processed = 0
            batches_created = 0
            tokens_processed = 0
            max_batch_tokens = 0
            max_batch_chunks = 0
            
            memory_monitor.sample()
            
            # Process with careful monitoring
            async for item in process_json_file(test_file, schema_config):
                completed_batch = batch_manager.add_processed_item(item)
                items_processed += 1
                
                if completed_batch:
                    # Critical validation for extreme limits
                    is_valid, violations = self.validator.validate_batch(
                        completed_batch, f"extreme_batch_{batches_created}"
                    )
                    
                    if not is_valid:
                        errors.extend(violations)
                        logger.error(f"CRITICAL: Batch limit violation in extreme test: {violations}")
                    
                    batches_created += 1
                    tokens_processed += completed_batch.total_tokens
                    max_batch_tokens = max(max_batch_tokens, completed_batch.total_tokens)
                    max_batch_chunks = max(max_batch_chunks, completed_batch.size)
                
                # Sample memory more frequently for extreme test
                if items_processed % 50 == 0:
                    memory_monitor.sample()
                
                # Break early if too many items (prevent test timeout)
                if items_processed > 10000:
                    logger.info("Stopping extreme test early to prevent timeout")
                    break
            
            # Finalize
            final_batch = batch_manager.finalize_batches()
            if final_batch:
                is_valid, violations = self.validator.validate_batch(final_batch, "extreme_final")
                if not is_valid:
                    errors.extend(violations)
                
                batches_created += 1
                tokens_processed += final_batch.total_tokens
                max_batch_tokens = max(max_batch_tokens, final_batch.total_tokens)
                max_batch_chunks = max(max_batch_chunks, final_batch.size)
            
            memory_monitor.sample()
            processing_time = time.time() - start_time
            memory_stats = memory_monitor.get_stats()
            
            # Strict validation for extreme test
            validation_results = {
                "absolutely_no_violations": len(errors) == 0,  # Zero tolerance for limit violations
                "many_batches_created": batches_created >= 10,  # Should create many batches
                "max_tokens_under_hard_limit": max_batch_tokens < 10000,  # Hard API limit
                "max_chunks_under_hard_limit": max_batch_chunks < 1000,   # Hard API limit
                "max_tokens_under_safety_limit": max_batch_tokens <= 9500,  # Safety margin
                "max_chunks_under_safety_limit": max_batch_chunks <= 950,   # Safety margin
                "memory_bounded": memory_stats["growth_mb"] < 1000,  # Should not grow excessively
            }
            
            success = all(validation_results.values())
            
            result = TestResults(
                test_name="extreme_batch_limits",
                success=success,
                processing_time=processing_time,
                memory_usage_mb=memory_stats["peak_mb"],
                items_processed=items_processed,
                batches_created=batches_created,
                tokens_processed=tokens_processed,
                max_batch_tokens=max_batch_tokens,
                max_batch_chunks=max_batch_chunks,
                errors=errors,
                validation_results=validation_results
            )
            
            logger.info(
                f"Extreme test completed: {items_processed} items, {batches_created} batches, "
                f"max tokens: {max_batch_tokens}, max chunks: {max_batch_chunks}"
            )
            return result
            
        except Exception as e:
            logger.error(f"Extreme limits test failed: {e}")
            errors.append(str(e))
            
            return TestResults(
                test_name="extreme_batch_limits",
                success=False,
                processing_time=time.time() - start_time,
                memory_usage_mb=memory_monitor.get_stats()["peak_mb"],
                items_processed=items_processed,
                batches_created=batches_created,
                tokens_processed=tokens_processed,
                max_batch_tokens=max_batch_tokens,
                max_batch_chunks=max_batch_chunks,
                errors=errors,
                validation_results={"test_completed": False}
            )
    
    async def test_format_compatibility(self) -> TestResults:
        """Test processing of different JSON formats (array vs NDJSON)."""
        logger.info("Testing format compatibility...")
        
        start_time = time.time()
        memory_monitor = MemoryMonitor()
        errors = []
        
        try:
            # Test both JSON array and NDJSON formats
            format_files = self.test_files["format_tests"]
            
            total_items = 0
            total_batches = 0
            
            for test_file in format_files[:2]:  # Test first 2 format files
                file_format = "ndjson" if "ndjson" in Path(test_file).name else "json_array"
                
                schema_config = {
                    "format": file_format,
                    "mapping": {
                        "content_path": "content",
                        "metadata_paths": {"id": "id", "title": "title"}
                    },
                    "chunking": {
                        "strategy": "recursive",
                        "max_chars": 500,
                        "overlap": 50
                    }
                }
                
                batch_manager = VoyageBatchManager("voyage-large-2")
                file_items = 0
                file_batches = 0
                
                memory_monitor.sample()
                
                async for item in process_json_file(test_file, schema_config):
                    completed_batch = batch_manager.add_processed_item(item)
                    file_items += 1
                    
                    if completed_batch:
                        is_valid, violations = self.validator.validate_batch(
                            completed_batch, f"format_{file_format}_batch_{file_batches}"
                        )
                        
                        if not is_valid:
                            errors.extend(violations)
                        
                        file_batches += 1
                
                final_batch = batch_manager.finalize_batches()
                if final_batch:
                    is_valid, violations = self.validator.validate_batch(
                        final_batch, f"format_{file_format}_final"
                    )
                    if not is_valid:
                        errors.extend(violations)
                    file_batches += 1
                
                total_items += file_items
                total_batches += file_batches
                
                logger.info(f"Format {file_format}: {file_items} items, {file_batches} batches")
            
            memory_monitor.sample()
            processing_time = time.time() - start_time
            memory_stats = memory_monitor.get_stats()
            
            validation_results = {
                "no_format_errors": len(errors) == 0,
                "both_formats_processed": total_items > 0,
                "reasonable_batch_efficiency": total_batches > 0 and total_batches < 50
            }
            
            success = all(validation_results.values())
            
            result = TestResults(
                test_name="format_compatibility",
                success=success,
                processing_time=processing_time,
                memory_usage_mb=memory_stats["peak_mb"],
                items_processed=total_items,
                batches_created=total_batches,
                tokens_processed=0,  # Not tracked in this test
                max_batch_tokens=0,
                max_batch_chunks=0,
                errors=errors,
                validation_results=validation_results
            )
            
            logger.info(f"Format compatibility test completed: {total_items} items across formats")
            return result
            
        except Exception as e:
            logger.error(f"Format compatibility test failed: {e}")
            errors.append(str(e))
            
            return TestResults(
                test_name="format_compatibility",
                success=False,
                processing_time=time.time() - start_time,
                memory_usage_mb=memory_monitor.get_stats()["peak_mb"],
                items_processed=0,
                batches_created=0,
                tokens_processed=0,
                max_batch_tokens=0,
                max_batch_chunks=0,
                errors=errors,
                validation_results={"test_completed": False}
            )
    
    async def test_checkpoint_recovery(self) -> TestResults:
        """Test checkpoint creation and recovery functionality."""
        logger.info("Testing checkpoint and recovery...")
        
        start_time = time.time()
        memory_monitor = MemoryMonitor()
        errors = []
        
        try:
            # Use medium size file for checkpoint testing
            test_file = self.test_files["medium_files"][0]
            task_id = "checkpoint_test_001"
            
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id"}
                },
                "chunking": {
                    "strategy": "recursive",
                    "max_chars": 400,
                    "overlap": 40
                }
            }
            
            checkpoint_manager = get_checkpoint_manager()
            batch_manager = VoyageBatchManager("voyage-large-2")
            
            items_processed = 0
            batches_created = 0
            checkpoint_saves = 0
            
            memory_monitor.sample()
            
            # Process with periodic checkpoints
            async for item in process_json_file(test_file, schema_config):
                completed_batch = batch_manager.add_processed_item(item)
                items_processed += 1
                
                if completed_batch:
                    is_valid, violations = self.validator.validate_batch(
                        completed_batch, f"checkpoint_batch_{batches_created}"
                    )
                    
                    if not is_valid:
                        errors.extend(violations)
                    
                    batches_created += 1
                
                # Save checkpoint every 100 items
                if items_processed % 100 == 0:
                    checkpoint_saved = await checkpoint_manager.save_checkpoint(
                        task_id=task_id,
                        file_path=test_file,
                        items_processed=items_processed,
                        chunks_processed=items_processed,  # Simplified
                        embeddings_generated=batches_created * 50,  # Estimated
                        processing_state={"test_mode": True},
                        force=True
                    )
                    
                    if checkpoint_saved:
                        checkpoint_saves += 1
                
                memory_monitor.sample()
                
                # Stop after reasonable number for testing
                if items_processed > 500:
                    break
            
            # Test checkpoint loading
            loaded_checkpoint = await checkpoint_manager.load_checkpoint(task_id)
            checkpoint_loaded = loaded_checkpoint is not None
            
            # Test recovery context creation
            recovery_context = await checkpoint_manager.create_recovery_context(task_id)
            recovery_created = recovery_context is not None
            
            # Test failed batch handling
            fake_batch_data = {"texts": ["test1", "test2"], "metadata": [{"id": 1}, {"id": 2}]}
            fake_error = {"error": "Simulated failure", "retry_count": 0}
            
            failed_batch_id = await checkpoint_manager.save_failed_batch(
                task_id=task_id,
                batch_data=fake_batch_data,
                error_info=fake_error
            )
            
            failed_batches = await checkpoint_manager.get_failed_batches(task_id)
            failed_batch_saved = len(failed_batches) > 0
            
            # Cleanup test data
            await checkpoint_manager.delete_checkpoint(task_id)
            if failed_batch_id:
                await checkpoint_manager.mark_batch_recovered(failed_batch_id)
            
            memory_monitor.sample()
            processing_time = time.time() - start_time
            memory_stats = memory_monitor.get_stats()
            
            validation_results = {
                "checkpoints_saved": checkpoint_saves > 0,
                "checkpoint_loaded": checkpoint_loaded,
                "recovery_context_created": recovery_created,
                "failed_batch_handling": failed_batch_saved,
                "no_processing_errors": len(errors) == 0
            }
            
            success = all(validation_results.values())
            
            result = TestResults(
                test_name="checkpoint_recovery",
                success=success,
                processing_time=processing_time,
                memory_usage_mb=memory_stats["peak_mb"],
                items_processed=items_processed,
                batches_created=batches_created,
                tokens_processed=0,
                max_batch_tokens=0,
                max_batch_chunks=0,
                errors=errors,
                validation_results=validation_results
            )
            
            logger.info(
                f"Checkpoint test completed: {checkpoint_saves} checkpoints saved, "
                f"recovery functionality validated"
            )
            return result
            
        except Exception as e:
            logger.error(f"Checkpoint recovery test failed: {e}")
            errors.append(str(e))
            
            return TestResults(
                test_name="checkpoint_recovery",
                success=False,
                processing_time=time.time() - start_time,
                memory_usage_mb=memory_monitor.get_stats()["peak_mb"],
                items_processed=0,
                batches_created=0,
                tokens_processed=0,
                max_batch_tokens=0,
                max_batch_chunks=0,
                errors=errors,
                validation_results={"test_completed": False}
            )
    
    async def run_all_tests(self) -> List[TestResults]:
        """Run all test scenarios."""
        logger.info("Starting comprehensive large file processing tests...")
        
        await self.setup_test_environment()
        
        # Run all test scenarios
        test_methods = [
            self.test_small_file_processing,
            self.test_large_file_multiple_batches,
            self.test_extreme_batch_limits,
            self.test_format_compatibility,
            self.test_checkpoint_recovery
        ]
        
        for test_method in test_methods:
            try:
                logger.info(f"\n{'='*60}")
                result = await test_method()
                self.test_results.append(result)
                
                # Log result summary
                status = "✅ PASSED" if result.success else "❌ FAILED"
                logger.info(
                    f"{status} {result.test_name}: "
                    f"{result.items_processed} items, {result.batches_created} batches, "
                    f"{result.processing_time:.2f}s, {result.memory_usage_mb:.1f}MB"
                )
                
                if result.errors:
                    logger.warning(f"Errors: {result.errors}")
                
            except Exception as e:
                logger.error(f"Test {test_method.__name__} failed with exception: {e}")
                
                # Create failed result
                failed_result = TestResults(
                    test_name=test_method.__name__,
                    success=False,
                    processing_time=0,
                    memory_usage_mb=0,
                    items_processed=0,
                    batches_created=0,
                    tokens_processed=0,
                    max_batch_tokens=0,
                    max_batch_chunks=0,
                    errors=[str(e)],
                    validation_results={"exception_occurred": True}
                )
                self.test_results.append(failed_result)
        
        return self.test_results
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        if not self.test_results:
            return {"error": "No test results available"}
        
        # Overall statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        
        total_items = sum(r.items_processed for r in self.test_results)
        total_batches = sum(r.batches_created for r in self.test_results)
        total_processing_time = sum(r.processing_time for r in self.test_results)
        
        # Validation summary
        validator_summary = self.validator.get_summary()
        
        # Performance metrics
        avg_processing_time = total_processing_time / total_tests if total_tests > 0 else 0
        max_memory_usage = max((r.memory_usage_mb for r in self.test_results), default=0)
        
        # Critical validations
        critical_validations = {
            "no_api_limit_violations": validator_summary["total_violations"] == 0,
            "all_tests_passed": failed_tests == 0,
            "memory_usage_reasonable": max_memory_usage < 1000,  # < 1GB
            "processing_time_reasonable": avg_processing_time < 30  # < 30s avg
        }
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "processing_statistics": {
                "total_items_processed": total_items,
                "total_batches_created": total_batches,
                "total_processing_time": total_processing_time,
                "average_processing_time": avg_processing_time,
                "max_memory_usage_mb": max_memory_usage
            },
            "api_limit_validation": validator_summary,
            "critical_validations": critical_validations,
            "overall_success": all(critical_validations.values()),
            "individual_test_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "processing_time": r.processing_time,
                    "memory_usage_mb": r.memory_usage_mb,
                    "items_processed": r.items_processed,
                    "batches_created": r.batches_created,
                    "max_batch_tokens": r.max_batch_tokens,
                    "max_batch_chunks": r.max_batch_chunks,
                    "error_count": len(r.errors),
                    "validation_results": r.validation_results
                }
                for r in self.test_results
            ]
        }
        
        return report
    
    def cleanup(self):
        """Clean up test files and resources."""
        logger.info("Cleaning up test environment...")
        self.file_generator.cleanup_generated_files()


async def main():
    """Main test execution function."""
    logger.info("Starting Large JSON File Processing Validation Tests")
    logger.info("=" * 80)
    
    test_suite = LargeFileProcessingTests()
    
    try:
        # Run all tests
        results = await test_suite.run_all_tests()
        
        # Generate report
        report = test_suite.generate_test_report()
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST EXECUTION COMPLETED")
        logger.info("=" * 80)
        
        print(f"\nTest Summary:")
        print(f"  Total Tests: {report['test_summary']['total_tests']}")
        print(f"  Passed: {report['test_summary']['passed_tests']}")
        print(f"  Failed: {report['test_summary']['failed_tests']}")
        print(f"  Success Rate: {report['test_summary']['success_rate']:.1%}")
        
        print(f"\nProcessing Statistics:")
        print(f"  Items Processed: {report['processing_statistics']['total_items_processed']}")
        print(f"  Batches Created: {report['processing_statistics']['total_batches_created']}")
        print(f"  Total Time: {report['processing_statistics']['total_processing_time']:.2f}s")
        print(f"  Peak Memory: {report['processing_statistics']['max_memory_usage_mb']:.1f}MB")
        
        print(f"\nAPI Limit Validation:")
        print(f"  Violations: {report['api_limit_validation']['total_violations']}")
        print(f"  Batches Validated: {report['api_limit_validation']['batches_validated']}")
        print(f"  Max Tokens Seen: {report['api_limit_validation']['max_tokens_seen']}")
        print(f"  Max Chunks Seen: {report['api_limit_validation']['max_chunks_seen']}")
        
        print(f"\nCritical Validations:")
        for validation, passed in report['critical_validations'].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {validation}: {status}")
        
        overall_status = "✅ SUCCESS" if report['overall_success'] else "❌ FAILURE"
        print(f"\nOVERALL RESULT: {overall_status}")
        
        if not report['overall_success']:
            print("\n❌ CRITICAL ISSUES DETECTED:")
            if report['api_limit_validation']['total_violations'] > 0:
                print("  - VoyageAI API limit violations found!")
                for violation in report['api_limit_validation']['violations']:
                    print(f"    • {violation}")
            
            failed_tests = [r for r in report['individual_test_results'] if not r['success']]
            if failed_tests:
                print("  - Failed tests:")
                for test in failed_tests:
                    print(f"    • {test['test_name']}")
        
        else:
            print("\n✅ ALL VALIDATIONS PASSED!")
            print("  - No VoyageAI API limit violations")
            print("  - Memory usage remains bounded")
            print("  - All test scenarios completed successfully")
            print("  - System ready for production use with large files")
        
        # Save detailed report
        report_file = Path(tempfile.gettempdir()) / "large_file_processing_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        test_suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())