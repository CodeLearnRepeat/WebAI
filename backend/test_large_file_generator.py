#!/usr/bin/env python3
"""
Large file test generator for VoyageAI batching system validation.
Creates various JSON test files that exceed VoyageAI's token and chunk limits.
"""

import json
import tempfile
import os
import random
import string
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FileSpec:
    """Specification for generating test files."""
    name: str
    size_mb: float
    num_items: int
    content_complexity: str  # "simple", "medium", "complex"
    format_type: str  # "json_array", "ndjson"
    description: str


class LargeFileGenerator:
    """Generates large JSON test files for validation testing."""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize file generator.
        
        Args:
            output_dir: Directory to store generated files (uses temp if None)
        """
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "large_json_tests"
        self.output_dir.mkdir(exist_ok=True)
        self.generated_files: List[str] = []
        
        logger.info(f"Initialized LargeFileGenerator with output_dir: {self.output_dir}")
    
    def generate_content(self, complexity: str, base_length: int = 100) -> str:
        """
        Generate content with specified complexity level.
        
        Args:
            complexity: "simple", "medium", or "complex"
            base_length: Base content length
            
        Returns:
            Generated content string
        """
        if complexity == "simple":
            # Simple repetitive content
            return f"This is simple test content. " * (base_length // 30)
        
        elif complexity == "medium":
            # Medium complexity with varied sentences
            sentences = [
                "The quick brown fox jumps over the lazy dog.",
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "Machine learning algorithms process vast amounts of data.",
                "Natural language processing enables computer understanding.",
                "Vector embeddings capture semantic relationships effectively."
            ]
            content = []
            for i in range(base_length // 50):
                content.append(random.choice(sentences))
            return " ".join(content)
        
        else:  # complex
            # Complex content with special characters, code, and varied structure
            complex_elements = [
                "JSON processing: {'key': 'value', 'nested': {'array': [1, 2, 3]}}",
                "Code snippet: def process_data(x): return [i**2 for i in x if i > 0]",
                "Mathematical formula: Σ(xi * yi) / √(Σ(xi²) * Σ(yi²))",
                "Unicode content: 你好世界 🌍 Здравствуй мир עולם שלום",
                "Technical jargon: API endpoint authentication via OAuth 2.0 bearer tokens",
                "Long identifier: very_long_variable_name_that_might_affect_tokenization_patterns"
            ]
            content = []
            for i in range(base_length // 100):
                content.append(random.choice(complex_elements))
                # Add some random text
                random_text = ''.join(random.choices(string.ascii_letters + ' ', k=random.randint(20, 100)))
                content.append(random_text)
            return " ".join(content)
    
    def create_json_item(self, item_id: int, content_complexity: str, target_tokens: int = 200) -> Dict[str, Any]:
        """
        Create a single JSON item with specified characteristics.
        
        Args:
            item_id: Unique item identifier
            content_complexity: Content complexity level
            target_tokens: Target token count for content
            
        Returns:
            JSON item dictionary
        """
        # Estimate character to token ratio (roughly 4:1 for English)
        target_chars = target_tokens * 4
        
        content = self.generate_content(content_complexity, target_chars)
        
        item = {
            "id": f"item_{item_id:06d}",
            "title": f"Test Document {item_id} - {content_complexity.title()} Content",
            "content": content,
            "metadata": {
                "item_index": item_id,
                "content_complexity": content_complexity,
                "estimated_tokens": target_tokens,
                "category": f"category_{item_id % 10}",
                "subcategory": f"subcat_{item_id % 5}",
                "tags": [f"tag_{i}" for i in range(item_id % 7)],
                "priority": item_id % 3,
                "timestamp": f"2024-{(item_id % 12) + 1:02d}-{(item_id % 28) + 1:02d}T10:00:00Z",
                "author": f"author_{item_id % 20}",
                "version": "1.0",
                "processing_hints": {
                    "chunk_strategy": "adaptive" if item_id % 3 == 0 else "fixed",
                    "priority_level": "high" if item_id % 10 == 0 else "normal"
                }
            },
            "relationships": {
                "parent_id": f"parent_{item_id // 10}" if item_id > 0 else None,
                "child_ids": [f"child_{item_id}_{i}" for i in range(item_id % 3)],
                "related_items": [f"related_{(item_id + i) % 1000}" for i in range(1, (item_id % 5) + 1)]
            }
        }
        
        return item
    
    def generate_json_array_file(self, spec: FileSpec) -> str:
        """
        Generate JSON array format file.
        
        Args:
            spec: File specification
            
        Returns:
            Path to generated file
        """
        filename = f"{spec.name}_array.json"
        filepath = self.output_dir / filename
        
        logger.info(f"Generating JSON array file: {filename} ({spec.num_items} items)")
        
        items = []
        for i in range(spec.num_items):
            # Vary token counts to create realistic distribution
            base_tokens = 150
            if spec.content_complexity == "simple":
                target_tokens = base_tokens + random.randint(0, 50)
            elif spec.content_complexity == "medium":
                target_tokens = base_tokens + random.randint(50, 200)
            else:  # complex
                target_tokens = base_tokens + random.randint(100, 500)
            
            item = self.create_json_item(i, spec.content_complexity, target_tokens)
            items.append(item)
        
        # Write JSON array
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(f"Generated {filename}: {file_size_mb:.2f}MB, {spec.num_items} items")
        
        self.generated_files.append(str(filepath))
        return str(filepath)
    
    def generate_ndjson_file(self, spec: FileSpec) -> str:
        """
        Generate NDJSON format file.
        
        Args:
            spec: File specification
            
        Returns:
            Path to generated file
        """
        filename = f"{spec.name}_ndjson.json"
        filepath = self.output_dir / filename
        
        logger.info(f"Generating NDJSON file: {filename} ({spec.num_items} items)")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for i in range(spec.num_items):
                # Vary token counts
                base_tokens = 150
                if spec.content_complexity == "simple":
                    target_tokens = base_tokens + random.randint(0, 50)
                elif spec.content_complexity == "medium":
                    target_tokens = base_tokens + random.randint(50, 200)
                else:  # complex
                    target_tokens = base_tokens + random.randint(100, 500)
                
                item = self.create_json_item(i, spec.content_complexity, target_tokens)
                json.dump(item, f, ensure_ascii=False)
                f.write('\n')
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(f"Generated {filename}: {file_size_mb:.2f}MB, {spec.num_items} items")
        
        self.generated_files.append(str(filepath))
        return str(filepath)
    
    def generate_extreme_batch_limit_file(self) -> str:
        """
        Generate file specifically designed to test VoyageAI batch limits.
        Creates content that would require 15+ batches if not properly managed.
        
        Returns:
            Path to generated file
        """
        filename = "extreme_batch_limits.json"
        filepath = self.output_dir / filename
        
        logger.info("Generating extreme batch limit test file...")
        
        # Create items that would exceed limits if not properly batched
        # Target: ~15,000 chunks with ~150,000 total tokens
        items = []
        
        for i in range(15000):  # This exceeds the 1000 chunk limit by 15x
            # Each item will be chunked further, creating multiple chunks per item
            content_parts = []
            for j in range(5):  # 5 parts per item = 75,000 potential chunks
                part_content = self.generate_content("complex", 300)  # ~75 tokens each
                content_parts.append(part_content)
            
            item = {
                "id": f"extreme_item_{i:06d}",
                "title": f"Extreme Test Item {i}",
                "content": " ".join(content_parts),  # ~375 tokens total
                "metadata": {
                    "test_type": "extreme_batch_limit",
                    "item_index": i,
                    "expected_chunks": 5,
                    "category": f"extreme_cat_{i % 100}"
                }
            }
            items.append(item)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        logger.info(f"Generated {filename}: {file_size_mb:.2f}MB with extreme batching requirements")
        
        self.generated_files.append(str(filepath))
        return str(filepath)
    
    def generate_test_suite(self) -> Dict[str, List[str]]:
        """
        Generate complete test suite with various file specifications.
        
        Returns:
            Dictionary mapping test categories to file paths
        """
        logger.info("Generating comprehensive test suite...")
        
        # Define test file specifications
        test_specs = [
            # Small files for basic validation
            FileSpec("small_simple", 1.0, 500, "simple", "json_array", 
                    "Small file with simple content for basic testing"),
            FileSpec("small_complex", 1.0, 300, "complex", "json_array",
                    "Small file with complex content for tokenization testing"),
            
            # Medium files that exceed single batch limits
            FileSpec("medium_batch_test", 5.0, 2000, "medium", "json_array",
                    "Medium file requiring multiple batches"),
            FileSpec("medium_ndjson", 5.0, 2000, "medium", "ndjson",
                    "Medium NDJSON file for format testing"),
            
            # Large files that significantly exceed limits
            FileSpec("large_token_heavy", 25.0, 5000, "complex", "json_array",
                    "Large file with token-heavy content"),
            FileSpec("large_chunk_heavy", 50.0, 20000, "simple", "json_array",
                    "Large file with many chunks"),
            
            # Extra large files for stress testing
            FileSpec("xlarge_mixed", 100.0, 15000, "medium", "json_array",
                    "Extra large file with mixed content complexity"),
        ]
        
        generated_files = {
            "small_files": [],
            "medium_files": [],
            "large_files": [],
            "extreme_files": [],
            "format_tests": []
        }
        
        # Generate files according to specifications
        for spec in test_specs:
            if spec.format_type == "json_array":
                filepath = self.generate_json_array_file(spec)
            else:
                filepath = self.generate_ndjson_file(spec)
            
            # Categorize files
            if spec.size_mb <= 2:
                generated_files["small_files"].append(filepath)
            elif spec.size_mb <= 10:
                generated_files["medium_files"].append(filepath)
            else:
                generated_files["large_files"].append(filepath)
            
            if spec.format_type == "ndjson":
                generated_files["format_tests"].append(filepath)
        
        # Generate extreme test file
        extreme_file = self.generate_extreme_batch_limit_file()
        generated_files["extreme_files"].append(extreme_file)
        
        # Generate files with various token distributions
        high_token_file = self.generate_high_token_file()
        many_small_chunks_file = self.generate_many_small_chunks_file()
        
        generated_files["extreme_files"].extend([high_token_file, many_small_chunks_file])
        
        self._generate_test_summary(generated_files)
        
        return generated_files
    
    def generate_high_token_file(self) -> str:
        """Generate file with items that have very high token counts."""
        filename = "high_token_content.json"
        filepath = self.output_dir / filename
        
        logger.info("Generating high token content file...")
        
        items = []
        for i in range(1000):
            # Create content with very high token density
            content = self.generate_content("complex", 2000)  # ~500 tokens per item
            
            item = {
                "id": f"high_token_{i:04d}",
                "title": f"High Token Document {i}",
                "content": content,
                "metadata": {
                    "test_type": "high_token_density",
                    "estimated_tokens": 500
                }
            }
            items.append(item)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        
        self.generated_files.append(str(filepath))
        return str(filepath)
    
    def generate_many_small_chunks_file(self) -> str:
        """Generate file with many small chunks to test chunk limits."""
        filename = "many_small_chunks.json"
        filepath = self.output_dir / filename
        
        logger.info("Generating many small chunks file...")
        
        items = []
        for i in range(5000):  # Many items
            # Small content that will create individual chunks
            content = self.generate_content("simple", 50)  # ~12 tokens each
            
            item = {
                "id": f"small_chunk_{i:05d}",
                "content": content,
                "metadata": {
                    "test_type": "many_small_chunks",
                    "chunk_size": "small"
                }
            }
            items.append(item)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
        
        self.generated_files.append(str(filepath))
        return str(filepath)
    
    def _generate_test_summary(self, generated_files: Dict[str, List[str]]):
        """Generate summary of test files."""
        summary_file = self.output_dir / "test_files_summary.json"
        
        summary = {
            "generation_timestamp": "2024-01-01T00:00:00Z",
            "total_files": len(self.generated_files),
            "categories": {},
            "files": []
        }
        
        for category, files in generated_files.items():
            summary["categories"][category] = len(files)
            
            for filepath in files:
                file_path = Path(filepath)
                file_size = file_path.stat().st_size
                
                file_info = {
                    "name": file_path.name,
                    "path": str(filepath),
                    "category": category,
                    "size_bytes": file_size,
                    "size_mb": file_size / (1024 * 1024)
                }
                summary["files"].append(file_info)
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Generated test summary: {summary_file}")
    
    def cleanup_generated_files(self):
        """Clean up all generated test files."""
        logger.info("Cleaning up generated test files...")
        
        for filepath in self.generated_files:
            try:
                Path(filepath).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete {filepath}: {e}")
        
        # Also remove summary
        summary_file = self.output_dir / "test_files_summary.json"
        summary_file.unlink(missing_ok=True)
        
        self.generated_files.clear()
        logger.info("Cleanup completed")


def create_test_file_specifications() -> List[FileSpec]:
    """Create predefined test file specifications for consistent testing."""
    return [
        # Files designed to test specific VoyageAI limits
        FileSpec("voyage_token_limit_test", 10.0, 1500, "complex", "json_array",
                "File designed to test VoyageAI 10,000 token limit per batch"),
        
        FileSpec("voyage_chunk_limit_test", 15.0, 5000, "simple", "json_array", 
                "File designed to test VoyageAI 1,000 chunk limit per batch"),
        
        FileSpec("voyage_combined_limits", 20.0, 3000, "medium", "json_array",
                "File designed to test both token and chunk limits simultaneously"),
        
        # Real-world scenario files
        FileSpec("documentation_corpus", 30.0, 2000, "medium", "json_array",
                "Simulates large documentation corpus ingestion"),
        
        FileSpec("customer_support_tickets", 25.0, 10000, "simple", "ndjson",
                "Simulates customer support ticket processing"),
        
        FileSpec("research_papers", 40.0, 1000, "complex", "json_array",
                "Simulates academic research paper processing"),
    ]


def main():
    """Main function for testing the generator."""
    logging.basicConfig(level=logging.INFO)
    
    generator = LargeFileGenerator()
    
    try:
        # Generate test suite
        generated_files = generator.generate_test_suite()
        
        print("\n=== Generated Test Files ===")
        for category, files in generated_files.items():
            print(f"\n{category.upper()}:")
            for filepath in files:
                file_size = Path(filepath).stat().st_size / (1024 * 1024)
                print(f"  - {Path(filepath).name}: {file_size:.2f}MB")
        
        print(f"\nTotal files generated: {len(generator.generated_files)}")
        print(f"Output directory: {generator.output_dir}")
        
        # Optionally cleanup (comment out to keep files for testing)
        # generator.cleanup_generated_files()
        
    except Exception as e:
        logger.error(f"Error generating test files: {e}")
        raise


if __name__ == "__main__":
    main()