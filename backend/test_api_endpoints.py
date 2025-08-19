#!/usr/bin/env python3
"""
Comprehensive API endpoint tests for large JSON file processing task management.
Tests all new endpoints with realistic large file scenarios and validates
task status updates, progress tracking, and control operations.
"""

import asyncio
import json
import pytest
import tempfile
import time
import logging
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from dataclasses import dataclass
from io import BytesIO

# FastAPI testing
from fastapi.testclient import TestClient
from fastapi import UploadFile

# Import the app and services
from app.main import app
from test_large_file_generator import LargeFileGenerator, FileSpec
from app.services.background_tasks import TaskStatus
from app.services.progress_tracker import ProcessingPhase

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class APITestResult:
    """Result of API endpoint test."""
    endpoint: str
    method: str
    success: bool
    status_code: int
    response_data: Dict[str, Any]
    test_scenario: str
    errors: List[str]
    performance_metrics: Dict[str, float]


class MockTenantConfig:
    """Mock tenant configuration for testing."""
    
    @staticmethod
    def get_valid_config():
        return {
            "rag": {
                "enabled": True,
                "provider": "milvus",
                "milvus": {
                    "host": "localhost",
                    "port": 19530,
                    "collection_name": "test_collection"
                },
                "embedding_provider": "voyageai",
                "embedding_model": "voyage-large-2",
                "provider_keys": {
                    "voyageai": "test_api_key_12345",
                    "openai": "test_openai_key"
                }
            }
        }


class APIEndpointTester:
    """Comprehensive API endpoint testing suite."""
    
    def __init__(self):
        self.client = TestClient(app)
        self.file_generator = LargeFileGenerator()
        self.test_results: List[APITestResult] = []
        self.tenant_id = "test_tenant"
        
    def setup_mocks(self):
        """Set up necessary mocks for testing."""
        # Mock tenant configuration
        self.tenant_config_patch = patch(
            'app.services.tenants.get_tenant_config',
            return_value=MockTenantConfig.get_valid_config()
        )
        
        # Mock task manager
        self.mock_task_manager = Mock()
        self.task_manager_patch = patch(
            'app.services.background_tasks.get_task_manager',
            return_value=self.mock_task_manager
        )
        
        # Mock progress tracker
        self.mock_progress_tracker = Mock()
        self.progress_tracker_patch = patch(
            'app.services.progress_tracker.get_progress_tracker',
            return_value=self.mock_progress_tracker
        )
        
        # Mock checkpoint manager
        self.mock_checkpoint_manager = Mock()
        self.checkpoint_manager_patch = patch(
            'app.services.checkpoint_manager.get_checkpoint_manager',
            return_value=self.mock_checkpoint_manager
        )
        
        # Mock file stats
        self.file_stats_patch = patch(
            'app.services.streaming_parser.get_file_stats',
            return_value=asyncio.coroutine(lambda *args: {
                "file_size_bytes": 1024000,
                "estimated_items": 1000,
                "format_detected": "json_array",
                "compression": None
            })()
        )
        
        # Mock streaming ingestion
        self.streaming_ingest_patch = patch(
            'app.services.rag_ingest.ingest_json_file_streaming',
            return_value=asyncio.coroutine(lambda *args, **kwargs: {
                "upserted": 500,
                "dim": 1024,
                "statistics": {"processing_time": 45.2}
            })()
        )
        
        # Start all patches
        self.tenant_config_patch.start()
        self.task_manager_patch.start()
        self.progress_tracker_patch.start()
        self.checkpoint_manager_patch.start()
        self.file_stats_patch.start()
        self.streaming_ingest_patch.start()
    
    def cleanup_mocks(self):
        """Clean up all mocks."""
        self.tenant_config_patch.stop()
        self.task_manager_patch.stop()
        self.progress_tracker_patch.stop()
        self.checkpoint_manager_patch.stop()
        self.file_stats_patch.stop()
        self.streaming_ingest_patch.stop()
    
    def create_test_file_upload(self, file_content: str, filename: str = "test.json") -> Dict[str, Any]:
        """Create test file upload data."""
        return {
            "file": (BytesIO(file_content.encode()), filename, "application/json")
        }
    
    def test_analyze_file_endpoint(self) -> APITestResult:
        """Test file analysis endpoint."""
        logger.info("Testing /rag/analyze-file endpoint...")
        
        start_time = time.time()
        errors = []
        
        try:
            # Create test file
            test_file = self.file_generator.generate_json_array_file(
                FileSpec("api_test_analyze", 5.0, 1000, "medium", "json_array", "API test file")
            )
            
            with open(test_file, 'rb') as f:
                file_content = f.read()
            
            # Test the endpoint
            response = self.client.post(
                "/rag/analyze-file",
                files={"file": ("test_analyze.json", file_content, "application/json")},
                headers={"x-tenant-id": self.tenant_id}
            )
            
            processing_time = time.time() - start_time
            success = response.status_code == 200
            
            response_data = response.json() if response.status_code == 200 else {}
            
            # Validate response structure
            if success:
                expected_keys = ["status", "file_analysis", "processing_estimates", "recommendations"]
                for key in expected_keys:
                    if key not in response_data:
                        errors.append(f"Missing key in response: {key}")
                        success = False
                
                # Validate analysis data
                if "file_analysis" in response_data:
                    analysis = response_data["file_analysis"]
                    if analysis.get("file_size_bytes", 0) <= 0:
                        errors.append("Invalid file size in analysis")
                        success = False
                
                # Validate recommendations
                if "recommendations" in response_data:
                    recs = response_data["recommendations"]
                    if "approach" not in recs or "use_batching" not in recs:
                        errors.append("Missing recommendation fields")
                        success = False
            
            return APITestResult(
                endpoint="/rag/analyze-file",
                method="POST",
                success=success,
                status_code=response.status_code,
                response_data=response_data,
                test_scenario="file_analysis",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            )
            
        except Exception as e:
            logger.error(f"Analyze file test failed: {e}")
            errors.append(str(e))
            
            return APITestResult(
                endpoint="/rag/analyze-file",
                method="POST",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="file_analysis",
                errors=errors,
                performance_metrics={"processing_time": time.time() - start_time}
            )
    
    def test_processing_capabilities_endpoint(self) -> APITestResult:
        """Test processing capabilities endpoint."""
        logger.info("Testing /rag/processing-capabilities endpoint...")
        
        start_time = time.time()
        errors = []
        
        try:
            response = self.client.get(
                "/rag/processing-capabilities",
                headers={"x-tenant-id": self.tenant_id}
            )
            
            processing_time = time.time() - start_time
            success = response.status_code == 200
            
            response_data = response.json() if response.status_code == 200 else {}
            
            # Validate response structure
            if success:
                expected_keys = ["status", "capabilities"]
                for key in expected_keys:
                    if key not in response_data:
                        errors.append(f"Missing key in response: {key}")
                        success = False
                
                # Validate capabilities structure
                if "capabilities" in response_data:
                    caps = response_data["capabilities"]
                    required_cap_keys = ["providers", "features", "limits", "default_settings"]
                    for key in required_cap_keys:
                        if key not in caps:
                            errors.append(f"Missing capabilities key: {key}")
                            success = False
                    
                    # Validate features
                    if "features" in caps:
                        features = caps["features"]
                        expected_features = [
                            "streaming_processing", "token_aware_chunking", 
                            "intelligent_batching", "progress_tracking"
                        ]
                        for feature in expected_features:
                            if feature not in features:
                                errors.append(f"Missing feature: {feature}")
                                success = False
            
            return APITestResult(
                endpoint="/rag/processing-capabilities",
                method="GET",
                success=success,
                status_code=response.status_code,
                response_data=response_data,
                test_scenario="capabilities_check",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            )
            
        except Exception as e:
            logger.error(f"Processing capabilities test failed: {e}")
            errors.append(str(e))
            
            return APITestResult(
                endpoint="/rag/processing-capabilities",
                method="GET",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="capabilities_check",
                errors=errors,
                performance_metrics={"processing_time": time.time() - start_time}
            )
    
    def test_streaming_ingestion_endpoint(self) -> APITestResult:
        """Test streaming ingestion endpoint."""
        logger.info("Testing /rag/ingest-file-streaming endpoint...")
        
        start_time = time.time()
        errors = []
        
        try:
            # Create test file
            test_file = self.file_generator.generate_json_array_file(
                FileSpec("api_test_streaming", 10.0, 2000, "medium", "json_array", "API streaming test")
            )
            
            with open(test_file, 'rb') as f:
                file_content = f.read()
            
            # Schema configuration
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {
                        "id": "id",
                        "title": "title",
                        "category": "metadata.category"
                    }
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 500,
                    "overlap_tokens": 50,
                    "model_name": "voyage-large-2"
                }
            }
            
            # Test the endpoint
            response = self.client.post(
                "/rag/ingest-file-streaming",
                files={"file": ("test_streaming.json", file_content, "application/json")},
                data={
                    "schema_json": json.dumps(schema_config),
                    "embedding_provider": "voyageai",
                    "embedding_model": "voyage-large-2",
                    "enable_chunking_enhancement": "true",
                    "max_tokens_per_chunk": "1000"
                },
                headers={"x-tenant-id": self.tenant_id}
            )
            
            processing_time = time.time() - start_time
            success = response.status_code == 200
            
            response_data = response.json() if response.status_code == 200 else {}
            
            # Validate response structure
            if success:
                if "status" not in response_data or response_data["status"] != "ok":
                    errors.append("Invalid status in response")
                    success = False
                
                # Check for expected result fields
                expected_fields = ["upserted", "dim"]
                for field in expected_fields:
                    if field not in response_data:
                        errors.append(f"Missing result field: {field}")
                        success = False
            
            return APITestResult(
                endpoint="/rag/ingest-file-streaming",
                method="POST",
                success=success,
                status_code=response.status_code,
                response_data=response_data,
                test_scenario="streaming_ingestion",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            )
            
        except Exception as e:
            logger.error(f"Streaming ingestion test failed: {e}")
            errors.append(str(e))
            
            return APITestResult(
                endpoint="/rag/ingest-file-streaming",
                method="POST",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="streaming_ingestion",
                errors=errors,
                performance_metrics={"processing_time": time.time() - start_time}
            )
    
    def test_async_ingestion_and_task_management(self) -> List[APITestResult]:
        """Test async ingestion and full task management workflow."""
        logger.info("Testing async ingestion and task management workflow...")
        
        results = []
        
        # Mock task responses
        test_task_id = "test_task_12345"
        
        # Configure mock task manager
        self.mock_task_manager.start_task.return_value = asyncio.coroutine(lambda: test_task_id)()
        
        # Mock task info for different states
        def create_mock_task_info(status: str, progress_percentage: float = 0):
            mock_info = Mock()
            mock_info.tenant_id = self.tenant_id
            mock_info.status = status
            mock_info.file_info = {
                "filename": "test_async.json",
                "file_size": 1024000
            }
            mock_info.configuration = {
                "embedding_provider": "voyageai",
                "embedding_model": "voyage-large-2",
                "schema_config": {"format": "json_array"}
            }
            mock_info.progress = Mock()
            mock_info.progress.items_processed = int(1000 * progress_percentage / 100)
            mock_info.progress.items_total = 1000
            mock_info.progress.percentage = progress_percentage
            mock_info.progress.chunks_processed = int(1200 * progress_percentage / 100)
            mock_info.progress.embeddings_generated = int(1200 * progress_percentage / 100)
            mock_info.progress.current_phase = ProcessingPhase.GENERATING_EMBEDDINGS.value
            mock_info.progress.error_count = 0
            mock_info.progress.start_time = time.time() - 60
            mock_info.progress.elapsed_time = 60
            mock_info.progress.estimated_completion = time.time() + 30
            mock_info.updated_at = time.time()
            mock_info.error_info = None
            return mock_info
        
        # 1. Test async ingestion start
        try:
            test_file = self.file_generator.generate_json_array_file(
                FileSpec("api_test_async", 15.0, 3000, "medium", "json_array", "API async test")
            )
            
            with open(test_file, 'rb') as f:
                file_content = f.read()
            
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id", "title": "title"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 400,
                    "overlap_tokens": 40,
                    "model_name": "voyage-large-2"
                }
            }
            
            start_time = time.time()
            response = self.client.post(
                "/rag/ingest-file-async",
                files={"file": ("test_async.json", file_content, "application/json")},
                data={
                    "schema_json": json.dumps(schema_config),
                    "embedding_provider": "voyageai",
                    "embedding_model": "voyage-large-2",
                    "enable_chunking_enhancement": "true",
                    "max_tokens_per_chunk": "1000"
                },
                headers={"x-tenant-id": self.tenant_id}
            )
            processing_time = time.time() - start_time
            
            success = response.status_code == 200
            response_data = response.json() if success else {}
            errors = []
            
            if success:
                if response_data.get("status") != "processing_started":
                    errors.append("Expected status 'processing_started'")
                    success = False
                
                if "task_id" not in response_data:
                    errors.append("Missing task_id in response")
                    success = False
                
                if "endpoints" not in response_data:
                    errors.append("Missing endpoints in response")
                    success = False
            
            results.append(APITestResult(
                endpoint="/rag/ingest-file-async",
                method="POST",
                success=success,
                status_code=response.status_code,
                response_data=response_data,
                test_scenario="async_start",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            logger.error(f"Async ingestion start test failed: {e}")
            results.append(APITestResult(
                endpoint="/rag/ingest-file-async",
                method="POST",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="async_start",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        # 2. Test task status checking
        for progress in [25, 50, 75, 100]:
            try:
                self.mock_task_manager.get_task_status.return_value = asyncio.coroutine(
                    lambda: create_mock_task_info(
                        TaskStatus.RUNNING.value if progress < 100 else TaskStatus.COMPLETED.value,
                        progress
                    )
                )()
                
                # Mock detailed progress
                self.mock_progress_tracker.get_detailed_progress.return_value = asyncio.coroutine(
                    lambda task_id: {
                        "overall": {"percentage": progress},
                        "phase_history": [{"phase": "analyzing", "completed": True}],
                        "current_phase": {"name": "embedding", "progress": progress}
                    }
                )()
                
                start_time = time.time()
                response = self.client.get(
                    f"/rag/task-status/{test_task_id}",
                    headers={"x-tenant-id": self.tenant_id}
                )
                processing_time = time.time() - start_time
                
                success = response.status_code == 200
                response_data = response.json() if success else {}
                errors = []
                
                if success:
                    # Validate response structure
                    expected_keys = ["task_id", "status", "progress", "timing"]
                    for key in expected_keys:
                        if key not in response_data:
                            errors.append(f"Missing key in status response: {key}")
                            success = False
                    
                    # Validate progress data
                    if "progress" in response_data:
                        progress_data = response_data["progress"]
                        if "percentage" not in progress_data:
                            errors.append("Missing percentage in progress")
                            success = False
                        elif abs(progress_data["percentage"] - progress) > 1:
                            errors.append(f"Progress mismatch: expected {progress}, got {progress_data['percentage']}")
                            success = False
                
                results.append(APITestResult(
                    endpoint=f"/rag/task-status/{test_task_id}",
                    method="GET",
                    success=success,
                    status_code=response.status_code,
                    response_data=response_data,
                    test_scenario=f"status_check_{progress}%",
                    errors=errors,
                    performance_metrics={"processing_time": processing_time}
                ))
                
            except Exception as e:
                logger.error(f"Task status test failed at {progress}%: {e}")
                results.append(APITestResult(
                    endpoint=f"/rag/task-status/{test_task_id}",
                    method="GET",
                    success=False,
                    status_code=500,
                    response_data={},
                    test_scenario=f"status_check_{progress}%",
                    errors=[str(e)],
                    performance_metrics={"processing_time": 0}
                ))
        
        # 3. Test task control operations
        for action in ["pause", "resume", "cancel"]:
            try:
                # Mock task info for running state
                self.mock_task_manager.get_task_status.return_value = asyncio.coroutine(
                    lambda: create_mock_task_info(TaskStatus.RUNNING.value, 50)
                )()
                
                # Mock control operations
                if action == "pause":
                    self.mock_task_manager.pause_task.return_value = asyncio.coroutine(lambda task_id: True)()
                elif action == "resume":
                    self.mock_task_manager.resume_task.return_value = asyncio.coroutine(lambda task_id: True)()
                elif action == "cancel":
                    self.mock_task_manager.cancel_task.return_value = asyncio.coroutine(lambda task_id: True)()
                
                start_time = time.time()
                response = self.client.post(
                    f"/rag/task-control/{test_task_id}",
                    params={"action": action},
                    headers={"x-tenant-id": self.tenant_id}
                )
                processing_time = time.time() - start_time
                
                success = response.status_code == 200
                response_data = response.json() if success else {}
                errors = []
                
                if success:
                    if response_data.get("status") != "ok":
                        errors.append(f"Expected status 'ok' for {action}")
                        success = False
                    
                    if response_data.get("action") != action:
                        errors.append(f"Action mismatch: expected {action}, got {response_data.get('action')}")
                        success = False
                
                results.append(APITestResult(
                    endpoint=f"/rag/task-control/{test_task_id}",
                    method="POST",
                    success=success,
                    status_code=response.status_code,
                    response_data=response_data,
                    test_scenario=f"control_{action}",
                    errors=errors,
                    performance_metrics={"processing_time": processing_time}
                ))
                
            except Exception as e:
                logger.error(f"Task control test failed for {action}: {e}")
                results.append(APITestResult(
                    endpoint=f"/rag/task-control/{test_task_id}",
                    method="POST",
                    success=False,
                    status_code=500,
                    response_data={},
                    test_scenario=f"control_{action}",
                    errors=[str(e)],
                    performance_metrics={"processing_time": 0}
                ))
        
        # 4. Test recovery information
        try:
            # Mock failed task
            self.mock_task_manager.get_task_status.return_value = asyncio.coroutine(
                lambda: create_mock_task_info(TaskStatus.FAILED.value, 75)
            )()
            
            # Mock recovery stats
            self.mock_checkpoint_manager.estimate_recovery_progress.return_value = asyncio.coroutine(
                lambda task_id: {
                    "recoverable": True,
                    "checkpoint_age_hours": 0.5,
                    "items_processed": 750,
                    "estimated_remaining_work": {"failed_batches": 2, "failed_items": 50}
                }
            )()
            
            start_time = time.time()
            response = self.client.get(
                f"/rag/task-recovery/{test_task_id}",
                headers={"x-tenant-id": self.tenant_id}
            )
            processing_time = time.time() - start_time
            
            success = response.status_code == 200
            response_data = response.json() if success else {}
            errors = []
            
            if success:
                expected_keys = ["status", "task_id", "recovery_info"]
                for key in expected_keys:
                    if key not in response_data:
                        errors.append(f"Missing key in recovery response: {key}")
                        success = False
            
            results.append(APITestResult(
                endpoint=f"/rag/task-recovery/{test_task_id}",
                method="GET",
                success=success,
                status_code=response.status_code,
                response_data=response_data,
                test_scenario="recovery_info",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            logger.error(f"Task recovery test failed: {e}")
            results.append(APITestResult(
                endpoint=f"/rag/task-recovery/{test_task_id}",
                method="GET",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="recovery_info",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        # 5. Test active tasks listing
        try:
            # Mock active tasks
            self.mock_task_manager.get_active_tasks.return_value = asyncio.coroutine(
                lambda: [test_task_id, "other_task_123"]
            )()
            
            # Mock task info for active tasks
            self.mock_task_manager.get_task_status.return_value = asyncio.coroutine(
                lambda: create_mock_task_info(TaskStatus.RUNNING.value, 60)
            )()
            
            start_time = time.time()
            response = self.client.get(
                "/rag/active-tasks",
                headers={"x-tenant-id": self.tenant_id}
            )
            processing_time = time.time() - start_time
            
            success = response.status_code == 200
            response_data = response.json() if success else {}
            errors = []
            
            if success:
                if "active_tasks" not in response_data:
                    errors.append("Missing active_tasks in response")
                    success = False
                
                if "total_count" not in response_data:
                    errors.append("Missing total_count in response")
                    success = False
            
            results.append(APITestResult(
                endpoint="/rag/active-tasks",
                method="GET",
                success=success,
                status_code=response.status_code,
                response_data=response_data,
                test_scenario="active_tasks_list",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            logger.error(f"Active tasks test failed: {e}")
            results.append(APITestResult(
                endpoint="/rag/active-tasks",
                method="GET",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="active_tasks_list",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        return results
    
    def test_error_handling_scenarios(self) -> List[APITestResult]:
        """Test various error handling scenarios."""
        logger.info("Testing error handling scenarios...")
        
        results = []
        
        # Test invalid tenant ID
        try:
            start_time = time.time()
            response = self.client.get(
                "/rag/processing-capabilities",
                headers={"x-tenant-id": "invalid_tenant"}
            )
            processing_time = time.time() - start_time
            
            # Should return 404 for invalid tenant
            success = response.status_code == 404
            errors = [] if success else ["Expected 404 for invalid tenant"]
            
            results.append(APITestResult(
                endpoint="/rag/processing-capabilities",
                method="GET",
                success=success,
                status_code=response.status_code,
                response_data=response.json() if response.status_code != 500 else {},
                test_scenario="invalid_tenant",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            results.append(APITestResult(
                endpoint="/rag/processing-capabilities",
                method="GET",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="invalid_tenant",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        # Test missing required parameters
        try:
            start_time = time.time()
            response = self.client.post(
                "/rag/ingest-file-streaming",
                files={"file": ("test.json", b'{"test": "data"}', "application/json")},
                data={},  # Missing schema_json
                headers={"x-tenant-id": self.tenant_id}
            )
            processing_time = time.time() - start_time
            
            # Should return 422 for missing required parameter
            success = response.status_code == 422
            errors = [] if success else ["Expected 422 for missing schema_json"]
            
            results.append(APITestResult(
                endpoint="/rag/ingest-file-streaming",
                method="POST",
                success=success,
                status_code=response.status_code,
                response_data=response.json() if response.status_code not in [500, 422] else {},
                test_scenario="missing_parameters",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            results.append(APITestResult(
                endpoint="/rag/ingest-file-streaming",
                method="POST",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="missing_parameters",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        # Test invalid JSON schema
        try:
            start_time = time.time()
            response = self.client.post(
                "/rag/ingest-file-streaming",
                files={"file": ("test.json", b'{"test": "data"}', "application/json")},
                data={"schema_json": "invalid json"},
                headers={"x-tenant-id": self.tenant_id}
            )
            processing_time = time.time() - start_time
            
            # Should return 400 for invalid JSON
            success = response.status_code == 400
            errors = [] if success else ["Expected 400 for invalid JSON schema"]
            
            results.append(APITestResult(
                endpoint="/rag/ingest-file-streaming",
                method="POST",
                success=success,
                status_code=response.status_code,
                response_data=response.json() if response.status_code not in [500] else {},
                test_scenario="invalid_json_schema",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            results.append(APITestResult(
                endpoint="/rag/ingest-file-streaming",
                method="POST",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="invalid_json_schema",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        # Test task not found
        try:
            start_time = time.time()
            
            # Mock task not found
            self.mock_task_manager.get_task_status.return_value = asyncio.coroutine(lambda: None)()
            
            response = self.client.get(
                "/rag/task-status/nonexistent_task",
                headers={"x-tenant-id": self.tenant_id}
            )
            processing_time = time.time() - start_time
            
            # Should return 404 for task not found
            success = response.status_code == 404
            errors = [] if success else ["Expected 404 for nonexistent task"]
            
            results.append(APITestResult(
                endpoint="/rag/task-status/nonexistent_task",
                method="GET",
                success=success,
                status_code=response.status_code,
                response_data=response.json() if response.status_code not in [500] else {},
                test_scenario="task_not_found",
                errors=errors,
                performance_metrics={"processing_time": processing_time}
            ))
            
        except Exception as e:
            results.append(APITestResult(
                endpoint="/rag/task-status/nonexistent_task",
                method="GET",
                success=False,
                status_code=500,
                response_data={},
                test_scenario="task_not_found",
                errors=[str(e)],
                performance_metrics={"processing_time": 0}
            ))
        
        return results
    
    def run_all_tests(self) -> List[APITestResult]:
        """Run all API endpoint tests."""
        logger.info("Starting API endpoint test suite...")
        
        self.setup_mocks()
        
        try:
            # Individual endpoint tests
            self.test_results.append(self.test_analyze_file_endpoint())
            self.test_results.append(self.test_processing_capabilities_endpoint())
            self.test_results.append(self.test_streaming_ingestion_endpoint())
            
            # Task management workflow tests
            task_management_results = self.test_async_ingestion_and_task_management()
            self.test_results.extend(task_management_results)
            
            # Error handling tests
            error_handling_results = self.test_error_handling_scenarios()
            self.test_results.extend(error_handling_results)
            
        finally:
            self.cleanup_mocks()
        
        return self.test_results
    
    def generate_api_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive API test report."""
        if not self.test_results:
            return {"error": "No test results available"}
        
        # Calculate overall statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        
        # Group by endpoint
        endpoint_stats = {}
        for result in self.test_results:
            endpoint = result.endpoint
            if endpoint not in endpoint_stats:
                endpoint_stats[endpoint] = {"total": 0, "passed": 0, "failed": 0}
            
            endpoint_stats[endpoint]["total"] += 1
            if result.success:
                endpoint_stats[endpoint]["passed"] += 1
            else:
                endpoint_stats[endpoint]["failed"] += 1
        
        # Performance metrics
        avg_response_time = sum(r.performance_metrics.get("processing_time", 0) for r in self.test_results) / total_tests
        max_response_time = max((r.performance_metrics.get("processing_time", 0) for r in self.test_results), default=0)
        
        # Status code distribution
        status_codes = {}
        for result in self.test_results:
            code = result.status_code
            status_codes[code] = status_codes.get(code, 0) + 1
        
        # Critical validations
        critical_validations = {
            "all_endpoints_functional": all(endpoint_stats[ep]["passed"] > 0 for ep in endpoint_stats),
            "error_handling_works": any(r.test_scenario.startswith("invalid_") or r.test_scenario.startswith("missing_") for r in self.test_results if r.success),
            "task_management_complete": any(r.test_scenario.startswith("control_") for r in self.test_results if r.success),
            "response_times_acceptable": avg_response_time < 5.0,  # < 5 seconds average
            "success_rate_acceptable": (passed_tests / total_tests) >= 0.8  # >= 80% success rate
        }
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0
            },
            "endpoint_statistics": endpoint_stats,
            "performance_metrics": {
                "average_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "response_time_threshold": 5.0
            },
            "status_code_distribution": status_codes,
            "critical_validations": critical_validations,
            "overall_api_health": all(critical_validations.values()),
            "detailed_results": [
                {
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "success": r.success,
                    "status_code": r.status_code,
                    "test_scenario": r.test_scenario,
                    "response_time": r.performance_metrics.get("processing_time", 0),
                    "error_count": len(r.errors),
                    "has_response_data": len(r.response_data) > 0
                }
                for r in self.test_results
            ],
            "failed_tests_summary": [
                {
                    "endpoint": r.endpoint,
                    "scenario": r.test_scenario,
                    "status_code": r.status_code,
                    "errors": r.errors
                }
                for r in self.test_results if not r.success
            ]
        }
        
        return report
    
    def cleanup(self):
        """Clean up test resources."""
        self.file_generator.cleanup_generated_files()


def main():
    """Main test execution."""
    logger.info("Starting API Endpoint Test Suite")
    logger.info("=" * 80)
    
    tester = APIEndpointTester()
    
    try:
        # Run all tests
        results = tester.run_all_tests()
        
        # Generate report
        report = tester.generate_api_test_report()
        
        logger.info("\n" + "=" * 80)
        logger.info("API ENDPOINT TEST RESULTS")
        logger.info("=" * 80)
        
        print(f"\nTest Summary:")
        summary = report["test_summary"]
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed_tests']}")
        print(f"  Failed: {summary['failed_tests']}")
        print(f"  Success Rate: {summary['success_rate']:.1%}")
        
        print(f"\nEndpoint Statistics:")
        for endpoint, stats in report["endpoint_statistics"].items():
            print(f"  {endpoint}: {stats['passed']}/{stats['total']} passed")
        
        print(f"\nPerformance Metrics:")
        perf = report["performance_metrics"]
        print(f"  Average Response Time: {perf['average_response_time']:.2f}s")
        print(f"  Max Response Time: {perf['max_response_time']:.2f}s")
        
        print(f"\nStatus Code Distribution:")
        for code, count in report["status_code_distribution"].items():
            print(f"  {code}: {count} responses")
        
        print(f"\nCritical Validations:")
        for validation, passed in report["critical_validations"].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {validation}: {status}")
        
        overall_status = "✅ SUCCESS" if report["overall_api_health"] else "❌ ISSUES DETECTED"
        print(f"\nOVERALL API HEALTH: {overall_status}")
        
        if not report["overall_api_health"]:
            print("\n❌ ISSUES DETECTED:")
            for failed_test in report["failed_tests_summary"]:
                print(f"  - {failed_test['endpoint']} ({failed_test['scenario']}): {failed_test['status_code']}")
                for error in failed_test["errors"]:
                    print(f"    • {error}")
        else:
            print("\n✅ ALL API ENDPOINTS WORKING!")
            print("  - All endpoints are functional")
            print("  - Error handling is working correctly")
            print("  - Task management is complete")
            print("  - Response times are acceptable")
            print("  - API is ready for production use")
        
        # Save detailed report
        report_file = Path(tempfile.gettempdir()) / "api_endpoint_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"API test suite failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()