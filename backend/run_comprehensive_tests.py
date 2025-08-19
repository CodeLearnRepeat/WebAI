#!/usr/bin/env python3
"""
Comprehensive test suite runner for large JSON file processing with VoyageAI batching system.
Executes all test modules and provides final validation that the solution solves the original problem.
"""

import asyncio
import json
import logging
import time
import tempfile
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class TestModuleResult:
    """Result of running a test module."""
    module_name: str
    success: bool
    execution_time: float
    summary: Dict[str, Any]
    errors: List[str]
    critical_validations: Dict[str, bool]


class ComprehensiveTestRunner:
    """Runs all test modules and generates final validation report."""
    
    def __init__(self):
        self.test_modules = [
            {
                "name": "Large File Generator",
                "module": "test_large_file_generator",
                "description": "Tests file generation for various sizes and formats",
                "critical": True
            },
            {
                "name": "Large File Processing E2E",
                "module": "test_large_file_processing",
                "description": "End-to-end tests for complete workflow with large files",
                "critical": True
            },
            {
                "name": "Batching Validation",
                "module": "test_batching_validation",
                "description": "Validates VoyageAI token and chunk limits are respected",
                "critical": True
            },
            {
                "name": "Recovery & Error Handling",
                "module": "test_recovery_error_handling", 
                "description": "Tests checkpoint recovery and error handling mechanisms",
                "critical": True
            },
            {
                "name": "Performance & Scale",
                "module": "test_performance_scale",
                "description": "Validates performance and scalability characteristics",
                "critical": True
            },
            {
                "name": "API Endpoints",
                "module": "test_api_endpoints",
                "description": "Tests all new API endpoints with realistic scenarios",
                "critical": True
            }
        ]
        
        self.results: List[TestModuleResult] = []
        
    def run_test_module(self, module_info: Dict[str, Any]) -> TestModuleResult:
        """Run a single test module and capture results."""
        module_name = module_info["name"]
        module_file = module_info["module"]
        
        logger.info(f"Running {module_name} tests...")
        logger.info(f"Description: {module_info['description']}")
        
        start_time = time.time()
        errors = []
        summary = {}
        critical_validations = {}
        success = False
        
        try:
            # Run the test module as a subprocess
            result = subprocess.run(
                [sys.executable, f"{module_file}.py"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            # Check if module executed successfully
            if result.returncode == 0:
                success = True
                logger.info(f"✅ {module_name} completed successfully in {execution_time:.2f}s")
                
                # Try to extract summary from output
                try:
                    # Look for JSON report files in temp directory
                    temp_dir = Path(tempfile.gettempdir())
                    
                    # Define report file mappings
                    report_files = {
                        "test_large_file_processing": "large_file_processing_test_report.json",
                        "test_batching_validation": "batching_validation_report.json", 
                        "test_recovery_error_handling": "recovery_error_handling_report.json",
                        "test_performance_scale": "performance_scale_report.json",
                        "test_api_endpoints": "api_endpoint_test_report.json"
                    }
                    
                    if module_file in report_files:
                        report_file = temp_dir / report_files[module_file]
                        if report_file.exists():
                            with open(report_file, 'r') as f:
                                summary = json.load(f)
                            
                            # Extract critical validations from summary
                            if module_file == "test_large_file_processing":
                                critical_validations = summary.get("critical_validations", {})
                            elif module_file == "test_batching_validation":
                                critical_validations = summary.get("critical_validations", {})
                            elif module_file == "test_recovery_error_handling":
                                critical_validations = summary.get("critical_validations", {})
                            elif module_file == "test_performance_scale":
                                critical_validations = summary.get("performance_validations", {})
                            elif module_file == "test_api_endpoints":
                                critical_validations = summary.get("critical_validations", {})
                    
                except Exception as e:
                    logger.warning(f"Could not parse detailed results for {module_name}: {e}")
                    summary = {"note": "Module completed but detailed results not available"}
                
            else:
                success = False
                errors.append(f"Module exited with code {result.returncode}")
                
                if result.stderr:
                    errors.append(f"STDERR: {result.stderr}")
                
                logger.error(f"❌ {module_name} failed after {execution_time:.2f}s")
                logger.error(f"Error output: {result.stderr}")
            
            # Log stdout for debugging if needed
            if result.stdout:
                logger.debug(f"Module output: {result.stdout}")
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            success = False
            errors.append(f"Module timed out after {execution_time:.2f}s")
            logger.error(f"❌ {module_name} timed out")
            
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            errors.append(str(e))
            logger.error(f"❌ {module_name} failed with exception: {e}")
        
        return TestModuleResult(
            module_name=module_name,
            success=success,
            execution_time=execution_time,
            summary=summary,
            errors=errors,
            critical_validations=critical_validations
        )
    
    def run_all_tests(self) -> List[TestModuleResult]:
        """Run all test modules sequentially."""
        logger.info("Starting Comprehensive Test Suite for Large JSON File Processing")
        logger.info("=" * 80)
        logger.info("Testing VoyageAI batching system with large file processing capabilities")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        for i, module_info in enumerate(self.test_modules, 1):
            logger.info(f"\n[{i}/{len(self.test_modules)}] {module_info['name']}")
            logger.info("-" * 60)
            
            result = self.run_test_module(module_info)
            self.results.append(result)
            
            # Log immediate result
            status = "✅ PASSED" if result.success else "❌ FAILED"
            logger.info(f"Result: {status} (took {result.execution_time:.2f}s)")
            
            if not result.success:
                logger.error(f"Errors: {'; '.join(result.errors)}")
                
                # For critical modules, consider stopping
                if module_info.get("critical", False):
                    logger.warning(f"Critical module {result.module_name} failed!")
        
        total_time = time.time() - start_time
        logger.info(f"\nAll test modules completed in {total_time:.2f}s")
        
        return self.results
    
    def generate_final_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive final validation report."""
        
        # Calculate overall statistics
        total_modules = len(self.results)
        passed_modules = sum(1 for r in self.results if r.success)
        failed_modules = total_modules - passed_modules
        
        total_execution_time = sum(r.execution_time for r in self.results)
        
        # Collect all critical validations
        all_critical_validations = {}
        validation_failures = []
        
        for result in self.results:
            if result.critical_validations:
                for validation, passed in result.critical_validations.items():
                    validation_key = f"{result.module_name}_{validation}"
                    all_critical_validations[validation_key] = passed
                    
                    if not passed:
                        validation_failures.append({
                            "module": result.module_name,
                            "validation": validation,
                            "status": "FAILED"
                        })
        
        # Original problem validation checklist
        original_problem_validations = {
            "voyageai_token_limit_respected": self._check_validation("test_batching_validation", "no_hard_limit_violations"),
            "voyageai_chunk_limit_respected": self._check_validation("test_batching_validation", "safety_margins_respected"),
            "large_files_processed_successfully": self._check_validation("test_large_file_processing", "all_tests_passed"),
            "memory_usage_bounded": self._check_validation("test_performance_scale", "memory_bounded"),
            "processing_scalable": self._check_validation("test_performance_scale", "linear_scaling"),
            "error_recovery_functional": self._check_validation("test_recovery_error_handling", "all_tests_passed"),
            "api_endpoints_working": self._check_validation("test_api_endpoints", "all_endpoints_functional"),
            "no_api_limit_violations": self._check_validation("test_large_file_processing", "no_api_limit_violations"),
            "checkpoint_system_working": self._check_validation("test_recovery_error_handling", "checkpoint_system_working"),
            "real_time_progress_tracking": self._check_validation("test_api_endpoints", "task_management_complete")
        }
        
        # Solution effectiveness assessment
        problem_solved = all(original_problem_validations.values())
        critical_issues = len(validation_failures)
        
        # Performance summary
        performance_summary = self._extract_performance_summary()
        
        # Final assessment
        final_assessment = self._generate_final_assessment(
            problem_solved, critical_issues, passed_modules, total_modules
        )
        
        report = {
            "validation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "test_execution_summary": {
                "total_modules": total_modules,
                "passed_modules": passed_modules,
                "failed_modules": failed_modules,
                "success_rate": passed_modules / total_modules if total_modules > 0 else 0,
                "total_execution_time": total_execution_time
            },
            "original_problem_validations": original_problem_validations,
            "problem_solved": problem_solved,
            "critical_validation_failures": validation_failures,
            "performance_summary": performance_summary,
            "final_assessment": final_assessment,
            "module_results": [
                {
                    "module_name": r.module_name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "error_count": len(r.errors),
                    "critical_validations_passed": sum(1 for v in r.critical_validations.values() if v),
                    "critical_validations_total": len(r.critical_validations)
                }
                for r in self.results
            ],
            "detailed_results": {
                r.module_name: {
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "summary": r.summary,
                    "errors": r.errors,
                    "critical_validations": r.critical_validations
                }
                for r in self.results
            }
        }
        
        return report
    
    def _check_validation(self, module_file: str, validation_name: str) -> bool:
        """Check if a specific validation passed in a module."""
        for result in self.results:
            if module_file in result.module_name.lower().replace(" ", "_").replace("&", ""):
                return result.critical_validations.get(validation_name, False)
        return False
    
    def _extract_performance_summary(self) -> Dict[str, Any]:
        """Extract performance summary from test results."""
        performance_summary = {
            "memory_efficiency": "Unknown",
            "processing_speed": "Unknown", 
            "scalability": "Unknown",
            "api_response_times": "Unknown"
        }
        
        # Extract from performance test results
        for result in self.results:
            if "performance" in result.module_name.lower():
                if result.summary:
                    perf_chars = result.summary.get("performance_characteristics", {})
                    if perf_chars:
                        performance_summary["memory_efficiency"] = "Good" if result.success else "Needs Improvement"
                        performance_summary["processing_speed"] = "Acceptable" if result.success else "Slow"
                        performance_summary["scalability"] = "Linear" if result.success else "Poor"
            
            elif "api" in result.module_name.lower():
                if result.summary:
                    perf_metrics = result.summary.get("performance_metrics", {})
                    if perf_metrics:
                        avg_time = perf_metrics.get("average_response_time", 0)
                        performance_summary["api_response_times"] = f"{avg_time:.2f}s avg" if avg_time > 0 else "Unknown"
        
        return performance_summary
    
    def _generate_final_assessment(self, problem_solved: bool, critical_issues: int, passed_modules: int, total_modules: int) -> Dict[str, Any]:
        """Generate final assessment of the solution."""
        
        if problem_solved and critical_issues == 0 and passed_modules == total_modules:
            verdict = "SOLUTION FULLY VALIDATED"
            confidence = "HIGH"
            recommendation = "Deploy to production"
            status = "SUCCESS"
        elif problem_solved and critical_issues <= 2:
            verdict = "SOLUTION MOSTLY VALIDATED"
            confidence = "MEDIUM-HIGH" 
            recommendation = "Address minor issues then deploy"
            status = "SUCCESS_WITH_NOTES"
        elif passed_modules >= total_modules * 0.8:
            verdict = "SOLUTION PARTIALLY VALIDATED"
            confidence = "MEDIUM"
            recommendation = "Address critical issues before deployment"
            status = "NEEDS_IMPROVEMENT"
        else:
            verdict = "SOLUTION NEEDS SIGNIFICANT WORK"
            confidence = "LOW"
            recommendation = "Do not deploy, address critical failures"
            status = "FAILURE"
        
        return {
            "verdict": verdict,
            "confidence_level": confidence,
            "recommendation": recommendation,
            "status": status,
            "key_achievements": self._get_key_achievements(),
            "remaining_issues": self._get_remaining_issues()
        }
    
    def _get_key_achievements(self) -> List[str]:
        """Get list of key achievements based on test results."""
        achievements = []
        
        for result in self.results:
            if result.success:
                if "batching" in result.module_name.lower():
                    achievements.append("✅ VoyageAI API limits properly respected")
                elif "large_file" in result.module_name.lower():
                    achievements.append("✅ Large file processing implemented successfully")
                elif "performance" in result.module_name.lower():
                    achievements.append("✅ Performance and scalability validated")
                elif "recovery" in result.module_name.lower():
                    achievements.append("✅ Error recovery and checkpoints working")
                elif "api" in result.module_name.lower():
                    achievements.append("✅ API endpoints functional with task management")
        
        if len([r for r in self.results if r.success]) == len(self.results):
            achievements.append("✅ All test modules passed successfully")
        
        return achievements
    
    def _get_remaining_issues(self) -> List[str]:
        """Get list of remaining issues based on test results."""
        issues = []
        
        for result in self.results:
            if not result.success:
                issues.append(f"❌ {result.module_name} test failures")
                for error in result.errors[:3]:  # Limit to first 3 errors
                    issues.append(f"   • {error}")
        
        # Check for critical validation failures
        for result in self.results:
            for validation, passed in result.critical_validations.items():
                if not passed:
                    issues.append(f"⚠️ Critical validation failed: {validation} in {result.module_name}")
        
        return issues


def main():
    """Main execution function."""
    logger.info("Starting Comprehensive Large JSON File Processing Test Suite")
    logger.info("Testing VoyageAI batching system implementation")
    logger.info("=" * 80)
    
    runner = ComprehensiveTestRunner()
    
    try:
        # Run all test modules
        results = runner.run_all_tests()
        
        # Generate final report
        report = runner.generate_final_validation_report()
        
        # Display comprehensive results
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE TEST SUITE RESULTS")
        logger.info("=" * 80)
        
        print(f"\n📊 TEST EXECUTION SUMMARY:")
        summary = report["test_execution_summary"]
        print(f"   Total Modules: {summary['total_modules']}")
        print(f"   Passed: {summary['passed_modules']}")
        print(f"   Failed: {summary['failed_modules']}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print(f"   Total Time: {summary['total_execution_time']:.1f}s")
        
        print(f"\n🎯 ORIGINAL PROBLEM VALIDATION:")
        problem_validations = report["original_problem_validations"]
        for validation, passed in problem_validations.items():
            status = "✅ SOLVED" if passed else "❌ NOT SOLVED"
            print(f"   {validation}: {status}")
        
        print(f"\n⚡ PERFORMANCE SUMMARY:")
        perf = report["performance_summary"]
        for metric, value in perf.items():
            print(f"   {metric}: {value}")
        
        print(f"\n🏆 FINAL ASSESSMENT:")
        assessment = report["final_assessment"]
        print(f"   Verdict: {assessment['verdict']}")
        print(f"   Confidence: {assessment['confidence_level']}")
        print(f"   Recommendation: {assessment['recommendation']}")
        print(f"   Status: {assessment['status']}")
        
        if report["problem_solved"]:
            print(f"\n🎉 ORIGINAL PROBLEM SOLVED!")
            print(f"   ✅ VoyageAI batch size limitations have been successfully addressed")
            print(f"   ✅ Large JSON files can now be processed without exceeding API limits")
            print(f"   ✅ Memory usage is bounded and efficient")
            print(f"   ✅ Real-time progress tracking and error recovery implemented")
        else:
            print(f"\n⚠️ SOLUTION NEEDS ATTENTION")
            print(f"   Some aspects of the original problem remain unresolved")
        
        print(f"\n🏅 KEY ACHIEVEMENTS:")
        for achievement in assessment["key_achievements"]:
            print(f"   {achievement}")
        
        if assessment["remaining_issues"]:
            print(f"\n🔧 REMAINING ISSUES:")
            for issue in assessment["remaining_issues"]:
                print(f"   {issue}")
        
        # Final verdict
        if report["problem_solved"] and summary["success_rate"] >= 0.9:
            print(f"\n🟢 OVERALL RESULT: COMPREHENSIVE SUCCESS")
            print(f"   The VoyageAI batching system solution is validated and ready for production!")
        elif report["problem_solved"]:
            print(f"\n🟡 OVERALL RESULT: SUCCESS WITH MINOR ISSUES")
            print(f"   The solution works but has some areas for improvement")
        else:
            print(f"\n🔴 OVERALL RESULT: NEEDS SIGNIFICANT WORK")
            print(f"   Critical issues must be resolved before deployment")
        
        # Save comprehensive report
        report_file = Path(tempfile.gettempdir()) / "comprehensive_test_validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Return appropriate exit code
        if report["problem_solved"] and summary["success_rate"] >= 0.8:
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # Failure
        
    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()