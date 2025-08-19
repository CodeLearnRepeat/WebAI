"""
Streaming JSON parser for memory-efficient processing of large JSON files.
Supports JSON arrays, NDJSON, and gzip compression.
"""

import ijson
import gzip
import json
import re
import logging
from typing import AsyncIterator, Dict, Any, IO, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
# import aiofiles  # Optional dependency - will be imported when needed

logger = logging.getLogger(__name__)


@dataclass
class ProcessedItem:
    """Container for processed JSON item with extracted content and metadata."""
    text: str
    metadata: Dict[str, Any]
    source_index: int
    chunk_index: int = 0


@dataclass
class StreamingStats:
    """Statistics for streaming processing."""
    items_processed: int = 0
    bytes_processed: int = 0
    errors_encountered: int = 0
    current_phase: str = "initializing"


class StreamingJSONProcessor:
    """Memory-efficient streaming JSON processing with content extraction."""
    
    def __init__(self, file_stream: IO, schema_config: Dict[str, Any]):
        """
        Initialize streaming processor.
        
        Args:
            file_stream: File-like object to read from
            schema_config: Configuration with format, mapping, and chunking settings
        """
        self.file_stream = file_stream
        self.schema_config = schema_config
        self.format = schema_config.get("format", "json_array").lower()
        self.mapping = schema_config.get("mapping", {})
        self.chunking = schema_config.get("chunking", {"strategy": "none"})
        self.content_path = self.mapping.get("content_path", "")
        self.metadata_paths = self.mapping.get("metadata_paths", {})
        
        self.stats = StreamingStats()
        
        # Validate configuration
        if not self.content_path:
            raise ValueError("schema_config.mapping.content_path is required")
        
        if self.format not in ("json_array", "ndjson"):
            raise ValueError("format must be 'json_array' or 'ndjson'")
        
        logger.info(f"Initialized streaming parser for format: {self.format}")
    
    async def process_stream(self) -> AsyncIterator[ProcessedItem]:
        """
        Stream process JSON without loading entire file.
        
        Yields:
            ProcessedItem: Extracted and chunked content with metadata
        """
        try:
            self.stats.current_phase = "parsing"
            
            if self.format == "json_array":
                async for item in self._stream_json_array():
                    yield item
            else:  # ndjson
                async for item in self._stream_ndjson():
                    yield item
                    
            self.stats.current_phase = "completed"
            
        except Exception as e:
            self.stats.current_phase = "error"
            logger.error(f"Error during streaming: {e}")
            raise
    
    async def _stream_json_array(self) -> AsyncIterator[ProcessedItem]:

        try:
            # Use ijson to parse array items one by one
            parser = ijson.parse(self.file_stream)
            items = {}  # Store items by their array index
            item_index = 0
            
            for prefix, event, value in parser:
                self.stats.bytes_processed += 1  # Approximate
                
                if event == 'start_array' and prefix == '':
                    # Root array started
                    continue
                elif event == 'end_array' and prefix == '':
                    # Root array ended
                    break
                elif event == 'start_map' and prefix.isdigit():
                    # New array item starting (prefix is "0", "1", "2", etc.)
                    array_index = int(prefix)
                    items[array_index] = {}
                elif event == 'end_map' and prefix.isdigit():
                    # Array item complete
                    array_index = int(prefix)
                    if array_index in items:
                        async for processed in self._process_item(items[array_index], array_index):
                            yield processed
                        del items[array_index]  # Free memory
                        self.stats.items_processed += 1
                elif prefix and '.' in prefix:
                    # Nested property within an array item (e.g., "0.raw_text", "1.source_url")
                    parts = prefix.split('.', 1)
                    if parts[0].isdigit():
                        array_index = int(parts[0])
                        if array_index not in items:
                            items[array_index] = {}
                        
                        # Set nested value
                        try:
                            self._set_nested_value_simple(items[array_index], parts[1], event, value)
                        except Exception as e:
                            logger.warning(f"Error setting nested value at {prefix}: {e}")
                            self.stats.errors_encountered += 1
                elif prefix.isdigit() and event in ('string', 'number', 'boolean', 'null'):
                    # Direct value in array item (shouldn't happen with objects, but handle it)
                    array_index = int(prefix)
                    if array_index not in items:
                        items[array_index] = value
                        
        except Exception as e:
            logger.error(f"Error parsing JSON array: {e}")
            self.stats.errors_encountered += 1
            raise

    def _set_nested_value_simple(self, obj: Dict, path: str, event: str, value: Any):
        """Set nested value in object using simplified path."""
        if not path:
            return
            
        # Split path and navigate to parent
        parts = path.split('.')
        current = obj
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set final value
        final_key = parts[-1]
        if event in ('string', 'number', 'boolean', 'null'):
            current[final_key] = value
        elif event == 'start_map':
            if final_key not in current:
                current[final_key] = {}
        elif event == 'start_array':
            if final_key not in current:
                current[final_key] = []

    
    async def _stream_ndjson(self) -> AsyncIterator[ProcessedItem]:

        """Stream parse NDJSON (newline-delimited JSON) format."""
        
        try:
            item_index = 0
            
            # Read line by line
            async for line in self._read_lines():
                line = line.strip()
                if not line:
                    continue
                
                try:
                    item = json.loads(line)
                    async for processed in self._process_item(item, item_index):
                        yield processed
                    item_index += 1
                    self.stats.items_processed += 1
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on line {item_index + 1}: {e}")
                    self.stats.errors_encountered += 1
                    continue
                except Exception as e:
                    logger.error(f"Error processing item {item_index}: {e}")
                    self.stats.errors_encountered += 1
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing NDJSON: {e}")
            self.stats.errors_encountered += 1
            raise
    
    async def _read_lines(self) -> AsyncIterator[str]:
        """Read lines from file stream."""
        buffer = ""
        chunk_size = 8192
        
        while True:
            chunk = self.file_stream.read(chunk_size)
            if not chunk:
                break
                
            if isinstance(chunk, bytes):
                chunk = chunk.decode('utf-8')
            
            buffer += chunk
            self.stats.bytes_processed += len(chunk)
            
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                yield line
        
        # Yield remaining buffer if any
        if buffer.strip():
            yield buffer
    
    def _set_nested_value(self, obj: Dict, prefix: str, event: str, value: Any):
        """Set nested value in object based on ijson path."""
        if not prefix:
            return
            
        # Parse ijson prefix (e.g., "item.data.content")
        parts = prefix.split('.')
        current = obj
        
        # Navigate to parent
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set final value
        final_key = parts[-1]
        if event in ('string', 'number', 'boolean', 'null'):
            current[final_key] = value
        elif event == 'start_map':
            if final_key not in current:
                current[final_key] = {}
        elif event == 'start_array':
            if final_key not in current:
                current[final_key] = []
    
    async def _process_item(self, item: Dict[str, Any], item_index: int) -> AsyncIterator[ProcessedItem]:
        """
        Process individual JSON item - extract content and metadata, then chunk.
        
        Args:
            item: JSON object
            item_index: Index of item in source
            
        Yields:
            ProcessedItem: Processed and chunked content
        """
        try:
            # Extract content using dot-path
            content = self._parse_dot_path(self.content_path, item)
            if not isinstance(content, str) or not content.strip():
                # Skip items without valid content
                return
            
            # Extract metadata
            metadata = {}
            for key, path in self.metadata_paths.items():
                metadata[key] = self._parse_dot_path(path, item)
            
            # Add source tracking
            metadata["_source_index"] = item_index
            
            # Chunk the content
            chunks = self._chunk_text(content)
            
            # Yield processed items for each chunk
            for chunk_index, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata["_chunk_index"] = chunk_index
                chunk_metadata["_total_chunks"] = len(chunks)
                
                yield ProcessedItem(
                    text=chunk,
                    metadata=chunk_metadata,
                    source_index=item_index,
                    chunk_index=chunk_index
                )
                
        except Exception as e:
            logger.error(f"Error processing item {item_index}: {e}")
            self.stats.errors_encountered += 1
    
    def _parse_dot_path(self, path: str, obj: Any) -> Any:
        """
        Parse dot-notation path to extract value from nested object.
        Supports array indexing like 'items[0].content'.
        """
        if not path or obj is None:
            return None
        
        current = obj
        # Enhanced regex to handle array indices
        token_re = re.compile(r"\.?([^[.\]]+)|\[(\d+)\]")
        
        try:
            for match in token_re.finditer(path):
                key, idx = match.groups()
                
                if key:
                    # Object key access
                    if not isinstance(current, dict) or key not in current:
                        return None
                    current = current[key]
                else:
                    # Array index access
                    index = int(idx)
                    if not isinstance(current, list) or index >= len(current):
                        return None
                    current = current[index]
                    
            return current
            
        except (KeyError, IndexError, TypeError, ValueError):
            return None
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text based on configuration strategy.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        strategy = self.chunking.get("strategy", "none").lower()
        
        if strategy == "none":
            return [text]
        elif strategy == "recursive":
            return self._recursive_chunk(text)
        elif strategy == "token_aware":
            return self._token_aware_chunk(text)
        else:
            logger.warning(f"Unknown chunking strategy: {strategy}, using 'none'")
            return [text]
    
    def _recursive_chunk(self, text: str) -> List[str]:
        """Simple recursive character-based chunking."""
        max_chars = int(self.chunking.get("max_chars", 1200))
        overlap = int(self.chunking.get("overlap", 150))
        
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
    
    def _token_aware_chunk(self, text: str) -> List[str]:
        """Token-aware chunking (placeholder - will be enhanced in batch_manager)."""
        # For now, use character-based as fallback
        # This will be properly implemented in the batch manager
        return self._recursive_chunk(text)
    
    def get_stats(self) -> StreamingStats:
        """Get current processing statistics."""
        return self.stats


class StreamingFileHandler:
    """Helper class for handling file streams with compression support."""
    
    @staticmethod
    async def open_file_stream(file_path: Union[str, Path]) -> IO:
        """
        Open file stream with automatic gzip detection.
        
        Args:
            file_path: Path to file
            
        Returns:
            File stream (handles gzip automatically)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if file is gzipped
        if file_path.suffix == '.gz':
            return gzip.open(file_path, 'rt', encoding='utf-8')
        
        # Check magic bytes for gzip
        with open(file_path, 'rb') as f:
            magic = f.read(2)
            
        if len(magic) >= 2 and magic[0] == 0x1F and magic[1] == 0x8B:
            # File is gzipped
            return gzip.open(file_path, 'rt', encoding='utf-8')
        else:
            # Regular text file
            return open(file_path, 'r', encoding='utf-8')
    
    @staticmethod
    def detect_format(file_stream: IO) -> str:
        """
        Auto-detect JSON format (json_array vs ndjson).
        
        Args:
            file_stream: File stream to analyze
            
        Returns:
            Detected format: 'json_array' or 'ndjson'
        """
        # Save current position
        current_pos = file_stream.tell()
        
        try:
            # Read first few lines
            sample_lines = []
            for _ in range(5):
                line = file_stream.readline()
                if not line:
                    break
                sample_lines.append(line.strip())
            
            # Reset file position
            file_stream.seek(current_pos)
            
            # Check if first line starts with '['
            if sample_lines and sample_lines[0].startswith('['):
                return 'json_array'
            
            # Check if lines look like individual JSON objects
            json_object_count = 0
            for line in sample_lines:
                if line and (line.startswith('{') or line.startswith('"')):
                    try:
                        json.loads(line)
                        json_object_count += 1
                    except:
                        pass
            
            if json_object_count >= 1:
                return 'ndjson'
            
            # Default to json_array
            return 'json_array'
            
        except Exception as e:
            logger.warning(f"Error detecting format: {e}, defaulting to json_array")
            file_stream.seek(current_pos)
            return 'json_array'


# Convenience functions
async def process_json_file(
    file_path: Union[str, Path],
    schema_config: Dict[str, Any]
) -> AsyncIterator[ProcessedItem]:
    """
    Convenience function to process a JSON file with streaming.
    
    Args:
        file_path: Path to JSON file
        schema_config: Processing configuration
        
    Yields:
        ProcessedItem: Processed content items
    """
    try:
        import aiofiles
    except ImportError:
        raise ImportError("aiofiles is required for async file processing. Install with: pip install aiofiles")
    
    file_stream = await StreamingFileHandler.open_file_stream(file_path)
    
    try:
        # Auto-detect format if not specified
        if "format" not in schema_config:
            detected_format = StreamingFileHandler.detect_format(file_stream)
            schema_config = schema_config.copy()
            schema_config["format"] = detected_format
            logger.info(f"Auto-detected format: {detected_format}")
        
        processor = StreamingJSONProcessor(file_stream, schema_config)
        
        async for item in processor.process_stream():
            yield item
            
    finally:
        file_stream.close()


async def get_file_stats(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get statistics about a JSON file without full processing.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Dictionary with file statistics
    """
    file_path = Path(file_path)
    file_size = file_path.stat().st_size
    
    file_stream = await StreamingFileHandler.open_file_stream(file_path)
    
    try:
        detected_format = StreamingFileHandler.detect_format(file_stream)
        
        # Quick estimate of item count for JSON arrays
        if detected_format == 'json_array':
            # Count commas and brackets for rough estimate
            content_sample = file_stream.read(10000)  # Read 10KB sample
            file_stream.seek(0)
            comma_count = content_sample.count(',')
            estimated_items = max(1, comma_count // 10)  # Rough estimate
        else:
            # For NDJSON, count lines
            line_count = 0
            for _ in file_stream:
                line_count += 1
                if line_count > 1000:  # Sample first 1000 lines
                    break
            estimated_items = line_count
        
        return {
            "file_size_bytes": file_size,
            "detected_format": detected_format,
            "estimated_items": estimated_items,
            "file_path": str(file_path)
        }
        
    finally:
        file_stream.close()