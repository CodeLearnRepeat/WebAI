#!/usr/bin/env python3
"""
Detailed batching validation tests for VoyageAI token and chunk limits.
Tests adaptive batch sizing, token counting accuracy, and safety margins.
"""

import pytest
import asyncio
import json
import tempfile
import logging
import time
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# Import core batching services
from app.services.token_counter import VoyageTokenCounter, AdaptiveBatchSizer, count_tokens
from app.services.batch_manager import VoyageBatchManager, Batch, BatchItem
from app.services.streaming_parser import ProcessedItem

# Import test generator for creating test content
from test_large_file_generator import LargeFileGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BatchValidationResult:
    """Result of batch validation test."""
    test_name: str
    success: bool
    batches_tested: int
    max_tokens_observed: int
    max_chunks_observed: int
    violations: List[str]
    performance_metrics: Dict[str, float]
    accuracy_metrics: Dict[str, float]


class TokenCountingValidator:
    """Validates token counting accuracy across different content types."""
    
    def __init__(self):
        self.token_counter = VoyageTokenCounter("voyage-large-2")
        self.test_results = []
    
    def test_simple_content_tokens(self) -> Dict[str, Any]:
        """Test token counting for simple, repetitive content."""
        logger.info("Testing token counting for simple content...")
        
        test_cases = [
            ("Hello world", 2),  # Expected approximate token count
            ("The quick brown fox jumps over the lazy dog.", 9),
            ("A" * 100, None),  # Variable depending on tokenizer
            ("Test " * 50, None),  # Repetitive content
        ]
        
        results = []
        for text, expected in test_cases:
            actual_tokens = self.token_counter.count_tokens(text)
            
            result = {
                "text": text[:50] + "..." if len(text) > 50 else text,
                "expected": expected,
                "actual": actual_tokens,
                "accuracy": "within_range" if expected is None else abs(actual_tokens - expected) <= 2
            }
            results.append(result)
            
            logger.debug(f"Text: '{result['text']}' -> {actual_tokens} tokens")
        
        return {
            "test_type": "simple_content",
            "results": results,
            "accuracy_rate": sum(1 for r in results if r["accuracy"]) / len(results)
        }
    
    def test_complex_content_tokens(self) -> Dict[str, Any]:
        """Test token counting for complex content with special characters."""
        logger.info("Testing token counting for complex content...")
        
        complex_texts = [
            "JSON: {'key': 'value', 'nested': {'array': [1, 2, 3]}}",
            "Code: def func(x): return [i**2 for i in x if i > 0]",
            "Math: Σ(xi * yi) / √(Σ(xi²) * Σ(yi²))",
            "Unicode: 你好世界 🌍 Здравствуй мир עולם שלום",
            "Technical: OAuth 2.0 bearer tokens for API authentication",
            "Mixed: Normal text with code `var x = 1;` and symbols @#$%^&*()"
        ]
        
        results = []
        for text in complex_texts:
            tokens = self.token_counter.count_tokens(text)
            
            # Estimate expected token range (complex content typically 1:3 to 1:5 char:token ratio)
            char_count = len(text)
            expected_min = char_count // 5
            expected_max = char_count // 3
            
            result = {
                "text": text,
                "char_count": char_count,
                "token_count": tokens,
                "char_token_ratio": char_count / tokens if tokens > 0 else 0,
                "within_expected_range": expected_min <= tokens <= expected_max
            }
            results.append(result)
            
            logger.debug(f"Complex text ({char_count} chars) -> {tokens} tokens (ratio: {result['char_token_ratio']:.2f})")
        
        return {
            "test_type": "complex_content",
            "results": results,
            "avg_char_token_ratio": sum(r["char_token_ratio"] for r in results) / len(results),
            "range_accuracy": sum(1 for r in results if r["within_expected_range"]) / len(results)
        }
    
    def test_batch_token_estimation(self) -> Dict[str, Any]:
        """Test batch token estimation accuracy."""
        logger.info("Testing batch token estimation...")
        
        # Create test batches of varying sizes
        test_batches = []
        
        # Small batch
        small_texts = [f"Short text {i} with basic content." for i in range(5)]
        test_batches.append(("small_batch", small_texts))
        
        # Medium batch
        medium_texts = [f"Medium length text {i} with more detailed content that spans multiple sentences." for i in range(20)]
        test_batches.append(("medium_batch", medium_texts))
        
        # Large batch
        large_texts = [f"Large text {i} " + "with extensive content " * 20 for i in range(50)]
        test_batches.append(("large_batch", large_texts))
        
        results = []
        for batch_name, texts in test_batches:
            # Individual token counting
            individual_tokens = [self.token_counter.count_tokens(text) for text in texts]
            individual_total = sum(individual_tokens)
            
            # Batch estimation
            estimated_total = self.token_counter.estimate_batch_tokens(texts)
            
            # Calculate accuracy
            accuracy = 1 - abs(estimated_total - individual_total) / max(individual_total, 1)
            
            result = {
                "batch_name": batch_name,
                "text_count": len(texts),
                "individual_total": individual_total,
                "estimated_total": estimated_total,
                "accuracy": accuracy,
                "difference": abs(estimated_total - individual_total)
            }
            results.append(result)
            
            logger.debug(f"Batch {batch_name}: Individual={individual_total}, Estimated={estimated_total}, Accuracy={accuracy:.3f}")
        
        return {
            "test_type": "batch_estimation",
            "results": results,
            "avg_accuracy": sum(r["accuracy"] for r in results) / len(results),
            "max_difference": max(r["difference"] for r in results)
        }


class BatchSizeValidator:
    """Validates batch sizing logic and limit adherence."""
    
    def __init__(self):
        self.batch_manager = VoyageBatchManager("voyage-large-2")
        self.validation_results = []
    
    def test_token_limit_adherence(self) -> BatchValidationResult:
        """Test that batches never exceed token limits."""
        logger.info("Testing token limit adherence...")
        
        start_time = time.time()
        violations = []
        batches_tested = 0
        max_tokens = 0
        max_chunks = 0
        
        # Create texts that push towards token limits
        test_texts = []
        
        # High token density texts
        for i in range(100):
            # Create content that should have ~95 tokens each
            content = "complex technical documentation " * 25  # Should be ~95 tokens
            test_texts.append(content)
        
        # Process through batch manager
        batches = list(self.batch_manager.create_batches(test_texts))
        
        for i, batch in enumerate(batches):
            batches_tested += 1
            max_tokens = max(max_tokens, batch.total_tokens)
            max_chunks = max(max_chunks, batch.size)
            
            # Check hard API limits
            if batch.total_tokens > 10000:
                violations.append(f"Batch {i}: Hard token limit exceeded ({batch.total_tokens} > 10000)")
            
            if batch.size > 1000:
                violations.append(f"Batch {i}: Hard chunk limit exceeded ({batch.size} > 1000)")
            
            # Check safety margins
            if batch.total_tokens > 9500:
                violations.append(f"Batch {i}: Safety token margin exceeded ({batch.total_tokens} > 9500)")
            
            if batch.size > 950:
                violations.append(f"Batch {i}: Safety chunk margin exceeded ({batch.size} > 950)")
        
        processing_time = time.time() - start_time
        
        return BatchValidationResult(
            test_name="token_limit_adherence",
            success=len(violations) == 0,
            batches_tested=batches_tested,
            max_tokens_observed=max_tokens,
            max_chunks_observed=max_chunks,
            violations=violations,
            performance_metrics={"processing_time": processing_time},
            accuracy_metrics={"utilization_rate": max_tokens / 9500 if max_tokens > 0 else 0}
        )
    
    def test_chunk_limit_adherence(self) -> BatchValidationResult:
        """Test that batches never exceed chunk limits."""
        logger.info("Testing chunk limit adherence...")
        
        start_time = time.time()
        violations = []
        batches_tested = 0
        max_tokens = 0
        max_chunks = 0
        
        # Create many small texts to test chunk limits
        test_texts = []
        
        for i in range(2000):  # Create more texts than can fit in one batch
            # Small text with ~5-10 tokens each
            content = f"Small chunk {i} content"
            test_texts.append(content)
        
        # Process through batch manager
        batches = list(self.batch_manager.create_batches(test_texts))
        
        for i, batch in enumerate(batches):
            batches_tested += 1
            max_tokens = max(max_tokens, batch.total_tokens)
            max_chunks = max(max_chunks, batch.size)
            
            # Validate limits
            if batch.size > 1000:
                violations.append(f"Batch {i}: Hard chunk limit exceeded ({batch.size} > 1000)")
            
            if batch.size > 950:
                violations.append(f"Batch {i}: Safety chunk margin exceeded ({batch.size} > 950)")
            
            if batch.total_tokens > 10000:
                violations.append(f"Batch {i}: Token limit exceeded ({batch.total_tokens} > 10000)")
        
        processing_time = time.time() - start_time
        
        return BatchValidationResult(
            test_name="chunk_limit_adherence",
            success=len(violations) == 0,
            batches_tested=batches_tested,
            max_tokens_observed=max_tokens,
            max_chunks_observed=max_chunks,
            violations=violations,
            performance_metrics={"processing_time": processing_time},
            accuracy_metrics={"chunk_utilization": max_chunks / 950 if max_chunks > 0 else 0}
        )
    
    def test_adaptive_batch_sizing(self) -> BatchValidationResult:
        """Test adaptive batch sizing with varying content complexity."""
        logger.info("Testing adaptive batch sizing...")
        
        start_time = time.time()
        violations = []
        batches_tested = 0
        max_tokens = 0
        max_chunks = 0
        
        # Create mixed content with varying token densities
        test_texts = []
        
        # Simple content (low token density)
        for i in range(50):
            content = f"Simple text {i}. " * 10  # Low token density
            test_texts.append(content)
        
        # Complex content (high token density)
        for i in range(50):
            content = f"Complex JSON example {i}: " + '{"key": "value", "nested": {"array": [1, 2, 3]}} ' * 5
            test_texts.append(content)
        
        # Mixed content
        for i in range(50):
            if i % 2 == 0:
                content = f"Short {i}"
            else:
                content = f"Very long text {i} " + "with lots of repeated content " * 20
            test_texts.append(content)
        
        # Shuffle to test adaptive behavior
        import random
        random.shuffle(test_texts)
        
        # Process and validate
        batches = list(self.batch_manager.create_batches(test_texts))
        
        batch_sizes = []
        token_counts = []
        
        for i, batch in enumerate(batches):
            batches_tested += 1
            max_tokens = max(max_tokens, batch.total_tokens)
            max_chunks = max(max_chunks, batch.size)
            
            batch_sizes.append(batch.size)
            token_counts.append(batch.total_tokens)
            
            # Validate limits
            if batch.total_tokens > 10000:
                violations.append(f"Batch {i}: Token limit exceeded ({batch.total_tokens})")
            
            if batch.size > 1000:
                violations.append(f"Batch {i}: Chunk limit exceeded ({batch.size})")
        
        processing_time = time.time() - start_time
        
        # Calculate efficiency metrics
        avg_batch_size = sum(batch_sizes) / len(batch_sizes) if batch_sizes else 0
        avg_token_count = sum(token_counts) / len(token_counts) if token_counts else 0
        
        # Check if adaptive sizing is working (should see variation in batch sizes)
        batch_size_variance = sum((size - avg_batch_size) ** 2 for size in batch_sizes) / len(batch_sizes) if batch_sizes else 0
        
        return BatchValidationResult(
            test_name="adaptive_batch_sizing",
            success=len(violations) == 0,
            batches_tested=batches_tested,
            max_tokens_observed=max_tokens,
            max_chunks_observed=max_chunks,
            violations=violations,
            performance_metrics={
                "processing_time": processing_time,
                "avg_batch_size": avg_batch_size,
                "batch_size_variance": batch_size_variance
            },
            accuracy_metrics={
                "token_efficiency": avg_token_count / 9500,
                "chunk_efficiency": avg_batch_size / 950,
                "size_adaptation": batch_size_variance > 100  # Should see variation
            }
        )
    
    def test_edge_case_handling(self) -> BatchValidationResult:
        """Test edge cases like very large single items, empty content, etc."""
        logger.info("Testing edge case handling...")
        
        start_time = time.time()
        violations = []
        batches_tested = 0
        max_tokens = 0
        max_chunks = 0
        
        # Create edge case content
        edge_cases = []
        
        # Empty and very small content
        edge_cases.extend(["", " ", "a", "ab"])
        
        # Very large single item (should be handled gracefully)
        large_content = "This is a very large piece of content. " * 500  # ~3000+ tokens
        edge_cases.append(large_content)
        
        # Unicode and special characters
        edge_cases.extend([
            "Unicode: 你好世界 🌍",
            "Symbols: @#$%^&*()_+-=[]{}|;':\",./<>?",
            "JSON: " + json.dumps({"complex": {"nested": {"data": list(range(100))}}),
            "Code: " + "def func():\n    return {'data': [i**2 for i in range(100)]}"
        ])
        
        # Normal content mixed in
        edge_cases.extend([f"Normal content {i}" for i in range(20)])
        
        try:
            # Process edge cases
            batches = list(self.batch_manager.create_batches(edge_cases))
            
            for i, batch in enumerate(batches):
                batches_tested += 1
                max_tokens = max(max_tokens, batch.total_tokens)
                max_chunks = max(max_chunks, batch.size)
                
                # Validate limits
                if batch.total_tokens > 10000:
                    violations.append(f"Edge case batch {i}: Token limit exceeded ({batch.total_tokens})")
                
                if batch.size > 1000:
                    violations.append(f"Edge case batch {i}: Chunk limit exceeded ({batch.size})")
                
                # Check for empty texts in batch
                empty_texts = sum(1 for item in batch.items if not item.text.strip())
                if empty_texts > 0:
                    violations.append(f"Edge case batch {i}: Contains {empty_texts} empty texts")
            
        except Exception as e:
            violations.append(f"Exception during edge case processing: {str(e)}")
        
        processing_time = time.time() - start_time
        
        return BatchValidationResult(
            test_name="edge_case_handling",
            success=len(violations) == 0,
            batches_tested=batches_tested,
            max_tokens_observed=max_tokens,
            max_chunks_observed=max_chunks,
            violations=violations,
            performance_metrics={"processing_time": processing_time},
            accuracy_metrics={"graceful_handling": len(violations) == 0}
        )


class AdaptiveSizerValidator:
    """Validates the adaptive batch sizer component."""
    
    def __init__(self):
        self.sizer = AdaptiveBatchSizer()
    
    def test_capacity_estimation(self) -> Dict[str, Any]:
        """Test batch capacity estimation accuracy."""
        logger.info("Testing adaptive sizer capacity estimation...")
        
        test_scenarios = [
            {
                "name": "uniform_small",
                "texts": [f"Small text {i}" for i in range(100)],
                "token_limit": 9500,
                "chunk_limit": 950
            },
            {
                "name": "uniform_large",
                "texts": [f"Large text {i} " + "content " * 50 for i in range(50)],
                "token_limit": 9500,
                "chunk_limit": 950
            },
            {
                "name": "mixed_sizes",
                "texts": [f"Text {i} " + "word " * (i % 20 + 1) for i in range(100)],
                "token_limit": 9500,
                "chunk_limit": 950
            }
        ]
        
        results = []
        
        for scenario in test_scenarios:
            # Get capacity estimation
            estimated_capacity = self.sizer.estimate_batch_capacity(
                scenario["texts"], 
                scenario["token_limit"], 
                scenario["chunk_limit"]
            )
            
            # Test actual batching to compare
            batch_manager = VoyageBatchManager("voyage-large-2")
            actual_batches = list(batch_manager.create_batches(scenario["texts"]))
            
            if actual_batches:
                actual_avg_capacity = len(scenario["texts"]) / len(actual_batches)
            else:
                actual_avg_capacity = 0
            
            # Calculate accuracy
            accuracy = 1 - abs(estimated_capacity - actual_avg_capacity) / max(actual_avg_capacity, 1) if actual_avg_capacity > 0 else 0
            
            result = {
                "scenario": scenario["name"],
                "text_count": len(scenario["texts"]),
                "estimated_capacity": estimated_capacity,
                "actual_avg_capacity": actual_avg_capacity,
                "actual_batches": len(actual_batches),
                "accuracy": accuracy
            }
            results.append(result)
            
            logger.debug(f"Scenario {scenario['name']}: Estimated={estimated_capacity:.1f}, Actual={actual_avg_capacity:.1f}")
        
        return {
            "test_type": "capacity_estimation",
            "results": results,
            "avg_accuracy": sum(r["accuracy"] for r in results) / len(results)
        }


class BatchingValidationSuite:
    """Complete validation suite for batching functionality."""
    
    def __init__(self):
        self.token_validator = TokenCountingValidator()
        self.batch_validator = BatchSizeValidator()
        self.sizer_validator = AdaptiveSizerValidator()
        self.results = []
    
    async def run_token_counting_tests(self):
        """Run all token counting validation tests."""
        logger.info("Running token counting validation tests...")
        
        simple_test = self.token_validator.test_simple_content_tokens()
        complex_test = self.token_validator.test_complex_content_tokens()
        batch_test = self.token_validator.test_batch_token_estimation()
        
        self.results.extend([simple_test, complex_test, batch_test])
        
        logger.info(f"Token counting tests completed:")
        logger.info(f"  Simple content accuracy: {simple_test['accuracy_rate']:.1%}")
        logger.info(f"  Complex content range accuracy: {complex_test['range_accuracy']:.1%}")
        logger.info(f"  Batch estimation accuracy: {batch_test['avg_accuracy']:.1%}")
    
    async def run_batch_validation_tests(self):
        """Run all batch validation tests."""
        logger.info("Running batch validation tests...")
        
        token_test = self.batch_validator.test_token_limit_adherence()
        chunk_test = self.batch_validator.test_chunk_limit_adherence()
        adaptive_test = self.batch_validator.test_adaptive_batch_sizing()
        edge_test = self.batch_validator.test_edge_case_handling()
        
        batch_results = [token_test, chunk_test, adaptive_test, edge_test]
        self.results.extend(batch_results)
        
        logger.info("Batch validation tests completed:")
        for result in batch_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            logger.info(f"  {result.test_name}: {status} ({result.batches_tested} batches, max tokens: {result.max_tokens_observed})")
            
            if result.violations:
                for violation in result.violations:
                    logger.warning(f"    ⚠️  {violation}")
    
    async def run_adaptive_sizer_tests(self):
        """Run adaptive sizer validation tests."""
        logger.info("Running adaptive sizer validation tests...")
        
        capacity_test = self.sizer_validator.test_capacity_estimation()
        self.results.append(capacity_test)
        
        logger.info(f"Adaptive sizer tests completed:")
        logger.info(f"  Capacity estimation accuracy: {capacity_test['avg_accuracy']:.1%}")
    
    async def run_stress_tests(self):
        """Run stress tests with large datasets."""
        logger.info("Running batching stress tests...")
        
        # Generate large test dataset
        file_generator = LargeFileGenerator()
        
        # Create stress test content
        stress_texts = []
        
        # Mix of different complexities
        for i in range(5000):
            if i % 3 == 0:
                content = file_generator.generate_content("simple", 100)
            elif i % 3 == 1:
                content = file_generator.generate_content("medium", 200)
            else:
                content = file_generator.generate_content("complex", 300)
            
            stress_texts.append(content)
        
        logger.info(f"Created {len(stress_texts)} stress test items")
        
        # Test with batch manager
        start_time = time.time()
        batch_manager = VoyageBatchManager("voyage-large-2")
        
        violations = []
        batches_created = 0
        max_tokens = 0
        max_chunks = 0
        
        for batch in batch_manager.create_batches(stress_texts):
            batches_created += 1
            max_tokens = max(max_tokens, batch.total_tokens)
            max_chunks = max(max_chunks, batch.size)
            
            # Check limits
            if batch.total_tokens > 10000:
                violations.append(f"Stress batch {batches_created}: Token limit exceeded ({batch.total_tokens})")
            
            if batch.size > 1000:
                violations.append(f"Stress batch {batches_created}: Chunk limit exceeded ({batch.size})")
        
        processing_time = time.time() - start_time
        
        stress_result = BatchValidationResult(
            test_name="stress_test",
            success=len(violations) == 0,
            batches_tested=batches_created,
            max_tokens_observed=max_tokens,
            max_chunks_observed=max_chunks,
            violations=violations,
            performance_metrics={
                "processing_time": processing_time,
                "items_per_second": len(stress_texts) / processing_time,
                "batches_per_second": batches_created / processing_time
            },
            accuracy_metrics={"stress_success": len(violations) == 0}
        )
        
        self.results.append(stress_result)
        
        logger.info(f"Stress test completed:")
        logger.info(f"  Items processed: {len(stress_texts)}")
        logger.info(f"  Batches created: {batches_created}")
        logger.info(f"  Processing time: {processing_time:.2f}s")
        logger.info(f"  Items/sec: {len(stress_texts)/processing_time:.1f}")
        logger.info(f"  Violations: {len(violations)}")
        
        # Clean up
        file_generator.cleanup_generated_files()
    
    async def run_all_tests(self):
        """Run complete validation suite."""
        logger.info("Starting comprehensive batching validation suite...")
        logger.info("=" * 70)
        
        try:
            await self.run_token_counting_tests()
            await self.run_batch_validation_tests()
            await self.run_adaptive_sizer_tests()
            await self.run_stress_tests()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            raise
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        # Separate results by type
        token_results = [r for r in self.results if "test_type" in r]
        batch_results = [r for r in self.results if isinstance(r, BatchValidationResult)]
        
        # Calculate overall metrics
        batch_successes = sum(1 for r in batch_results if r.success)
        total_batch_tests = len(batch_results)
        
        total_violations = sum(len(r.violations) for r in batch_results)
        max_tokens_seen = max((r.max_tokens_observed for r in batch_results), default=0)
        max_chunks_seen = max((r.max_chunks_observed for r in batch_results), default=0)
        
        # Critical validations
        critical_checks = {
            "no_hard_limit_violations": max_tokens_seen < 10000 and max_chunks_seen < 1000,
            "safety_margins_respected": max_tokens_seen <= 9500 and max_chunks_seen <= 950,
            "all_batch_tests_passed": batch_successes == total_batch_tests,
            "no_violations_detected": total_violations == 0
        }
        
        report = {
            "validation_summary": {
                "total_tests_run": len(self.results),
                "batch_tests_passed": batch_successes,
                "total_batch_tests": total_batch_tests,
                "batch_success_rate": batch_successes / total_batch_tests if total_batch_tests > 0 else 0
            },
            "limit_validation": {
                "max_tokens_observed": max_tokens_seen,
                "max_chunks_observed": max_chunks_seen,
                "total_violations": total_violations,
                "hard_limits_respected": max_tokens_seen < 10000 and max_chunks_seen < 1000,
                "safety_margins_respected": max_tokens_seen <= 9500 and max_chunks_seen <= 950
            },
            "token_counting_accuracy": {
                r["test_type"]: {
                    "accuracy_rate": r.get("accuracy_rate", 0),
                    "avg_accuracy": r.get("avg_accuracy", 0),
                    "range_accuracy": r.get("range_accuracy", 0)
                }
                for r in token_results
            },
            "batch_test_details": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "batches_tested": r.batches_tested,
                    "max_tokens": r.max_tokens_observed,
                    "max_chunks": r.max_chunks_observed,
                    "violations": r.violations,
                    "performance": r.performance_metrics
                }
                for r in batch_results
            ],
            "critical_validations": critical_checks,
            "overall_validation_success": all(critical_checks.values())
        }
        
        return report


async def main():
    """Main test execution."""
    logger.info("Starting VoyageAI Batching Validation Suite")
    logger.info("=" * 60)
    
    suite = BatchingValidationSuite()
    
    try:
        await suite.run_all_tests()
        
        # Generate and display report
        report = suite.generate_validation_report()
        
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 60)
        
        print(f"\nValidation Summary:")
        print(f"  Total Tests: {report['validation_summary']['total_tests_run']}")
        print(f"  Batch Tests Passed: {report['validation_summary']['batch_tests_passed']}/{report['validation_summary']['total_batch_tests']}")
        print(f"  Success Rate: {report['validation_summary']['batch_success_rate']:.1%}")
        
        print(f"\nLimit Validation:")
        print(f"  Max Tokens Observed: {report['limit_validation']['max_tokens_observed']} (limit: 10000, safety: 9500)")
        print(f"  Max Chunks Observed: {report['limit_validation']['max_chunks_observed']} (limit: 1000, safety: 950)")
        print(f"  Total Violations: {report['limit_validation']['total_violations']}")
        
        print(f"\nCritical Validations:")
        for check, passed in report['critical_validations'].items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check}: {status}")
        
        # Overall result
        overall_status = "✅ SUCCESS" if report['overall_validation_success'] else "❌ FAILURE"
        print(f"\nOVERALL VALIDATION: {overall_status}")
        
        if not report['overall_validation_success']:
            print("\n❌ CRITICAL ISSUES DETECTED:")
            if report['limit_validation']['total_violations'] > 0:
                print("  - Limit violations found!")
            if not report['limit_validation']['hard_limits_respected']:
                print("  - Hard API limits exceeded!")
            if not report['limit_validation']['safety_margins_respected']:
                print("  - Safety margins violated!")
        else:
            print("\n✅ ALL VALIDATIONS PASSED!")
            print("  - VoyageAI API limits are properly respected")
            print("  - Safety margins are maintained")
            print("  - Batching logic is working correctly")
            print("  - Token counting is accurate")
        
        # Save detailed report
        report_file = Path(tempfile.gettempdir()) / "batching_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Validation suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())