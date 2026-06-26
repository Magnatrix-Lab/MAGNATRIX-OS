#!/usr/bin/env python3
"""Tests for the test suite engine itself."""
import sys
sys.path.insert(0, "/mnt/agents/MAGNATRIX-OS")

from core.test_suite_engine_native import TestRunner, ModuleTestCase, IntegrationTestSuite, CoverageReporter, TestSuiteEngine

def test_test_runner_discover():
    runner = TestRunner("/mnt/agents/MAGNATRIX-OS")
    modules = runner.discover()
    assert len(modules) > 0, "Should discover modules"

def test_module_test_case():
    suite = ModuleTestCase("integration_layer_native", "/mnt/agents/MAGNATRIX-OS")
    result = suite.run_all()
    assert result.total > 0, "Should have tests"

def test_integration_suite():
    suite = IntegrationTestSuite("/mnt/agents/MAGNATRIX-OS")
    result = suite.run_all()
    assert result.total > 0, "Should have integration tests"

def test_coverage_reporter():
    cov = CoverageReporter()
    cov.start()
    x = 1 + 1
    cov.stop()
    report = cov.report()
    assert "overall_coverage" in report

def test_suite_engine():
    engine = TestSuiteEngine("/mnt/agents/MAGNATRIX-OS")
    stats = engine.get_stats()
    assert isinstance(stats, dict)

if __name__ == "__main__":
    print("Running test suite engine tests...")
    tests = [test_test_runner_discover, test_module_test_case, test_integration_suite, test_coverage_reporter, test_suite_engine]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__} - {e}")
            failed += 1
    print(f"\nResults: {passed}/{passed+failed} passed")
