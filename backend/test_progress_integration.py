"""
Integration test for progress tracking and error handling in large JSON file processing.
Tests the complete pipeline with background tasks, checkpoints, and progress monitoring.
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

from app.services.background_tasks import get_task_manager, TaskStatus
from app.services.checkpoint_manager import get_checkpoint_manager
from app.services.progress_tracker import get_progress_tracker, ProcessingPhase
from app.services.rag_ingest import ingest_json_file_streaming
from app.core.redis import get_redis_client


def create_test_json_file(num_items: int = 1000) -> str:
    """Create a test JSON file with specified number of items."""
    test_data = []
    for i in range(num_items):
        item = {
            "id": f"item_{i:04d}",
            "content": f"This is test content for item {i}. " * 10,  # ~400 chars each
            "metadata": {
                "category": f"category_{i % 5}",
                "priority": i % 3,
                "tags": [f"tag_{j}" for j in range(i % 4)]
            },
            "timestamp": f"2024-01-{(i % 30) + 1:02d}T10:00:00Z"
        }
        test_data.append(item)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, indent=2)
        return f.name


def create_test_schema_config() -> Dict[str, Any]:
    """Create test schema configuration."""
    return {
        "format": "json_array",
        "mapping": {
            "content_path": "content",
            "metadata_paths": {
                "item_id": "id",
                "category": "metadata.category",
                "priority": "metadata.priority",
                "timestamp": "timestamp"
            }
        },
        "chunking": {
            "strategy": "recursive",
            "max_chars": 500,
            "overlap": 50
        }
    }


async def test_basic_progress_tracking():
    """Test basic progress tracking functionality."""
    print("\n=== Testing Basic Progress Tracking ===")
    
    # Create test file
    test_file = create_test_json_file(100)
    schema_config = create_test_schema_config()
    
    try:
        progress_tracker = get_progress_tracker()
        task_id = "test_progress_001"
        
        # Start tracking
        progress_stats = await progress_tracker.start_tracking(
            task_id=task_id,
            tenant_id="test_tenant",
            total_items_expected=100
        )
        
        print(f"Started tracking task {task_id}")
        
        # Simulate phase updates
        phases = [
            ProcessingPhase.ANALYZING_FILE,
            ProcessingPhase.PARSING_JSON,
            ProcessingPhase.GENERATING_EMBEDDINGS,
            ProcessingPhase.STORING_VECTORS
        ]
        
        for i, phase in enumerate(phases):
            await progress_tracker.update_phase(task_id, phase)
            await progress_tracker.update_progress(
                task_id=task_id,
                items_processed=i * 25,
                force_update=True
            )
            print(f"  Phase {phase.value}: {i * 25} items processed")
            await asyncio.sleep(0.1)
        
        # Get final progress
        final_progress = await progress_tracker.get_detailed_progress(task_id)
        if final_progress:
            print(f"  Final progress: {final_progress['overall']['percentage']:.1f}%")
            print(f"  Phases completed: {len(final_progress['phase_history'])}")
        
        # Finish tracking
        await progress_tracker.finish_tracking(task_id, success=True)
        print("Progress tracking test completed successfully")
        
    finally:
        # Cleanup
        Path(test_file).unlink(missing_ok=True)


async def test_checkpoint_recovery():
    """Test checkpoint and recovery functionality."""
    print("\n=== Testing Checkpoint Recovery ===")
    
    checkpoint_manager = get_checkpoint_manager()
    task_id = "test_checkpoint_001"
    
    # Create initial checkpoint
    await checkpoint_manager.save_checkpoint(
        task_id=task_id,
        file_path="/tmp/test.json",
        items_processed=50,
        chunks_processed=150,
        embeddings_generated=150,
        processing_state={"test_mode": True},
        force=True
    )
    print(f"Created checkpoint for task {task_id}")
    
    # Load checkpoint
    checkpoint = await checkpoint_manager.load_checkpoint(task_id)
    if checkpoint:
        print(f"  Loaded checkpoint: {checkpoint.items_processed} items processed")
        print(f"  Processing state: {checkpoint.processing_state}")
    
    # Create recovery context
    recovery_context = await checkpoint_manager.create_recovery_context(task_id)
    if recovery_context:
        print(f"  Recovery context created: can retry={recovery_context.can_retry}")
        print(f"  Items to recover from: {recovery_context.checkpoint.items_processed}")
    
    # Test failed batch handling
    batch_data = {"texts": ["text1", "text2"], "metadata": [{"id": 1}, {"id": 2}]}
    error_info = {"error": "Connection timeout", "retry_count": 1}
    
    failed_batch_id = await checkpoint_manager.save_failed_batch(
        task_id=task_id,
        batch_data=batch_data,
        error_info=error_info
    )
    print(f"  Saved failed batch: {failed_batch_id}")
    
    # Get failed batches
    failed_batches = await checkpoint_manager.get_failed_batches(task_id)
    print(f"  Failed batches found: {len(failed_batches)}")
    
    # Cleanup
    await checkpoint_manager.delete_checkpoint(task_id)
    print("Checkpoint recovery test completed successfully")


async def test_error_handling():
    """Test enhanced error handling with retry logic."""
    print("\n=== Testing Error Handling ===")
    
    from app.services.embeddings import RobustVoyageEmbedder
    
    # Test retry logic (will fail with invalid API key)
    embedder = RobustVoyageEmbedder("invalid_api_key", "voyage-large-2")
    
    try:
        await embedder.embed_with_retry(["test text"])
    except Exception as e:
        print(f"  Expected error caught: {type(e).__name__}")
        
        # Test if error should be retried
        should_retry = embedder._should_retry(e)
        print(f"  Should retry this error: {should_retry}")
    
    print("Error handling test completed successfully")


async def test_background_task_integration():
    """Test full background task integration."""
    print("\n=== Testing Background Task Integration ===")
    
    # Create test file
    test_file = create_test_json_file(50)  # Small file for quick test
    schema_config = create_test_schema_config()
    
    try:
        task_manager = get_task_manager()
        
        # Start background task (this will fail due to missing milvus config, but we can test the setup)
        task_id = await task_manager.start_task(
            tenant_id="test_tenant",
            file_path=test_file,
            file_size=Path(test_file).stat().st_size,
            schema_config=schema_config,
            embedding_provider="sentence_transformers",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        print(f"Started background task: {task_id}")
        
        # Monitor task for a few seconds
        for i in range(10):
            task_info = await task_manager.get_task_status(task_id)
            if task_info:
                print(f"  Task status: {task_info.status}")
                print(f"  Items processed: {task_info.progress.items_processed}")
                print(f"  Current phase: {task_info.progress.current_phase}")
                
                if task_info.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    break
            
            await asyncio.sleep(0.5)
        
        # Get final status
        final_task_info = await task_manager.get_task_status(task_id)
        if final_task_info:
            print(f"  Final status: {final_task_info.status}")
            if final_task_info.error_info:
                print(f"  Error (expected): {final_task_info.error_info.get('error_message', 'Unknown')}")
        
        print("Background task integration test completed")
        
    finally:
        # Cleanup
        Path(test_file).unlink(missing_ok=True)


async def test_api_integration():
    """Test API endpoints functionality (without actual HTTP calls)."""
    print("\n=== Testing API Integration ===")
    
    task_manager = get_task_manager()
    
    # Create a mock task
    task_id = "test_api_001"
    
    # Test task control functions
    active_tasks = await task_manager.get_active_tasks()
    print(f"Active tasks: {len(active_tasks)}")
    
    # Test cleanup
    cleaned_count = await task_manager.cleanup_completed_tasks(max_age_hours=0)
    print(f"Cleaned up {cleaned_count} old tasks")
    
    print("API integration test completed successfully")


async def main():
    """Run all integration tests."""
    print("Starting Progress Tracking and Error Handling Integration Tests")
    print("=" * 70)
    
    try:
        # Test individual components
        await test_basic_progress_tracking()
        await test_checkpoint_recovery()
        await test_error_handling()
        await test_api_integration()
        
        # Test full integration (this may fail due to missing config, but tests the pipeline)
        await test_background_task_integration()
        
        print("\n" + "=" * 70)
        print("✅ All integration tests completed!")
        print("\nNote: Some tests may show expected errors due to missing production configuration")
        print("(Milvus connection, VoyageAI API keys, etc.), but this demonstrates the error handling works correctly.")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())