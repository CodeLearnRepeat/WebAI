#!/usr/bin/env python3
"""
Performance and scale tests for large JSON file processing with VoyageAI batching.
Tests memory usage, processing speed, and scalability with various file sizes.
"""

import asyncio
import json
import tempfile
import time
import logging
import psutil
import gc
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# Import test generator and core services
from test_large_file_generator import LargeFileGenerator, FileSpec
from app.services.token_counter import VoyageTokenCounter
from app.services.streaming_parser import process_json_file
from app.services.batch_manager import VoyageBatchManager, create_batch_processor
from app.services.checkpoint_manager import get_checkpoint_manager
from app.services.progress_tracker import get_progress_tracker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    test_name: str
    file_size_mb: float
    items_processed: int
    batches_created: int
    processing_time: float
    memory_initial_mb: float
    memory_peak_mb: float
    memory_final_mb: float
    memory_growth_mb: float
    items_per_second: float
    batches_per_second: float
    memory_efficiency: float  # Items per MB memory growth
    cpu_usage_percent: float
    success: bool
    error_details: List[str]


class MemoryProfiler:
    """Detailed memory usage profiler."""
    
    def __init__(self, sample_interval: float = 0.5):
        """
        Initialize memory profiler.
        
        Args:
            sample_interval: Time between memory samples in seconds
        """
        self.sample_interval = sample_interval
        self.process = psutil.Process()
        self.samples = []
        self.sampling = False
        self.sample_thread = None
        
    def start_sampling(self):
        """Start continuous memory sampling."""
        self.sampling = True
        self.samples = []
        
        def sample_memory():
            while self.sampling:
                try:
                    memory_info = self.process.memory_info()
                    cpu_percent = self.process.cpu_percent()
                    
                    sample = {
                        "timestamp": time.time(),
                        "rss_mb": memory_info.rss / (1024 * 1024),
                        "vms_mb": memory_info.vms / (1024 * 1024),
                        "cpu_percent": cpu_percent
                    }
                    self.samples.append(sample)
                    
                    time.sleep(self.sample_interval)
                except Exception as e:
                    logger.warning(f"Memory sampling error: {e}")
                    break
        
        self.sample_thread = threading.Thread(target=sample_memory, daemon=True)
        self.sample_thread.start()
    
    def stop_sampling(self):
        """Stop memory sampling."""
        self.sampling = False
        if self.sample_thread:
            self.sample_thread.join(timeout=1.0)
    
    def get_stats(self) -> Dict[str, float]:
        """Get memory usage statistics."""
        if not self.samples:
            return {
                "initial_mb": 0,
                "peak_mb": 0,
                "final_mb": 0,
                "growth_mb": 0,
                "avg_mb": 0,
                "avg_cpu_percent": 0
            }
        
        rss_values = [s["rss_mb"] for s in self.samples]
        cpu_values = [s["cpu_percent"] for s in self.samples if s["cpu_percent"] is not None]
        
        return {
            "initial_mb": rss_values[0] if rss_values else 0,
            "peak_mb": max(rss_values) if rss_values else 0,
            "final_mb": rss_values[-1] if rss_values else 0,
            "growth_mb": max(rss_values) - rss_values[0] if len(rss_values) >= 2 else 0,
            "avg_mb": statistics.mean(rss_values) if rss_values else 0,
            "avg_cpu_percent": statistics.mean(cpu_values) if cpu_values else 0
        }


class PerformanceTester:
    """Core performance testing functionality."""
    
    def __init__(self):
        self.file_generator = LargeFileGenerator()
        self.results: List[PerformanceMetrics] = []
        
    async def test_small_file_baseline(self) -> PerformanceMetrics:
        """Test performance with small files to establish baseline."""
        logger.info("Testing small file performance baseline...")
        
        # Generate small test file
        test_file = self.file_generator.generate_json_array_file(
            FileSpec("small_perf", 1.0, 500, "medium", "json_array", "Small performance test")
        )
        
        return await self._measure_processing_performance(
            test_name="small_file_baseline",
            test_file=test_file,
            schema_config={
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id", "title": "title"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 200,
                    "overlap_tokens": 20,
                    "model_name": "voyage-large-2"
                }
            }
        )
    
    async def test_medium_file_scaling(self) -> PerformanceMetrics:
        """Test performance with medium-sized files."""
        logger.info("Testing medium file scaling performance...")
        
        test_file = self.file_generator.generate_json_array_file(
            FileSpec("medium_perf", 10.0, 2000, "medium", "json_array", "Medium performance test")
        )
        
        return await self._measure_processing_performance(
            test_name="medium_file_scaling",
            test_file=test_file,
            schema_config={
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id", "title": "title", "category": "metadata.category"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 300,
                    "overlap_tokens": 30,
                    "model_name": "voyage-large-2"
                }
            }
        )
    
    async def test_large_file_efficiency(self) -> PerformanceMetrics:
        """Test performance with large files."""
        logger.info("Testing large file efficiency...")
        
        test_file = self.file_generator.generate_json_array_file(
            FileSpec("large_perf", 50.0, 10000, "medium", "json_array", "Large performance test")
        )
        
        return await self._measure_processing_performance(
            test_name="large_file_efficiency",
            test_file=test_file,
            schema_config={
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id", "title": "title"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 250,
                    "overlap_tokens": 25,
                    "model_name": "voyage-large-2"
                }
            }
        )
    
    async def test_memory_bounded_processing(self) -> PerformanceMetrics:
        """Test that memory usage remains bounded regardless of file size."""
        logger.info("Testing memory-bounded processing...")
        
        # Create extra large file to stress test memory usage
        test_file = self.file_generator.generate_json_array_file(
            FileSpec("memory_test", 100.0, 20000, "simple", "json_array", "Memory test")
        )
        
        return await self._measure_processing_performance(
            test_name="memory_bounded_processing",
            test_file=test_file,
            schema_config={
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id"}
                },
                "chunking": {
                    "strategy": "recursive",
                    "max_chars": 500,
                    "overlap": 50
                }
            },
            memory_focus=True
        )
    
    async def test_token_complexity_impact(self) -> PerformanceMetrics:
        """Test performance impact of different content complexities."""
        logger.info("Testing token complexity impact...")
        
        # Generate file with complex content that has high token density
        test_file = self.file_generator.generate_json_array_file(
            FileSpec("complex_tokens", 20.0, 3000, "complex", "json_array", "Complex token test")
        )
        
        return await self._measure_processing_performance(
            test_name="token_complexity_impact",
            test_file=test_file,
            schema_config={
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id", "title": "title"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 150,  # Smaller to handle complex content
                    "overlap_tokens": 15,
                    "model_name": "voyage-large-2"
                }
            }
        )
    
    async def test_concurrent_processing(self) -> PerformanceMetrics:
        """Test performance with concurrent file processing."""
        logger.info("Testing concurrent processing performance...")
        
        start_time = time.time()
        profiler = MemoryProfiler()
        errors = []
        
        try:
            # Generate multiple small files for concurrent processing
            test_files = []
            for i in range(3):
                test_file = self.file_generator.generate_json_array_file(
                    FileSpec(f"concurrent_{i}", 5.0, 1000, "medium", "json_array", f"Concurrent test {i}")
                )
                test_files.append(test_file)
            
            profiler.start_sampling()
            
            # Process files concurrently
            schema_config = {
                "format": "json_array",
                "mapping": {
                    "content_path": "content",
                    "metadata_paths": {"id": "id"}
                },
                "chunking": {
                    "strategy": "token_aware",
                    "max_tokens": 200,
                    "overlap_tokens": 20,
                    "model_name": "voyage-large-2"
                }
            }
            
            async def process_file(file_path: str) -> Tuple[int, int]:
                """Process a single file and return item and batch counts."""
                batch_manager = VoyageBatchManager("voyage-large-2")
                items = 0
                batches = 0
                
                async for item in process_json_file(file_path, schema_config):
                    completed_batch = batch_manager.add_processed_item(item)
                    items += 1
                    
                    if completed_batch:
                        batches += 1
                
                # Get final batch
                final_batch = batch_manager.finalize_batches()
                if final_batch:
                    batches += 1
                
                return items, batches
            
            # Run concurrent processing
            tasks = [process_file(file_path) for file_path in test_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            total_items = 0
            total_batches = 0
            
            for result in results:
                if isinstance(result, Exception):
                    errors.append(str(result))
                else:
                    items, batches = result
                    total_items += items
                    total_batches += batches
            
            profiler.stop_sampling()
            processing_time = time.time() - start_time
            memory_stats = profiler.get_stats()
            
            # Calculate total file size
            total_size_mb = sum(Path(f).stat().st_size for f in test_files) / (1024 * 1024)
            
            success = len(errors) == 0
            
            return PerformanceMetrics(
                test_name="concurrent_processing",
                file_size_mb=total_size_mb,
                items_processed=total_items,
                batches_created=total_batches,
                processing_time=processing_time,
                memory_initial_mb=memory_stats["initial_mb"],
                memory_peak_mb=memory_stats["peak_mb"],
                memory_final_mb=memory_stats["final_mb"],
                memory_growth_mb=memory_stats["growth_mb"],
                items_per_second=total_items / processing_time if processing_time > 0 else 0,
                batches_per_second=total_batches / processing_time if processing_time > 0 else 0,
                memory_efficiency=total_items / max(memory_stats["growth_mb"], 1),
                cpu_usage_percent=memory_stats["avg_cpu_percent"],
                success=success,
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Concurrent processing test failed: {e}")
            profiler.stop_sampling()
            memory_stats = profiler.get_stats()
            
            return PerformanceMetrics(
                test_name="concurrent_processing",
                file_size_mb=0,
                items_processed=0,
                batches_created=0,
                processing_time=time.time() - start_time,
                memory_initial_mb=memory_stats["initial_mb"],
                memory_peak_mb=memory_stats["peak_mb"],
                memory_final_mb=memory_stats["final_mb"],
                memory_growth_mb=memory_stats["growth_mb"],
                items_per_second=0,
                batches_per_second=0,
                memory_efficiency=0,
                cpu_usage_percent=memory_stats["avg_cpu_percent"],
                success=False,
                error_details=[str(e)]
            )
    
    async def _measure_processing_performance(
        self, 
        test_name: str, 
        test_file: str, 
        schema_config: Dict[str, Any],
        memory_focus: bool = False
    ) -> PerformanceMetrics:
        """Core performance measurement function."""
        start_time = time.time()
        profiler = MemoryProfiler(sample_interval=0.2 if memory_focus else 0.5)
        errors = []
        
        try:
            file_size_mb = Path(test_file).stat().st_size / (1024 * 1024)
            
            # Force garbage collection before starting
            gc.collect()
            
            profiler.start_sampling()
            
            # Process file with batch manager
            batch_manager = VoyageBatchManager("voyage-large-2")
            items_processed = 0
            batches_created = 0
            
            async for item in process_json_file(test_file, schema_config):
                completed_batch = batch_manager.add_processed_item(item)
                items_processed += 1
                
                if completed_batch:
                    batches_created += 1
                
                # Force more frequent GC for memory-focused tests
                if memory_focus and items_processed % 100 == 0:
                    gc.collect()
            
            # Get final batch
            final_batch = batch_manager.finalize_batches()
            if final_batch:
                batches_created += 1
            
            profiler.stop_sampling()
            processing_time = time.time() - start_time
            memory_stats = profiler.get_stats()
            
            # Calculate performance metrics
            items_per_second = items_processed / processing_time if processing_time > 0 else 0
            batches_per_second = batches_created / processing_time if processing_time > 0 else 0
            memory_efficiency = items_processed / max(memory_stats["growth_mb"], 1)
            
            success = len(errors) == 0 and items_processed > 0
            
            logger.info(
                f"Performance test {test_name}: {items_processed} items, {batches_created} batches, "
                f"{processing_time:.2f}s, {memory_stats['growth_mb']:.1f}MB growth"
            )
            
            return PerformanceMetrics(
                test_name=test_name,
                file_size_mb=file_size_mb,
                items_processed=items_processed,
                batches_created=batches_created,
                processing_time=processing_time,
                memory_initial_mb=memory_stats["initial_mb"],
                memory_peak_mb=memory_stats["peak_mb"],
                memory_final_mb=memory_stats["final_mb"],
                memory_growth_mb=memory_stats["growth_mb"],
                items_per_second=items_per_second,
                batches_per_second=batches_per_second,
                memory_efficiency=memory_efficiency,
                cpu_usage_percent=memory_stats["avg_cpu_percent"],
                success=success,
                error_details=errors
            )
            
        except Exception as e:
            logger.error(f"Performance test {test_name} failed: {e}")
            profiler.stop_sampling()
            memory_stats = profiler.get_stats()
            errors.append(str(e))
            
            return PerformanceMetrics(
                test_name=test_name,
                file_size_mb=Path(test_file).stat().st_size / (1024 * 1024) if Path(test_file).exists() else 0,
                items_processed=0,
                batches_created=0,
                processing_time=time.time() - start_time,
                memory_initial_mb=memory_stats["initial_mb"],
                memory_peak_mb=memory_stats["peak_mb"],
                memory_final_mb=memory_stats["final_mb"],
                memory_growth_mb=memory_stats["growth_mb"],
                items_per_second=0,
                batches_per_second=0,
                memory_efficiency=0,
                cpu_usage_percent=memory_stats["avg_cpu_percent"],
                success=False,
                error_details=errors
            )


class ScalabilityTester:
    """Tests system scalability with increasing loads."""
    
    def __init__(self):
        self.file_generator = LargeFileGenerator()
        
    async def test_scaling_characteristics(self) -> List[PerformanceMetrics]:
        """Test how performance scales with increasing file sizes."""
        logger.info("Testing scaling characteristics...")
        
        # Define scaling test points
        test_points = [
            (1, 500, "small"),      # 1MB, 500 items
            (5, 1000, "medium_small"),   # 5MB, 1000 items
            (10, 2000, "medium"),   # 10MB, 2000 items
            (25, 5000, "large"),    # 25MB, 5000 items
            (50, 10000, "xlarge"),  # 50MB, 10000 items
        ]
        
        results = []
        
        for size_mb, items, size_name in test_points:
            logger.info(f"Testing scaling point: {size_name} ({size_mb}MB, {items} items)")
            
            # Generate test file
            test_file = self.file_generator.generate_json_array_file(
                FileSpec(f"scale_{size_name}", size_mb, items, "medium", "json_array", f"Scale test {size_name}")
            )
            
            # Measure performance
            tester = PerformanceTester()
            result = await tester._measure_processing_performance(
                test_name=f"scaling_{size_name}",
                test_file=test_file,
                schema_config={
                    "format": "json_array",
                    "mapping": {
                        "content_path": "content",
                        "metadata_paths": {"id": "id"}
                    },
                    "chunking": {
                        "strategy": "token_aware",
                        "max_tokens": 200,
                        "overlap_tokens": 20,
                        "model_name": "voyage-large-2"
                    }
                }
            )
            
            results.append(result)
            
            # Log scaling metrics
            if len(results) > 1:
                prev_result = results[-2]
                size_ratio = result.file_size_mb / prev_result.file_size_mb
                time_ratio = result.processing_time / prev_result.processing_time
                memory_ratio = result.memory_growth_mb / max(prev_result.memory_growth_mb, 1)
                
                logger.info(
                    f"Scaling ratios vs previous: Size={size_ratio:.1f}x, "
                    f"Time={time_ratio:.1f}x, Memory={memory_ratio:.1f}x"
                )
        
        return results
    
    async def test_batch_efficiency_scaling(self) -> Dict[str, Any]:
        """Test how batch efficiency scales with different content types."""
        logger.info("Testing batch efficiency scaling...")
        
        complexity_tests = [
            ("simple", "Simple repetitive content"),
            ("medium", "Medium complexity with varied sentences"),
            ("complex", "Complex content with JSON, code, unicode")
        ]
        
        results = {}
        
        for complexity, description in complexity_tests:
            logger.info(f"Testing batch efficiency with {complexity} content...")
            
            # Generate test file with specific complexity
            test_file = self.file_generator.generate_json_array_file(
                FileSpec(f"batch_eff_{complexity}", 15.0, 3000, complexity, "json_array", f"Batch efficiency {complexity}")
            )
            
            # Test with different chunking strategies
            strategies = [
                ("recursive", {"strategy": "recursive", "max_chars": 500, "overlap": 50}),
                ("token_aware", {"strategy": "token_aware", "max_tokens": 200, "overlap_tokens": 20, "model_name": "voyage-large-2"})
            ]
            
            complexity_results = {}
            
            for strategy_name, chunking_config in strategies:
                schema_config = {
                    "format": "json_array",
                    "mapping": {
                        "content_path": "content",
                        "metadata_paths": {"id": "id"}
                    },
                    "chunking": chunking_config
                }
                
                tester = PerformanceTester()
                result = await tester._measure_processing_performance(
                    test_name=f"batch_eff_{complexity}_{strategy_name}",
                    test_file=test_file,
                    schema_config=schema_config
                )
                
                complexity_results[strategy_name] = {
                    "items_per_second": result.items_per_second,
                    "batches_created": result.batches_created,
                    "memory_efficiency": result.memory_efficiency,
                    "processing_time": result.processing_time
                }
            
            results[complexity] = complexity_results
        
        return results


class PerformanceValidationSuite:
    """Complete performance and scale validation suite."""
    
    def __init__(self):
        self.performance_tester = PerformanceTester()
        self.scalability_tester = ScalabilityTester()
        self.results: List[PerformanceMetrics] = []
        
    async def run_performance_tests(self):
        """Run core performance tests."""
        logger.info("Running performance tests...")
        
        test_methods = [
            self.performance_tester.test_small_file_baseline,
            self.performance_tester.test_medium_file_scaling,
            self.performance_tester.test_large_file_efficiency,
            self.performance_tester.test_memory_bounded_processing,
            self.performance_tester.test_token_complexity_impact,
            self.performance_tester.test_concurrent_processing
        ]
        
        for test_method in test_methods:
            try:
                result = await test_method()
                self.results.append(result)
                
                status = "✅ PASS" if result.success else "❌ FAIL"
                logger.info(
                    f"{status} {result.test_name}: "
                    f"{result.items_per_second:.1f} items/sec, "
                    f"{result.memory_growth_mb:.1f}MB growth"
                )
                
            except Exception as e:
                logger.error(f"Performance test {test_method.__name__} failed: {e}")
    
    async def run_scalability_tests(self):
        """Run scalability tests."""
        logger.info("Running scalability tests...")
        
        # Test scaling characteristics
        scaling_results = await self.scalability_tester.test_scaling_characteristics()
        self.results.extend(scaling_results)
        
        # Test batch efficiency scaling
        batch_efficiency = await self.scalability_tester.test_batch_efficiency_scaling()
        
        logger.info("Batch efficiency scaling results:")
        for complexity, strategies in batch_efficiency.items():
            logger.info(f"  {complexity.capitalize()} content:")
            for strategy, metrics in strategies.items():
                logger.info(f"    {strategy}: {metrics['items_per_second']:.1f} items/sec, {metrics['batches_created']} batches")
    
    async def run_all_tests(self):
        """Run complete performance and scale test suite."""
        logger.info("Starting Performance and Scale Test Suite")
        logger.info("=" * 70)
        
        await self.run_performance_tests()
        await self.run_scalability_tests()
    
    def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends and characteristics."""
        if not self.results:
            return {"error": "No results to analyze"}
        
        # Group results by test type
        scaling_results = [r for r in self.results if r.test_name.startswith("scaling_")]
        other_results = [r for r in self.results if not r.test_name.startswith("scaling_")]
        
        analysis = {
            "performance_summary": {
                "tests_run": len(self.results),
                "successful_tests": sum(1 for r in self.results if r.success),
                "avg_items_per_second": statistics.mean([r.items_per_second for r in self.results if r.success]),
                "avg_memory_growth": statistics.mean([r.memory_growth_mb for r in self.results if r.success])
            }
        }
        
        # Scaling analysis
        if scaling_results:
            scaling_results.sort(key=lambda x: x.file_size_mb)
            
            # Calculate scaling factors
            size_growth = []
            time_growth = []
            memory_growth = []
            
            for i in range(1, len(scaling_results)):
                prev, curr = scaling_results[i-1], scaling_results[i]
                
                size_factor = curr.file_size_mb / prev.file_size_mb
                time_factor = curr.processing_time / prev.processing_time
                memory_factor = curr.memory_growth_mb / max(prev.memory_growth_mb, 0.1)
                
                size_growth.append(size_factor)
                time_growth.append(time_factor)
                memory_growth.append(memory_factor)
            
            analysis["scaling_analysis"] = {
                "avg_size_growth_factor": statistics.mean(size_growth) if size_growth else 0,
                "avg_time_growth_factor": statistics.mean(time_growth) if time_growth else 0,
                "avg_memory_growth_factor": statistics.mean(memory_growth) if memory_growth else 0,
                "time_complexity": "linear" if statistics.mean(time_growth) < 1.5 else "superlinear" if time_growth else "unknown",
                "memory_complexity": "bounded" if statistics.mean(memory_growth) < 1.2 else "growing" if memory_growth else "unknown"
            }
        
        # Performance characteristics
        if other_results:
            analysis["performance_characteristics"] = {
                "memory_efficiency_range": {
                    "min": min(r.memory_efficiency for r in other_results if r.success),
                    "max": max(r.memory_efficiency for r in other_results if r.success),
                    "avg": statistics.mean([r.memory_efficiency for r in other_results if r.success])
                },
                "processing_speed_range": {
                    "min": min(r.items_per_second for r in other_results if r.success),
                    "max": max(r.items_per_second for r in other_results if r.success),
                    "avg": statistics.mean([r.items_per_second for r in other_results if r.success])
                }
            }
        
        return analysis
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        analysis = self.analyze_performance_trends()
        
        # Performance validations
        successful_results = [r for r in self.results if r.success]
        
        if not successful_results:
            return {"error": "No successful test results"}
        
        # Critical performance validations
        avg_memory_growth = statistics.mean([r.memory_growth_mb for r in successful_results])
        max_memory_growth = max([r.memory_growth_mb for r in successful_results])
        min_processing_speed = min([r.items_per_second for r in successful_results])
        
        performance_validations = {
            "memory_bounded": max_memory_growth < 500,  # Memory growth should be < 500MB
            "acceptable_speed": min_processing_speed > 10,  # Should process > 10 items/sec minimum
            "linear_scaling": analysis.get("scaling_analysis", {}).get("time_complexity") == "linear",
            "memory_efficiency": avg_memory_growth < 100,  # Average growth < 100MB
            "all_tests_successful": len(successful_results) == len(self.results)
        }
        
        report = {
            "performance_summary": analysis.get("performance_summary", {}),
            "scaling_analysis": analysis.get("scaling_analysis", {}),
            "performance_characteristics": analysis.get("performance_characteristics", {}),
            "performance_validations": performance_validations,
            "overall_performance_acceptable": all(performance_validations.values()),
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "file_size_mb": r.file_size_mb,
                    "items_processed": r.items_processed,
                    "processing_time": r.processing_time,
                    "items_per_second": r.items_per_second,
                    "memory_growth_mb": r.memory_growth_mb,
                    "memory_efficiency": r.memory_efficiency,
                    "cpu_usage_percent": r.cpu_usage_percent
                }
                for r in self.results
            ]
        }
        
        return report
    
    def cleanup(self):
        """Clean up test files and resources."""
        self.performance_tester.file_generator.cleanup_generated_files()
        self.scalability_tester.file_generator.cleanup_generated_files()


async def main():
    """Main performance test execution."""
    logger.info("Starting Performance and Scale Validation Suite")
    logger.info("=" * 80)
    
    suite = PerformanceValidationSuite()
    
    try:
        await suite.run_all_tests()
        
        # Generate report
        report = suite.generate_performance_report()
        
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE AND SCALE TEST RESULTS")
        logger.info("=" * 80)
        
        print(f"\nPerformance Summary:")
        summary = report.get("performance_summary", {})
        print(f"  Tests Run: {summary.get('tests_run', 0)}")
        print(f"  Successful: {summary.get('successful_tests', 0)}")
        print(f"  Avg Speed: {summary.get('avg_items_per_second', 0):.1f} items/sec")
        print(f"  Avg Memory Growth: {summary.get('avg_memory_growth', 0):.1f}MB")
        
        scaling = report.get("scaling_analysis", {})
        if scaling:
            print(f"\nScaling Analysis:")
            print(f"  Time Complexity: {scaling.get('time_complexity', 'unknown')}")
            print(f"  Memory Complexity: {scaling.get('memory_complexity', 'unknown')}")
            print(f"  Avg Time Growth Factor: {scaling.get('avg_time_growth_factor', 0):.2f}x")
            print(f"  Avg Memory Growth Factor: {scaling.get('avg_memory_growth_factor', 0):.2f}x")
        
        print(f"\nPerformance Validations:")
        for validation, passed in report['performance_validations'].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {validation}: {status}")
        
        overall_status = "✅ SUCCESS" if report['overall_performance_acceptable'] else "❌ NEEDS IMPROVEMENT"
        print(f"\nOVERALL PERFORMANCE: {overall_status}")
        
        if not report['overall_performance_acceptable']:
            print("\n⚠️  PERFORMANCE ISSUES DETECTED:")
            failed_validations = [k for k, v in report['performance_validations'].items() if not v]
            for validation in failed_validations:
                print(f"  - {validation}")
        else:
            print("\n✅ EXCELLENT PERFORMANCE!")
            print("  - Memory usage is bounded and efficient")
            print("  - Processing speed meets requirements")
            print("  - System scales linearly with file size")
            print("  - Ready for production workloads")
        
        # Save detailed report
        report_file = Path(tempfile.gettempdir()) / "performance_scale_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Performance test suite failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main())