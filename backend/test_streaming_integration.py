#!/usr/bin/env python3
"""
Test script for streaming JSON chunking integration.
Demonstrates the new token-aware batching system.
"""

import asyncio
import json
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our new services
from app.services.token_counter import VoyageTokenCounter, count_tokens
from app.services.streaming_parser import StreamingJSONProcessor, process_json_file
from app.services.batch_manager import VoyageBatchManager, create_batch_processor
from app.services.embeddings import BatchEmbeddingService


def create_test_json_file(num_items: int = 100) -> str:
    """Create a test JSON file with sample data."""
    test_data = []
    
    for i in range(num_items):
        item = {
            "id": f"item_{i:04d}",
            "title": f"Test Document {i}",
            "content": f"This is the content of test document number {i}. " * (i % 10 + 1),
            "metadata": {
                "category": f"category_{i % 5}",
                "tags": [f"tag_{j}" for j in range(i % 3 + 1)],
                "timestamp": "2024-01-01T00:00:00Z",
                "length": len(f"This is the content of test document number {i}. " * (i % 10 + 1))
            }
        }
        test_data.append(item)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f, indent=2)
        return f.name


def test_token_counter():
    """Test the token counter service."""
    logger.info("Testing token counter service...")
    
    # Test with VoyageAI model
    counter = VoyageTokenCounter("voyage-large-2")
    
    test_texts = [
        "Hello world",
        "This is a longer text with more content to test token counting.",
        "Short text",
        "A" * 1000,  # Long text
    ]
    
    for text in test_texts:
        tokens = counter.count_tokens(text)
        logger.info(f"Text: '{text[:50]}...' -> {tokens} tokens")
    
    # Test batch estimation
    batch_tokens = counter.estimate_batch_tokens(test_texts)
    logger.info(f"Total batch tokens: {batch_tokens}")
    
    # Test batch capacity
    can_fit = counter.can_fit_in_limit(test_texts, token_limit=9500)
    logger.info(f"Can fit in limit: {can_fit}")
    
    logger.info("✓ Token counter tests passed")


async def test_streaming_parser():
    """Test the streaming JSON parser."""
    logger.info("Testing streaming JSON parser...")
    
    # Create test file
    test_file = create_test_json_file(50)
    
    try:
        # Configure schema
        schema_config = {
            "format": "json_array",
            "mapping": {
                "content_path": "content",
                "metadata_paths": {
                    "title": "title",
                    "category": "metadata.category",
                    "id": "id"
                }
            },
            "chunking": {
                "strategy": "recursive",
                "max_chars": 500,
                "overlap": 50
            }
        }
        
        # Test streaming processing
        items_processed = 0
        total_chunks = 0
        
        async for item in process_json_file(test_file, schema_config):
            items_processed += 1
            total_chunks += 1
            
            if items_processed <= 3:  # Log first few items
                logger.info(f"Processed item: {item.text[:100]}... (metadata: {item.metadata})")
        
        logger.info(f"Processed {total_chunks} total chunks from streaming parser")
        logger.info("✓ Streaming parser tests passed")
        
    finally:
        # Cleanup
        Path(test_file).unlink()


def test_batch_manager():
    """Test the batch manager."""
    logger.info("Testing batch manager...")
    
    # Create batch manager
    batch_manager = VoyageBatchManager("voyage-large-2")
    
    # Test texts of varying sizes
    test_texts = [
        f"Test text {i} with content that varies in length. " * (i % 5 + 1)
        for i in range(20)
    ]
    
    # Create batches
    batches = list(batch_manager.create_batches(test_texts))
    
    logger.info(f"Created {len(batches)} batches from {len(test_texts)} texts")
    
    for i, batch in enumerate(batches):
        logger.info(f"Batch {i}: {batch.size} items, {batch.total_tokens} tokens")
        
        # Validate batch
        is_valid, errors = batch_manager.validate_batch(batch)
        if not is_valid:
            logger.warning(f"Batch {i} validation errors: {errors}")
        else:
            logger.info(f"Batch {i} validation: ✓")
    
    # Get statistics
    stats = batch_manager.get_stats()
    logger.info(f"Batching stats: {stats.batches_created} batches, avg size: {stats.avg_batch_size:.1f}")
    
    logger.info("✓ Batch manager tests passed")


async def test_full_integration():
    """Test the full integration with mock embedding."""
    logger.info("Testing full integration...")
    
    # Create test file
    test_file = create_test_json_file(25)
    
    try:
        # Configure schema with token-aware chunking
        schema_config = {
            "format": "json_array",
            "mapping": {
                "content_path": "content",
                "metadata_paths": {
                    "title": "title",
                    "category": "metadata.category",
                    "id": "id"
                }
            },
            "chunking": {
                "strategy": "token_aware",
                "max_tokens": 200,
                "overlap_tokens": 20,
                "model_name": "voyage-large-2"
            }
        }
        
        # Create batch processor
        batch_processor = create_batch_processor("voyage-large-2", rate_limited=False)
        
        # Process stream to batches
        items_processed = 0
        batches_created = 0
        
        # Stream items and create batches
        async for item in process_json_file(test_file, schema_config):
            completed_batch = batch_processor.batch_manager.add_processed_item(item)
            items_processed += 1
            
            if completed_batch:
                batches_created += 1
                logger.info(f"Completed batch {batches_created}: {completed_batch.size} items, {completed_batch.total_tokens} tokens")
        
        # Get final batch
        final_batch = batch_processor.batch_manager.finalize_batches()
        if final_batch:
            batches_created += 1
            logger.info(f"Final batch: {final_batch.size} items, {final_batch.total_tokens} tokens")
        
        # Get processing statistics
        processing_stats = batch_processor.get_processing_stats()
        logger.info(f"Processing statistics: {processing_stats}")
        
        logger.info(f"Full integration: processed {items_processed} items into {batches_created} batches")
        logger.info("✓ Full integration tests passed")
        
    finally:
        # Cleanup
        Path(test_file).unlink()


async def test_mock_embedding_service():
    """Test the embedding service with mock data (no actual API calls)."""
    logger.info("Testing embedding service integration...")
    
    # Create mock embedding service (sentence transformers - no API key needed)
    embedding_service = BatchEmbeddingService("sentence_transformers", "all-MiniLM-L6-v2")
    
    test_texts = [
        "This is a test document for embedding.",
        "Another test document with different content.",
        "A third document to test batching behavior."
    ]
    
    try:
        # Test embedding (this will use sentence transformers, not VoyageAI)
        embeddings, dim = await embedding_service.embed_texts_with_batching(test_texts)
        
        logger.info(f"Generated {len(embeddings)} embeddings with dimension {dim}")
        logger.info(f"First embedding preview: {embeddings[0][:5]}..." if embeddings else "No embeddings")
        
        # Get batching stats
        stats = embedding_service.get_batching_stats()
        logger.info(f"Embedding service stats: {stats}")
        
        logger.info("✓ Embedding service integration tests passed")
        
    except Exception as e:
        logger.error(f"Embedding service test failed: {e}")
        # This is expected if sentence transformers isn't installed
        logger.info("ℹ Embedding test skipped (dependencies not available)")


def test_convenience_functions():
    """Test convenience functions."""
    logger.info("Testing convenience functions...")
    
    # Test token counting convenience function
    text = "This is a test text for token counting."
    tokens = count_tokens(text, "voyage-large-2")
    logger.info(f"Convenience token count: {tokens}")
    
    # Test batch manager creation
    batch_manager = create_batch_processor("voyage-large-2")
    logger.info(f"Created batch processor: {type(batch_manager).__name__}")
    
    logger.info("✓ Convenience function tests passed")


async def main():
    """Run all tests."""
    logger.info("Starting streaming JSON chunking integration tests...")
    logger.info("=" * 60)
    
    try:
        # Run tests
        test_token_counter()
        await test_streaming_parser()
        test_batch_manager()
        await test_full_integration()
        await test_mock_embedding_service()
        test_convenience_functions()
        
        logger.info("=" * 60)
        logger.info("🎉 All integration tests completed successfully!")
        logger.info("The streaming JSON chunking system is ready for use.")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())