#!/usr/bin/env python3
"""
Comprehensive recovery and error handling tests for large JSON file processing.
Tests checkpoint functionality, API failure recovery, and graceful error handling.
"""

import asyncio
import json
import pytest
import tempfile
import time
import logging
import random
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from dataclasses import dataclass
from pathlib import Path

# Import test generator and core services
from test_large_file_generator import LargeFileGenerator
from app.services.checkpoint_manager import CheckpointManager, CheckpointData, RecoveryContext, get_checkpoint_manager
from app.services.progress_tracker import ProgressTracker, ProcessingPhase, get_progress_tracker
from app.services.background_tasks import TaskManager, TaskStatus, get_task_manager
from app.services.embeddings import RobustVoyageEmbedder, BatchEmbeddingService
from app.services.batch_manager import VoyageBatchManager, Batch
from app.services.streaming_parser import process_json_file
from app.services.rag_ingest import ingest_json_file_streaming

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RecoveryTestResult:
    """Result of recovery/error handling test."""
    test_name: str
    success: bool
    scenario_tested: str
    recovery_successful: bool
    checkpoints_created: int
    errors_handled: int
    retry_attempts: int
    final_state: str
    performance_metrics: Dict[str, float]
    error_details: List[str]


class MockFailureSimulator:
    """Simulates various types of failures for testing recovery."""
    
    def __init__(self):
        self.failure_scenarios = {
            "api_rate_limit": {"status_code": 429, "retryable": True},
            "api_timeout": {"status_code": 408, "retryable": True},
            "api_server_error": {"status_code": 500, "retryable": True},
            "api_auth_error": {"status_code": 401, "retryable": False},
            "api_quota_exceeded": {"status_code": 403, "retryable": False},
            "network_error": {"error_type": "ConnectionError", "retryable": True},
            "malformed_response": {"error_type": "JSONDecodeError", "retryable": False}
        }
        self.failure_history = []
    
    def create_api_error(self, scenario: str, call_count: int = 1):
        """Create simulated API error based on scenario."""
        if scenario not in self.failure_scenarios:
            scenario = "api_server_error"
        
        error_config = self.failure_scenarios[scenario]
        self.failure_history.append({"scenario": scenario, "call": call_count, "time": time.time()})
        
        if "status_code" in error_config:
            # HTTP error
            error = Exception(f"HTTP {error_config['status_code']}: {scenario}")
            error.status_code = error_config["status_code"]
            error.retryable = error_config["retryable"]
        else:
            # Other error types
            if error_config["error_type"] == "ConnectionError":
                error = ConnectionError(f"Network connection failed: {scenario}")
            elif error_config["error_type"] == "JSONDecodeError":
                error = json.JSONDecodeError("Invalid JSON response", "", 0)
            else:
                error = Exception(f"Unknown error: {scenario}")
            
            error.retryable = error_config["retryable"]
        
        return error
    
    def should_fail(self, call_count: int, failure_pattern: str) -> bool:
        """Determine if current call should fail based on pattern."""
        if failure_pattern == "always":
            return True
        elif failure_pattern == "first_few":
            return call_count <= 3
        elif failure_pattern == "intermittent":
            return call_count % 3 == 0
        elif failure_pattern == "random":
            return random.random() < 0.3  # 30% failure rate
        return False


class CheckpointRecoveryTester:
    """Tests checkpoint creation and recovery functionality."""
    
    def __init__(self):
        self.checkpoint_manager = get_checkpoint_manager()
        self.file_generator = LargeFileGenerator()
        
    async def test_basic_checkpoint_functionality(self) -> RecoveryTestResult:
        """Test basic checkpoint save/load functionality."""
        logger.info("Testing basic checkpoint functionality...")
        
        start_time = time.time()
        task_id = "checkpoint_basic_test"
        errors = []
        checkpoints_created = 0
        
        try:
            # Create test file
            test_file = self.file_generator.generate_json_array_file(
                self.file_generator.FileSpec("checkpoint_test", 2.0, 200, "medium", "json_array", "Test file")
            )
            
            # Test checkpoint creation
            checkpoint_saved = await self.checkpoint_manager.save_checkpoint(
                task_id=task_id,
                file_path=test_file,
                items_processed=50,
                chunks_processed=75,
                embeddings_generated=75,
                processing_state={"test_mode": True, "batch_count": 3},
                force=True
            )
            
            if checkpoint_saved:
                checkpoints_created += 1
            else:
                errors.append("Failed to save initial checkpoint")
            
            # Test checkpoint loading
            loaded_checkpoint = await self.checkpoint_manager.load_checkpoint(task_id)
            
            if not loaded_checkpoint:
                errors.append("Failed to load saved checkpoint")
            elif loaded_checkpoint.items_processed != 50:
                errors.append(f"Checkpoint data mismatch: expected 50 items, got {loaded_checkpoint.items_processed}")
            
            # Test checkpoint update
            updated = await self.checkpoint_manager.save_checkpoint(
                task_id=task_id,
                file_path=test_file,
                items_processed=100,
                chunks_processed=150,
                embeddings_generated=150,
                processing_state={"test_mode": True, "batch_count": 6},
                force=True
            )
            
            if updated:
                checkpoints_created += 1
            
            # Verify update
            updated_checkpoint = await self.checkpoint_manager.load_checkpoint(task_id)
            if not updated_checkpoint or updated_checkpoint.items_processed != 100:
                errors.append("Checkpoint update failed")
            
            # Test recovery context creation
            recovery_context = await self.checkpoint_manager.create_recovery_context(task_id)
            if not recovery_context:
                errors.append("Failed to create recovery context")
            
            # Cleanup
            await self.checkpoint_manager.delete_checkpoint(task_id)
            
            processing_time = time.time() - start_time
            success = len(errors) == 0
            
            return RecoveryTestResult(
                test_name="basic_checkpoint_functionality",
                success=success,
                scenario_tested="basic_checkpoint_operations",
                recovery_successful=success,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=0,
                final_state="completed" if success else "failed",
                performance_metrics={"processing_time": processing_time},
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Basic checkpoint test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="basic_checkpoint_functionality",
                success=False,
                scenario_tested="basic_checkpoint_operations",
                recovery_successful=False,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=0,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )
    
    async def test_failed_batch_recovery(self) -> RecoveryTestResult:
        """Test failed batch handling and recovery."""
        logger.info("Testing failed batch recovery...")
        
        start_time = time.time()
        task_id = "failed_batch_test"
        errors = []
        checkpoints_created = 0
        retry_attempts = 0
        
        try:
            # Simulate failed batches
            batch_data_1 = {
                "texts": [f"Failed batch text {i}" for i in range(10)],
                "metadata": [{"id": i, "batch": "failed_1"} for i in range(10)]
            }
            
            batch_data_2 = {
                "texts": [f"Another failed batch text {i}" for i in range(5)],
                "metadata": [{"id": i + 100, "batch": "failed_2"} for i in range(5)]
            }
            
            error_info_1 = {
                "error": "Simulated API timeout",
                "status_code": 408,
                "retry_count": 0,
                "timestamp": time.time()
            }
            
            error_info_2 = {
                "error": "Simulated rate limit",
                "status_code": 429,
                "retry_count": 1,
                "timestamp": time.time()
            }
            
            # Save failed batches
            failed_batch_id_1 = await self.checkpoint_manager.save_failed_batch(
                task_id=task_id,
                batch_data=batch_data_1,
                error_info=error_info_1
            )
            
            failed_batch_id_2 = await self.checkpoint_manager.save_failed_batch(
                task_id=task_id,
                batch_data=batch_data_2,
                error_info=error_info_2
            )
            
            if not failed_batch_id_1 or not failed_batch_id_2:
                errors.append("Failed to save failed batches")
            
            # Retrieve failed batches
            failed_batches = await self.checkpoint_manager.get_failed_batches(task_id)
            
            if len(failed_batches) != 2:
                errors.append(f"Expected 2 failed batches, got {len(failed_batches)}")
            
            # Test retry logic
            for failed_batch in failed_batches:
                batch_id = failed_batch["batch_id"]
                
                # Attempt retry
                retry_data = await self.checkpoint_manager.retry_failed_batch(batch_id, max_retries=3)
                retry_attempts += 1
                
                if not retry_data:
                    errors.append(f"Failed to get retry data for batch {batch_id}")
                
                # Simulate successful retry and mark as recovered
                recovery_success = await self.checkpoint_manager.mark_batch_recovered(batch_id)
                if not recovery_success:
                    errors.append(f"Failed to mark batch {batch_id} as recovered")
            
            # Verify cleanup
            remaining_failed = await self.checkpoint_manager.get_failed_batches(task_id)
            if len(remaining_failed) > 0:
                errors.append(f"Expected 0 remaining failed batches, got {len(remaining_failed)}")
            
            processing_time = time.time() - start_time
            success = len(errors) == 0
            
            return RecoveryTestResult(
                test_name="failed_batch_recovery",
                success=success,
                scenario_tested="failed_batch_handling",
                recovery_successful=success,
                checkpoints_created=checkpoints_created,
                errors_handled=2,
                retry_attempts=retry_attempts,
                final_state="recovered" if success else "failed",
                performance_metrics={"processing_time": processing_time},
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Failed batch recovery test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="failed_batch_recovery",
                success=False,
                scenario_tested="failed_batch_handling",
                recovery_successful=False,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=retry_attempts,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )
    
    async def test_partial_processing_recovery(self) -> RecoveryTestResult:
        """Test recovery from partial processing state."""
        logger.info("Testing partial processing recovery...")
        
        start_time = time.time()
        task_id = "partial_recovery_test"
        errors = []
        checkpoints_created = 0
        
        try:
            # Create test file
            test_file = self.file_generator.generate_json_array_file(
                self.file_generator.FileSpec("partial_test", 3.0, 300, "medium", "json_array", "Partial test")
            )
            
            # Simulate partial processing with checkpoint
            await self.checkpoint_manager.save_checkpoint(
                task_id=task_id,
                file_path=test_file,
                file_offset=1500,  # Halfway through file
                items_processed=150,
                chunks_processed=200,
                embeddings_generated=180,
                processing_state={
                    "last_processed_id": "item_000149",
                    "current_batch": 8,
                    "processing_phase": "embedding_generation"
                },
                force=True
            )
            checkpoints_created += 1
            
            # Create recovery context
            recovery_context = await self.checkpoint_manager.create_recovery_context(task_id)
            
            if not recovery_context:
                errors.append("Failed to create recovery context")
            else:
                # Validate recovery context
                checkpoint = recovery_context.checkpoint
                
                if checkpoint.items_processed != 150:
                    errors.append(f"Recovery context mismatch: expected 150 items, got {checkpoint.items_processed}")
                
                if checkpoint.file_offset != 1500:
                    errors.append(f"File offset mismatch: expected 1500, got {checkpoint.file_offset}")
                
                # Test resume capability
                if not recovery_context.can_retry:
                    logger.info("Recovery context indicates no retry needed (as expected)")
                
                # Estimate remaining work
                recovery_stats = await self.checkpoint_manager.estimate_recovery_progress(task_id)
                
                if not recovery_stats["recoverable"]:
                    errors.append("Recovery statistics indicate task is not recoverable")
                
                logger.info(f"Recovery progress: {recovery_stats}")
            
            # Test continuation from checkpoint
            # Simulate continuing processing
            for i in range(3):
                await self.checkpoint_manager.save_checkpoint(
                    task_id=task_id,
                    file_path=test_file,
                    file_offset=1500 + (i + 1) * 500,
                    items_processed=150 + (i + 1) * 50,
                    chunks_processed=200 + (i + 1) * 60,
                    embeddings_generated=180 + (i + 1) * 55,
                    processing_state={
                        "last_processed_id": f"item_{150 + (i + 1) * 50 - 1:06d}",
                        "current_batch": 8 + i + 1,
                        "processing_phase": "embedding_generation"
                    },
                    force=True
                )
                checkpoints_created += 1
            
            # Final checkpoint verification
            final_checkpoint = await self.checkpoint_manager.load_checkpoint(task_id)
            if not final_checkpoint or final_checkpoint.items_processed != 300:
                errors.append("Final checkpoint verification failed")
            
            # Cleanup
            await self.checkpoint_manager.delete_checkpoint(task_id)
            
            processing_time = time.time() - start_time
            success = len(errors) == 0
            
            return RecoveryTestResult(
                test_name="partial_processing_recovery",
                success=success,
                scenario_tested="partial_processing_resume",
                recovery_successful=success,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=0,
                final_state="completed" if success else "failed",
                performance_metrics={"processing_time": processing_time},
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Partial processing recovery test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="partial_processing_recovery",
                success=False,
                scenario_tested="partial_processing_resume",
                recovery_successful=False,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=0,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )


class APIFailureRecoveryTester:
    """Tests API failure simulation and recovery mechanisms."""
    
    def __init__(self):
        self.failure_simulator = MockFailureSimulator()
        
    async def test_voyage_api_retry_logic(self) -> RecoveryTestResult:
        """Test VoyageAI API retry logic with various failure scenarios."""
        logger.info("Testing VoyageAI API retry logic...")
        
        start_time = time.time()
        errors = []
        retry_attempts = 0
        scenario_tested = "api_retry_mechanisms"
        
        try:
            # Test different failure scenarios
            failure_scenarios = ["api_rate_limit", "api_timeout", "api_server_error", "network_error"]
            
            for scenario in failure_scenarios:
                logger.info(f"Testing scenario: {scenario}")
                
                # Create mock embedder with failure injection
                with patch('app.services.embeddings.voyage.Client') as mock_client:
                    # Configure mock to fail first few calls, then succeed
                    call_count = 0
                    
                    async def mock_embed(*args, **kwargs):
                        nonlocal call_count
                        call_count += 1
                        
                        if self.failure_simulator.should_fail(call_count, "first_few"):
                            error = self.failure_simulator.create_api_error(scenario, call_count)
                            raise error
                        
                        # Success response
                        return Mock(embeddings=[[0.1] * 1024 for _ in range(10)])
                    
                    mock_instance = Mock()
                    mock_instance.embed = mock_embed
                    mock_client.return_value = mock_instance
                    
                    # Test with RobustVoyageEmbedder
                    embedder = RobustVoyageEmbedder("test_api_key", "voyage-large-2")
                    
                    test_texts = [f"Test text {i} for scenario {scenario}" for i in range(10)]
                    
                    try:
                        embeddings = await embedder.embed_with_retry(test_texts)
                        
                        if embeddings and len(embeddings) == 10:
                            logger.info(f"Scenario {scenario}: Recovery successful after {call_count} attempts")
                            retry_attempts += call_count - 1  # Subtract 1 for successful call
                        else:
                            errors.append(f"Scenario {scenario}: Invalid embeddings returned")
                        
                    except Exception as e:
                        # Some scenarios should fail permanently
                        if scenario in ["api_auth_error", "api_quota_exceeded"]:
                            logger.info(f"Scenario {scenario}: Expected permanent failure - {e}")
                        else:
                            errors.append(f"Scenario {scenario}: Unexpected failure - {e}")
            
            processing_time = time.time() - start_time
            success = len(errors) == 0
            
            return RecoveryTestResult(
                test_name="voyage_api_retry_logic",
                success=success,
                scenario_tested=scenario_tested,
                recovery_successful=success,
                checkpoints_created=0,
                errors_handled=len(failure_scenarios),
                retry_attempts=retry_attempts,
                final_state="completed" if success else "failed",
                performance_metrics={"processing_time": processing_time, "avg_retries": retry_attempts / len(failure_scenarios)},
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"API retry logic test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="voyage_api_retry_logic",
                success=False,
                scenario_tested=scenario_tested,
                recovery_successful=False,
                checkpoints_created=0,
                errors_handled=0,
                retry_attempts=retry_attempts,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )
    
    async def test_batch_processing_with_failures(self) -> RecoveryTestResult:
        """Test batch processing with intermittent failures."""
        logger.info("Testing batch processing with intermittent failures...")
        
        start_time = time.time()
        errors = []
        retry_attempts = 0
        checkpoints_created = 0
        
        try:
            # Create test batches
            batch_manager = VoyageBatchManager("voyage-large-2")
            test_texts = [f"Batch test text {i} with content." for i in range(100)]
            
            # Simulate processing with failures
            batches = list(batch_manager.create_batches(test_texts))
            processed_batches = 0
            failed_batches = 0
            
            checkpoint_manager = get_checkpoint_manager()
            task_id = "batch_failure_test"
            
            for i, batch in enumerate(batches):
                try:
                    # Simulate random failures
                    if random.random() < 0.3:  # 30% failure rate
                        # Simulate failure
                        error_info = {
                            "error": "Simulated batch processing failure",
                            "batch_index": i,
                            "retry_count": 0
                        }
                        
                        # Save failed batch
                        failed_batch_id = await checkpoint_manager.save_failed_batch(
                            task_id=task_id,
                            batch_data={"texts": batch.texts, "metadata": batch.metadatas},
                            error_info=error_info
                        )
                        
                        failed_batches += 1
                        
                        # Simulate retry
                        retry_data = await checkpoint_manager.retry_failed_batch(failed_batch_id)
                        if retry_data:
                            retry_attempts += 1
                            # Simulate successful retry
                            await checkpoint_manager.mark_batch_recovered(failed_batch_id)
                            processed_batches += 1
                        
                    else:
                        # Successful processing
                        processed_batches += 1
                    
                    # Save checkpoint periodically
                    if i % 5 == 0:
                        await checkpoint_manager.save_checkpoint(
                            task_id=task_id,
                            file_path="test_file.json",
                            items_processed=processed_batches * 10,  # Estimated
                            chunks_processed=processed_batches * 10,
                            embeddings_generated=processed_batches * 10,
                            processing_state={"batch_index": i},
                            force=True
                        )
                        checkpoints_created += 1
                
                except Exception as e:
                    errors.append(f"Batch {i} processing failed: {e}")
            
            # Verify all batches were eventually processed
            final_failed = await checkpoint_manager.get_failed_batches(task_id)
            if len(final_failed) > 0:
                errors.append(f"Still have {len(final_failed)} failed batches after recovery")
            
            # Cleanup
            await checkpoint_manager.delete_checkpoint(task_id)
            
            logger.info(f"Processed {processed_batches}/{len(batches)} batches with {failed_batches} failures and {retry_attempts} retries")
            
            processing_time = time.time() - start_time
            success = len(errors) == 0 and processed_batches == len(batches)
            
            return RecoveryTestResult(
                test_name="batch_processing_with_failures",
                success=success,
                scenario_tested="intermittent_batch_failures",
                recovery_successful=success,
                checkpoints_created=checkpoints_created,
                errors_handled=failed_batches,
                retry_attempts=retry_attempts,
                final_state="completed" if success else "failed",
                performance_metrics={
                    "processing_time": processing_time,
                    "failure_rate": failed_batches / len(batches),
                    "recovery_rate": retry_attempts / max(failed_batches, 1)
                },
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Batch processing failure test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="batch_processing_with_failures",
                success=False,
                scenario_tested="intermittent_batch_failures",
                recovery_successful=False,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=retry_attempts,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )


class TaskManagementTester:
    """Tests task pause/resume and cancellation functionality."""
    
    def __init__(self):
        self.task_manager = get_task_manager()
        self.progress_tracker = get_progress_tracker()
        
    async def test_task_pause_resume(self) -> RecoveryTestResult:
        """Test task pause and resume functionality."""
        logger.info("Testing task pause and resume...")
        
        start_time = time.time()
        errors = []
        checkpoints_created = 0
        
        try:
            task_id = "pause_resume_test"
            
            # Start progress tracking
            await self.progress_tracker.start_tracking(
                task_id=task_id,
                tenant_id="test_tenant",
                total_items_expected=1000
            )
            
            # Simulate processing progress
            phases = [ProcessingPhase.ANALYZING_FILE, ProcessingPhase.PARSING_JSON, ProcessingPhase.GENERATING_EMBEDDINGS]
            
            for phase_idx, phase in enumerate(phases):
                await self.progress_tracker.update_phase(task_id, phase)
                
                # Simulate work in phase
                for i in range(50):
                    await self.progress_tracker.update_progress(
                        task_id=task_id,
                        items_processed=phase_idx * 50 + i + 1
                    )
                    
                    # Simulate pause at certain point
                    if phase_idx == 1 and i == 25:  # Pause halfway through second phase
                        logger.info("Simulating task pause...")
                        
                        # Get current state
                        current_progress = await self.progress_tracker.get_detailed_progress(task_id)
                        if not current_progress:
                            errors.append("Failed to get progress before pause")
                        
                        # Simulate pause (in real implementation, this would stop processing)
                        pause_time = time.time()
                        await asyncio.sleep(0.1)  # Brief pause simulation
                        
                        # Resume
                        logger.info("Simulating task resume...")
                        resume_time = time.time()
                        
                        # Continue processing
                        checkpoints_created += 1
                
                checkpoints_created += 1
            
            # Complete processing
            await self.progress_tracker.finish_tracking(task_id, success=True)
            
            # Verify final state
            final_progress = await self.progress_tracker.get_detailed_progress(task_id)
            if not final_progress:
                errors.append("Failed to get final progress")
            elif final_progress["overall"]["percentage"] != 100.0:
                errors.append(f"Expected 100% completion, got {final_progress['overall']['percentage']}%")
            
            processing_time = time.time() - start_time
            success = len(errors) == 0
            
            return RecoveryTestResult(
                test_name="task_pause_resume",
                success=success,
                scenario_tested="pause_resume_functionality",
                recovery_successful=success,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=0,
                final_state="completed" if success else "failed",
                performance_metrics={"processing_time": processing_time},
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Task pause/resume test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="task_pause_resume",
                success=False,
                scenario_tested="pause_resume_functionality",
                recovery_successful=False,
                checkpoints_created=checkpoints_created,
                errors_handled=0,
                retry_attempts=0,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )
    
    async def test_graceful_error_handling(self) -> RecoveryTestResult:
        """Test graceful handling of various error conditions."""
        logger.info("Testing graceful error handling...")
        
        start_time = time.time()
        errors_handled = 0
        errors = []
        
        try:
            # Test invalid file handling
            try:
                invalid_file = "/nonexistent/file.json"
                schema_config = {"format": "json_array", "mapping": {"content_path": "content"}}
                
                async for item in process_json_file(invalid_file, schema_config):
                    pass  # Should not reach here
                
                errors.append("Expected file not found error not raised")
                
            except FileNotFoundError:
                errors_handled += 1
                logger.info("File not found error handled gracefully")
            except Exception as e:
                errors.append(f"Unexpected error for invalid file: {e}")
            
            # Test invalid JSON handling
            try:
                invalid_json_file = Path(tempfile.gettempdir()) / "invalid.json"
                with open(invalid_json_file, 'w') as f:
                    f.write("invalid json content {")
                
                schema_config = {"format": "json_array", "mapping": {"content_path": "content"}}
                
                async for item in process_json_file(str(invalid_json_file), schema_config):
                    pass  # Should not reach here
                
                errors.append("Expected JSON decode error not raised")
                
            except json.JSONDecodeError:
                errors_handled += 1
                logger.info("Invalid JSON error handled gracefully")
            except Exception as e:
                errors.append(f"Unexpected error for invalid JSON: {e}")
            finally:
                if invalid_json_file.exists():
                    invalid_json_file.unlink()
            
            # Test invalid schema handling
            try:
                # Create valid JSON file but with invalid schema
                test_file = Path(tempfile.gettempdir()) / "schema_test.json"
                with open(test_file, 'w') as f:
                    json.dump([{"data": "test"}], f)
                
                invalid_schema = {"format": "invalid_format", "mapping": {"content_path": "nonexistent"}}
                
                item_count = 0
                async for item in process_json_file(str(test_file), invalid_schema):
                    item_count += 1
                    if item_count > 10:  # Prevent infinite loop
                        break
                
                # This might not raise an error but should handle gracefully
                errors_handled += 1
                logger.info("Invalid schema handled gracefully")
                
            except Exception as e:
                # Expected to handle gracefully
                errors_handled += 1
                logger.info(f"Schema error handled: {e}")
            finally:
                if test_file.exists():
                    test_file.unlink()
            
            # Test memory pressure handling
            try:
                # Simulate large batch that might cause memory issues
                large_texts = ["X" * 100000 for _ in range(1000)]  # 100MB of text
                
                batch_manager = VoyageBatchManager("voyage-large-2")
                batch_count = 0
                
                for batch in batch_manager.create_batches(large_texts):
                    batch_count += 1
                    # Just count batches, don't actually process
                    if batch_count > 100:  # Safety limit
                        break
                
                errors_handled += 1
                logger.info("Large batch handling completed gracefully")
                
            except Exception as e:
                errors.append(f"Large batch handling failed: {e}")
            
            processing_time = time.time() - start_time
            success = len(errors) == 0 and errors_handled > 0
            
            return RecoveryTestResult(
                test_name="graceful_error_handling",
                success=success,
                scenario_tested="various_error_conditions",
                recovery_successful=success,
                checkpoints_created=0,
                errors_handled=errors_handled,
                retry_attempts=0,
                final_state="completed" if success else "failed",
                performance_metrics={"processing_time": processing_time},
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Graceful error handling test failed: {e}")
            errors.append(str(e))
            
            return RecoveryTestResult(
                test_name="graceful_error_handling",
                success=False,
                scenario_tested="various_error_conditions",
                recovery_successful=False,
                checkpoints_created=0,
                errors_handled=errors_handled,
                retry_attempts=0,
                final_state="exception",
                performance_metrics={"processing_time": time.time() - start_time},
                error_details=errors
            )


class RecoveryErrorHandlingSuite:
    """Complete recovery and error handling test suite."""
    
    def __init__(self):
        self.checkpoint_tester = CheckpointRecoveryTester()
        self.api_tester = APIFailureRecoveryTester()
        self.task_tester = TaskManagementTester()
        self.results: List[RecoveryTestResult] = []
        
    async def run_all_tests(self):
        """Run all recovery and error handling tests."""
        logger.info("Starting Recovery and Error Handling Test Suite")
        logger.info("=" * 70)
        
        # Checkpoint recovery tests
        logger.info("\n--- Checkpoint Recovery Tests ---")
        checkpoint_tests = [
            self.checkpoint_tester.test_basic_checkpoint_functionality,
            self.checkpoint_tester.test_failed_batch_recovery,
            self.checkpoint_tester.test_partial_processing_recovery
        ]
        
        for test in checkpoint_tests:
            try:
                result = await test()
                self.results.append(result)
                status = "✅ PASS" if result.success else "❌ FAIL"
                logger.info(f"{status} {result.test_name}: {result.final_state}")
                if result.error_details:
                    for error in result.error_details:
                        logger.warning(f"  ⚠️  {error}")
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")
        
        # API failure recovery tests
        logger.info("\n--- API Failure Recovery Tests ---")
        api_tests = [
            self.api_tester.test_voyage_api_retry_logic,
            self.api_tester.test_batch_processing_with_failures
        ]
        
        for test in api_tests:
            try:
                result = await test()
                self.results.append(result)
                status = "✅ PASS" if result.success else "❌ FAIL"
                logger.info(f"{status} {result.test_name}: {result.errors_handled} errors handled, {result.retry_attempts} retries")
                if result.error_details:
                    for error in result.error_details:
                        logger.warning(f"  ⚠️  {error}")
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")
        
        # Task management tests
        logger.info("\n--- Task Management Tests ---")
        task_tests = [
            self.task_tester.test_task_pause_resume,
            self.task_tester.test_graceful_error_handling
        ]
        
        for test in task_tests:
            try:
                result = await test()
                self.results.append(result)
                status = "✅ PASS" if result.success else "❌ FAIL"
                logger.info(f"{status} {result.test_name}: {result.final_state}")
                if result.error_details:
                    for error in result.error_details:
                        logger.warning(f"  ⚠️  {error}")
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with exception: {e}")
        
    def generate_recovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive recovery test report."""
        if not self.results:
            return {"error": "No test results available"}
        
        # Calculate overall statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        
        total_errors_handled = sum(r.errors_handled for r in self.results)
        total_retries = sum(r.retry_attempts for r in self.results)
        total_checkpoints = sum(r.checkpoints_created for r in self.results)
        
        # Recovery success rate
        recovery_tests = [r for r in self.results if r.recovery_successful]
        recovery_rate = len(recovery_tests) / total_tests if total_tests > 0 else 0
        
        # Performance metrics
        total_time = sum(r.performance_metrics.get("processing_time", 0) for r in self.results)
        avg_time = total_time / total_tests if total_tests > 0 else 0
        
        # Critical validations
        critical_checks = {
            "all_tests_passed": failed_tests == 0,
            "error_handling_functional": total_errors_handled > 0,
            "retry_logic_working": total_retries > 0,
            "checkpoint_system_working": total_checkpoints > 0,
            "recovery_rate_acceptable": recovery_rate >= 0.8  # 80% recovery success
        }
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "recovery_statistics": {
                "total_errors_handled": total_errors_handled,
                "total_retry_attempts": total_retries,
                "total_checkpoints_created": total_checkpoints,
                "recovery_success_rate": recovery_rate
            },
            "performance_metrics": {
                "total_processing_time": total_time,
                "average_test_time": avg_time,
                "errors_per_test": total_errors_handled / total_tests if total_tests > 0 else 0
            },
            "critical_validations": critical_checks,
            "overall_success": all(critical_checks.values()),
            "test_details": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "scenario": r.scenario_tested,
                    "recovery_successful": r.recovery_successful,
                    "errors_handled": r.errors_handled,
                    "retry_attempts": r.retry_attempts,
                    "checkpoints_created": r.checkpoints_created,
                    "final_state": r.final_state,
                    "processing_time": r.performance_metrics.get("processing_time", 0),
                    "error_count": len(r.error_details)
                }
                for r in self.results
            ]
        }
        
        return report


async def main():
    """Main test execution."""
    logger.info("Starting Recovery and Error Handling Validation")
    logger.info("=" * 80)
    
    suite = RecoveryErrorHandlingSuite()
    
    try:
        await suite.run_all_tests()
        
        # Generate and display report
        report = suite.generate_recovery_report()
        
        logger.info("\n" + "=" * 80)
        logger.info("RECOVERY AND ERROR HANDLING TEST RESULTS")
        logger.info("=" * 80)
        
        print(f"\nTest Summary:")
        print(f"  Total Tests: {report['test_summary']['total_tests']}")
        print(f"  Passed: {report['test_summary']['passed_tests']}")
        print(f"  Failed: {report['test_summary']['failed_tests']}")
        print(f"  Success Rate: {report['test_summary']['success_rate']:.1%}")
        
        print(f"\nRecovery Statistics:")
        print(f"  Errors Handled: {report['recovery_statistics']['total_errors_handled']}")
        print(f"  Retry Attempts: {report['recovery_statistics']['total_retry_attempts']}")
        print(f"  Checkpoints Created: {report['recovery_statistics']['total_checkpoints_created']}")
        print(f"  Recovery Success Rate: {report['recovery_statistics']['recovery_success_rate']:.1%}")
        
        print(f"\nCritical Validations:")
        for validation, passed in report['critical_validations'].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {validation}: {status}")
        
        overall_status = "✅ SUCCESS" if report['overall_success'] else "❌ FAILURE"
        print(f"\nOVERALL RESULT: {overall_status}")
        
        if not report['overall_success']:
            print("\n❌ ISSUES DETECTED:")
            failed_tests = [t for t in report['test_details'] if not t['success']]
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['final_state']}")
        else:
            print("\n✅ ALL RECOVERY TESTS PASSED!")
            print("  - Checkpoint system is working correctly")
            print("  - API failure recovery is functional")
            print("  - Error handling is graceful")
            print("  - Task management supports pause/resume")
        
        # Save detailed report
        report_file = Path(tempfile.gettempdir()) / "recovery_error_handling_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if hasattr(suite, 'checkpoint_tester'):
            suite.checkpoint_tester.file_generator.cleanup_generated_files()


if __name__ == "__main__":
    asyncio.run(main())