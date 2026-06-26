#!/usr/bin/env python3
"""Tests for the production dashboard."""
import sys
sys.path.insert(0, "/mnt/agents/MAGNATRIX-OS")

from core.dashboard_production_native import DashboardServer, DashboardHTML, MetricsCollector

def test_metrics_collector():
    metrics = MetricsCollector()
    data = metrics.collect()
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "load" in data

def test_dashboard_html():
    html = DashboardHTML()
    content = html.generate({"status": "test"})
    assert "<html>" in content.lower()
    assert "MAGNATRIX-OS" in content

def test_dashboard_server_init():
    server = DashboardServer(port=18080, repo_root="/mnt/agents/MAGNATRIX-OS")
    assert server.port == 18080
    status = server.get_status()
    assert "status" in status

def test_dashboard_server_metrics():
    server = DashboardServer(port=18080, repo_root="/mnt/agents/MAGNATRIX-OS")
    metrics = server.get_metrics()
    assert "cpu" in metrics

if __name__ == "__main__":
    print("Running dashboard tests...")
    tests = [test_metrics_collector, test_dashboard_html, test_dashboard_server_init, test_dashboard_server_metrics]
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
