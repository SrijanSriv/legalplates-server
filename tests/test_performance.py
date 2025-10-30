"""
Performance benchmarking tests for LegalPlates API.

These tests specifically focus on measuring and reporting performance metrics.
"""
import time
import statistics
from typing import List, Dict, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.template import Template


class PerformanceBenchmark:
    """Class to collect and report performance metrics."""
    
    results: Dict[str, List[float]] = {}
    
    @classmethod
    def record(cls, test_name: str, duration: float):
        """Record a test duration."""
        if test_name not in cls.results:
            cls.results[test_name] = []
        cls.results[test_name].append(duration)
    
    @classmethod
    def report(cls):
        """Print performance report."""
        if not cls.results:
            return
        
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK REPORT")
        print("="*80)
        print(f"{'Endpoint':<50} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}")
        print("-"*80)
        
        for test_name, durations in sorted(cls.results.items()):
            avg_ms = statistics.mean(durations) * 1000
            min_ms = min(durations) * 1000
            max_ms = max(durations) * 1000
            
            # Color code: green if <100ms, yellow if <500ms, red if >=500ms
            if avg_ms < 100:
                color = "🟢"
            elif avg_ms < 500:
                color = "🟡"
            else:
                color = "🔴"
            
            print(f"{color} {test_name:<47} {avg_ms:>10.0f} {min_ms:>10.0f} {max_ms:>10.0f}")
        
        print("="*80)
        print("\nLegend:")
        print("🟢 Fast (<100ms)  🟡 Acceptable (<500ms)  🔴 Slow (>=500ms)")
        print("="*80)


def measure_performance(test_name: str, func, *args, **kwargs):
    """Measure and record performance of a function call."""
    start = time.time()
    result = func(*args, **kwargs)
    duration = time.time() - start
    PerformanceBenchmark.record(test_name, duration)
    return result, duration


class TestPerformance:
    """Performance tests for all endpoints."""
    
    @pytest.mark.parametrize("iteration", range(3))
    def test_health_check_performance(self, client: TestClient, iteration: int):
        """Benchmark health check endpoint (3 iterations)."""
        response, duration = measure_performance(
            "GET / (Health Check)",
            client.get,
            "/"
        )
        assert response.status_code == 200
        print(f"  Iteration {iteration + 1}: {duration*1000:.0f}ms")
    
    @pytest.mark.parametrize("iteration", range(3))
    def test_list_templates_performance(self, client: TestClient, sample_template: Template, iteration: int):
        """Benchmark list templates endpoint (3 iterations)."""
        response, duration = measure_performance(
            "GET /api/v1/template (List)",
            client.get,
            "/api/v1/template?skip=0&limit=10"
        )
        assert response.status_code == 200
        print(f"  Iteration {iteration + 1}: {duration*1000:.0f}ms")
    
    @pytest.mark.parametrize("iteration", range(3))
    def test_get_template_performance(self, client: TestClient, sample_template: Template, iteration: int):
        """Benchmark get template by ID endpoint (3 iterations)."""
        response, duration = measure_performance(
            "GET /api/v1/template/{id}",
            client.get,
            f"/api/v1/template/{sample_template.template_id}"
        )
        assert response.status_code == 200
        print(f"  Iteration {iteration + 1}: {duration*1000:.0f}ms")
    
    @pytest.mark.parametrize("iteration", range(3))
    def test_generate_draft_performance(self, client: TestClient, sample_template: Template, iteration: int):
        """Benchmark draft generation endpoint (3 iterations)."""
        payload = {
            "template_id": sample_template.template_id,
            "answers": {
                "company_name": "Acme Corp",
                "client_name": "Tech Solutions Inc",
                "contract_date": "2025-01-15"
            },
            "user_query": "Create a service agreement"
        }
        
        response, duration = measure_performance(
            "POST /api/v1/draft/generate",
            client.post,
            "/api/v1/draft/generate",
            json=payload
        )
        assert response.status_code == 200
        print(f"  Iteration {iteration + 1}: {duration*1000:.0f}ms")


class TestLoadTesting:
    """Basic load testing - multiple concurrent-like requests."""
    
    def test_load_list_templates(self, client: TestClient, sample_template: Template):
        """Test list templates under load (10 sequential requests)."""
        print("\n" + "="*60)
        print("LOAD TEST: List Templates (10 requests)")
        print("="*60)
        
        durations = []
        for i in range(10):
            start = time.time()
            response = client.get("/api/v1/template?skip=0&limit=10")
            duration = time.time() - start
            durations.append(duration)
            
            assert response.status_code == 200
            print(f"Request {i+1:2d}: {duration*1000:6.0f}ms")
        
        avg = statistics.mean(durations) * 1000
        min_d = min(durations) * 1000
        max_d = max(durations) * 1000
        
        print("-"*60)
        print(f"Average: {avg:.0f}ms | Min: {min_d:.0f}ms | Max: {max_d:.0f}ms")
        print("="*60)
    
    def test_load_generate_draft(self, client: TestClient, sample_template: Template):
        """Test draft generation under load (5 sequential requests)."""
        print("\n" + "="*60)
        print("LOAD TEST: Generate Draft (5 requests)")
        print("="*60)
        
        payload = {
            "template_id": sample_template.template_id,
            "answers": {
                "company_name": "Acme Corp",
                "client_name": "Tech Solutions Inc",
                "contract_date": "2025-01-15"
            },
            "user_query": "Create a service agreement"
        }
        
        durations = []
        for i in range(5):
            start = time.time()
            response = client.post("/api/v1/draft/generate", json=payload)
            duration = time.time() - start
            durations.append(duration)
            
            assert response.status_code == 200
            print(f"Request {i+1}: {duration*1000:6.0f}ms")
        
        avg = statistics.mean(durations) * 1000
        min_d = min(durations) * 1000
        max_d = max(durations) * 1000
        
        print("-"*60)
        print(f"Average: {avg:.0f}ms | Min: {min_d:.0f}ms | Max: {max_d:.0f}ms")
        print("="*60)


class TestDatabasePerformance:
    """Test database query performance."""
    
    def test_query_templates_performance(self, db: Session, sample_template: Template):
        """Test database query performance for templates."""
        from app.models.template import Template
        
        print("\n" + "="*60)
        print("DATABASE PERFORMANCE TEST")
        print("="*60)
        
        # Test 1: Query all templates
        start = time.time()
        templates = db.query(Template).all()
        duration = (time.time() - start) * 1000
        print(f"Query all templates: {duration:.2f}ms ({len(templates)} results)")
        
        # Test 2: Query by template_id
        start = time.time()
        template = db.query(Template).filter(
            Template.template_id == sample_template.template_id
        ).first()
        duration = (time.time() - start) * 1000
        print(f"Query by template_id: {duration:.2f}ms")
        
        # Test 3: Query with pagination
        start = time.time()
        templates = db.query(Template).offset(0).limit(10).all()
        duration = (time.time() - start) * 1000
        print(f"Query with pagination (10): {duration:.2f}ms")
        
        print("="*60)


@pytest.fixture(scope="session", autouse=True)
def performance_report():
    """Print performance report after all tests."""
    yield
    PerformanceBenchmark.report()

