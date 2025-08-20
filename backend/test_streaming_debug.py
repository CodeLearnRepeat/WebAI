#!/usr/bin/env python3
"""Debug streaming parser issue"""

import json
import asyncio
import sys
from pathlib import Path

# Add the app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.streaming_parser import StreamingFileHandler, StreamingJSONProcessor

async def test_streaming():
    """Test the streaming parser directly"""
    
    # Read the file and schema
    file_path = "anotherone.json"
    schema_path = "schema_config.json"
    
    print(f"Testing file: {file_path}")
    
    # Load schema
    with open(schema_path, 'r') as f:
        schema = json.load(f)
    
    print(f"Schema loaded: {json.dumps(schema, indent=2)}")
    
    # Open file stream
    try:
        file_stream = await StreamingFileHandler.open_file_stream(file_path)
        print(f"File stream opened successfully")
        
        # Check file content
        content = file_stream.read()
        file_stream.seek(0)  # Reset to beginning
        print(f"File content preview: {content[:200]}")
        
        # Create processor
        processor = StreamingJSONProcessor(file_stream, schema)
        print(f"Processor created with format: {processor.format}")
        print(f"Content path: {processor.content_path}")
        print(f"Metadata paths: {processor.metadata_paths}")
        
        # Process items
        item_count = 0
        async for item in processor.process_stream():
            item_count += 1
            print(f"Item {item_count}: text='{item.text[:50]}...', metadata={item.metadata}")
        
        print(f"Total items processed: {item_count}")
        
        # Get stats
        stats = processor.get_stats()
        print(f"Processing stats: {stats}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'file_stream' in locals():
            file_stream.close()

if __name__ == "__main__":
    asyncio.run(test_streaming())