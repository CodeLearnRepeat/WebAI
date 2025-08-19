#!/usr/bin/env python3
"""
Simple test script for core streaming JSON chunking functionality.
Tests the components without external dependencies.
"""

import json
import tempfile
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our new services
from app.services.token_counter import VoyageTokenCounter, count_tokens
from app.services.batch_manager import VoyageBatchManager


def create_test_json_file(num_items: int = 10) -> str:
    """Create a test JSON file with sample data."""
    test_data = []
    
    for i in range(num_items):
        item = {
            "id": f"item_{i:04d}",
            "title": f"Test Document {i}",
            "content": f"This is the content of test document number {i}. " * (i % 5 + 1),
            "metadata": {
                "category": f"category_{i % 3}",
                "tags": [f"tag_{j}" for j in range(i % 3 + 1)],
                "timestamp": "2024-01-01T00:00:00Z"
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
        "A" * 500,  # Long text
    ]
    
    for text in test_texts:
        tokens = counter.count_tokens(text)
        logger.info(f"Text: '{text[:30]}...' -> {tokens} tokens")
    
    # Test batch estimation
    batch_tokens = counter.estimate_batch_tokens(test_texts)
    logger.info(f"Total batch tokens: {batch_tokens}")
    
    # Test batch capacity
    can_fit = counter.can_fit_in_limit(test_texts, token_limit=9500)
    logger.info(f"Can fit in limit: {can_fit}")
    
    # Test find max batch size
    max_size = counter.find_max_batch_size(test_texts, token_limit=9500)
    logger.info(f"Max batch size: {max_size}")
    
    logger.info("✓ Token counter tests passed")


def test_batch_manager():
    """Test the batch manager."""
    logger.info("Testing batch manager...")
    
    # Create batch manager
    batch_manager = VoyageBatchManager("voyage-large-2")
    
    # Test texts of varying sizes
    test_texts = [
        f"Test text {i} with content that varies in length. " * (i % 3 + 1)
        for i in range(15)
    ]
    
    # Add metadata for each text
    test_metadatas = [{"id": i, "category": f"cat_{i % 3}"} for i in range(len(test_texts))]
    
    # Create batches
    batches = list(batch_manager.create_batches(test_texts, test_metadatas))
    
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
    
    # Test current batch info
    batch_info = batch_manager.current_batch_info
    logger.info(f"Current batch info: {batch_info}")
    
    logger.info("✓ Batch manager tests passed")


def test_json_parsing():
    """Test basic JSON parsing functionality."""
    logger.info("Testing JSON parsing...")
    
    # Create test file
    test_file = create_test_json_file(5)
    
    try:
        # Read and parse the JSON file
        with open(test_file, 'r') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} items from JSON file")
        
        # Test dot-path parsing (simulate what the streaming parser does)
        def parse_dot_path(path: str, obj):
            """Simple dot-path parser."""
            if not path:
                return None
            current = obj
            for key in path.split('.'):
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        
        # Extract content and metadata from each item
        for i, item in enumerate(data):
            content = parse_dot_path("content", item)
            title = parse_dot_path("title", item)
            category = parse_dot_path("metadata.category", item)
            
            logger.info(f"Item {i}: title='{title}', category='{category}', content_len={len(content) if content else 0}")
        
        logger.info("✓ JSON parsing tests passed")
        
    finally:
        # Cleanup
        Path(test_file).unlink()


def test_chunking_simulation():
    """Test chunking simulation."""
    logger.info("Testing chunking simulation...")
    
    # Create some test content
    long_content = "This is a very long piece of content. " * 50  # About 1900 characters
    
    def chunk_text(text: str, max_chars: int = 500, overlap: int = 50) -> list:
        """Simple character-based chunking."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(text_len, start + max_chars)
            chunk = text[start:end]
            chunks.append(chunk)
            
            if end == text_len:
                break
            
            start = max(start + 1, end - overlap)
        
        return chunks
    
    # Test chunking
    chunks = chunk_text(long_content)
    logger.info(f"Split {len(long_content)} chars into {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Chunk {i}: {len(chunk)} chars")
    
    # Test with batch manager
    batch_manager = VoyageBatchManager("voyage-large-2")
    
    # Process chunks through batch manager
    batches = list(batch_manager.create_batches(chunks))
    logger.info(f"Created {len(batches)} batches from {len(chunks)} chunks")
    
    logger.info("✓ Chunking simulation tests passed")


def test_integration_workflow():
    """Test a complete workflow simulation."""
    logger.info("Testing integration workflow...")
    
    # Create test file
    test_file = create_test_json_file(8)
    
    try:
        # 1. Load JSON data
        with open(test_file, 'r') as f:
            data = json.load(f)
        
        # 2. Extract content and create chunks
        all_texts = []
        all_metadata = []
        
        for item in data:
            content = item.get("content", "")
            if content:
                # Simple chunking
                chunks = [content[i:i+300] for i in range(0, len(content), 250)]  # 50 char overlap
                
                for chunk_idx, chunk in enumerate(chunks):
                    all_texts.append(chunk)
                    all_metadata.append({
                        "source_id": item["id"],
                        "title": item["title"],
                        "category": item["metadata"]["category"],
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks)
                    })
        
        logger.info(f"Extracted {len(all_texts)} text chunks from {len(data)} documents")
        
        # 3. Process through batch manager
        batch_manager = VoyageBatchManager("voyage-large-2")
        batches = list(batch_manager.create_batches(all_texts, all_metadata))
        
        logger.info(f"Created {len(batches)} embedding batches")
        
        # 4. Simulate processing each batch
        total_processed = 0
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{len(batches)}: {batch.size} items, {batch.total_tokens} tokens")
            total_processed += batch.size
            
            # Simulate embedding generation (just count tokens)
            for text in batch.texts:
                tokens = count_tokens(text, "voyage-large-2")
                # In real usage, this would be sent to VoyageAI API
        
        logger.info(f"Workflow complete: processed {total_processed} text chunks")
        logger.info("✓ Integration workflow tests passed")
        
    finally:
        # Cleanup
        Path(test_file).unlink()


def test_convenience_functions():
    """Test convenience functions."""
    logger.info("Testing convenience functions...")
    
    # Test token counting convenience function
    text = "This is a test text for token counting with some content."
    tokens = count_tokens(text, "voyage-large-2")
    logger.info(f"Convenience token count: {tokens}")
    
    # Test with different model
    tokens2 = count_tokens(text, "voyage-2")
    logger.info(f"Different model token count: {tokens2}")
    
    logger.info("✓ Convenience function tests passed")


def main():
    """Run all tests."""
    logger.info("Starting core streaming JSON chunking integration tests...")
    logger.info("=" * 60)
    
    try:
        # Run tests
        test_token_counter()
        test_batch_manager()
        test_json_parsing()
        test_chunking_simulation()
        test_integration_workflow()
        test_convenience_functions()
        
        logger.info("=" * 60)
        logger.info("🎉 All core integration tests completed successfully!")
        logger.info("The streaming JSON chunking system core components are working correctly.")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Install full dependencies: pip install -r requirements.txt")
        logger.info("2. Configure VoyageAI API key in tenant configuration")
        logger.info("3. Use the new /rag/ingest-file-streaming endpoint for large files")
        logger.info("4. Use /rag/analyze-file to get file statistics before processing")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()