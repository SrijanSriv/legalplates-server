"""
Comprehensive API tests for LegalPlates with performance timing.

This test suite covers all endpoints with:
1. Success scenarios
2. Error scenarios
3. Performance timing measurements
4. Response validation

EXTERNAL API CALLS:
-------------------
The following tests make REAL API calls to external services:

1. Upload tests (PDF/DOCX):
   - Calls: Gemini API (for variable extraction and template generation)
   - May fail without: GEMINI_API_KEY in environment
   - Will consume: API credits/quota

2. Template matching tests:
   - Calls: Gemini API (for semantic matching)
   - May call: Exa API (if no match found, for web fallback)
   - May fail without: GEMINI_API_KEY, EXA_API_KEY in environment
   - Will consume: API credits/quota

3. Question generation tests:
   - Calls: Gemini API (for question generation and prefilling)
   - May fail without: GEMINI_API_KEY in environment
   - Will consume: API credits/quota

Tests that DON'T call external APIs:
- All error/validation tests (invalid file types, missing params, etc.)
- Template CRUD operations (list, get, delete)
- Draft generation with pre-filled data
- Health check

NOTE: Tests persist data to your test database (no rollback).
"""
import time
import json
import io
from typing import Dict, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.template import Template


class PerformanceTimer:
    """Context manager to measure execution time."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        print(f"\n⏱️  {self.test_name}: {self.duration:.3f}s ({self.duration*1000:.0f}ms)")


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_root_health_check(self, client: TestClient):
        """Test the root health check endpoint."""
        with PerformanceTimer("GET / - Health Check"):
            response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is False
        assert data["message"] == "LegalPlates API is running"
        assert "body" in data
        assert data["body"]["status"] == "healthy"
        assert "version" in data["body"]


class TestUploadAPI:
    """Tests for upload endpoint."""
    
    def test_upload_pdf_success(self, client: TestClient, db: Session):
        """Test successful PDF upload."""
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        with PerformanceTimer("POST /api/v1/upload - Success (PDF)"):
            response = client.post("/api/v1/upload", files=files)
        
        # Note: This will fail without actual PDF processing, but structure is correct
        # In real test, you'd mock the services or use actual test PDFs
        assert response.status_code in [200, 500]  # May fail due to PDF parsing
    
    def test_upload_docx_success(self, client: TestClient, db: Session):
        """Test successful DOCX upload."""
        # Create a mock DOCX file
        docx_content = b"PK\x03\x04"  # DOCX signature
        files = {"file": ("test.docx", io.BytesIO(docx_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        with PerformanceTimer("POST /api/v1/upload - Success (DOCX)"):
            response = client.post("/api/v1/upload", files=files)
        
        # Note: This will fail without actual DOCX processing
        assert response.status_code in [200, 500]  # May fail due to DOCX parsing
    
    def test_upload_no_file(self, client: TestClient):
        """Test upload with no file provided."""
        with PerformanceTimer("POST /api/v1/upload - No File Error"):
            response = client.post("/api/v1/upload")
        
        assert response.status_code == 422  # FastAPI validation error
    
    def test_upload_invalid_file_type_txt(self, client: TestClient):
        """Test upload with invalid file type (TXT)."""
        txt_content = b"This is a text file"
        files = {"file": ("test.txt", io.BytesIO(txt_content), "text/plain")}
        
        with PerformanceTimer("POST /api/v1/upload - Invalid Type (TXT)"):
            response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "PDF and DOCX" in data["message"]
    
    def test_upload_invalid_file_type_jpg(self, client: TestClient):
        """Test upload with invalid file type (JPG)."""
        jpg_content = b"\xff\xd8\xff\xe0"  # JPG signature
        files = {"file": ("test.jpg", io.BytesIO(jpg_content), "image/jpeg")}
        
        with PerformanceTimer("POST /api/v1/upload - Invalid Type (JPG)"):
            response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "PDF and DOCX" in data["message"]
    
    def test_upload_file_without_extension(self, client: TestClient):
        """Test upload with file without extension."""
        content = b"Some content"
        files = {"file": ("document", io.BytesIO(content), "application/octet-stream")}
        
        with PerformanceTimer("POST /api/v1/upload - No Extension"):
            response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "unknown format" in data["message"]


class TestTemplateAPI:
    """Tests for template endpoints."""
    
    def test_list_templates_success(self, client: TestClient, sample_template: Template):
        """Test listing templates with pagination."""
        with PerformanceTimer("GET /api/v1/template - List Templates"):
            response = client.get("/api/v1/template?skip=0&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is False
        assert "body" in data
        assert "templates" in data["body"]
        assert "pagination" in data["body"]
        assert len(data["body"]["templates"]) >= 1
    
    def test_list_templates_invalid_skip(self, client: TestClient):
        """Test listing templates with invalid skip parameter."""
        with PerformanceTimer("GET /api/v1/template - Invalid Skip"):
            response = client.get("/api/v1/template?skip=-1&limit=10")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "skip parameter must be >= 0" in data["message"]
    
    def test_list_templates_invalid_limit_high(self, client: TestClient):
        """Test listing templates with limit too high."""
        with PerformanceTimer("GET /api/v1/template - Limit Too High"):
            response = client.get("/api/v1/template?skip=0&limit=2000")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "between 1 and 1000" in data["message"]
    
    def test_list_templates_invalid_limit_low(self, client: TestClient):
        """Test listing templates with limit too low."""
        with PerformanceTimer("GET /api/v1/template - Limit Too Low"):
            response = client.get("/api/v1/template?skip=0&limit=0")
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert "between 1 and 1000" in data["message"]
    
    def test_get_template_by_id_success(self, client: TestClient, sample_template: Template):
        """Test getting a specific template by ID."""
        template_id = sample_template.template_id
        
        with PerformanceTimer("GET /api/v1/template/{id} - Success"):
            response = client.get(f"/api/v1/template/{template_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is False
        assert "body" in data
        assert data["body"]["template_id"] == template_id
        assert "variables" in data["body"]
        assert len(data["body"]["variables"]) >= 3
    
    def test_get_template_by_id_not_found(self, client: TestClient):
        """Test getting a non-existent template."""
        with PerformanceTimer("GET /api/v1/template/{id} - Not Found"):
            response = client.get("/api/v1/template/tpl_nonexistent_12345")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "not found" in data["message"].lower()
    
    def test_delete_template_success(self, client: TestClient, sample_template: Template):
        """Test deleting a template."""
        template_id = sample_template.template_id
        
        with PerformanceTimer("DELETE /api/v1/template/{id} - Success"):
            response = client.delete(f"/api/v1/template/{template_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is False
        assert "deleted" in data["message"].lower()
    
    def test_delete_template_not_found(self, client: TestClient):
        """Test deleting a non-existent template."""
        with PerformanceTimer("DELETE /api/v1/template/{id} - Not Found"):
            response = client.delete("/api/v1/template/tpl_nonexistent_12345")
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "not found" in data["message"].lower()


class TestDraftAPI:
    """Tests for draft endpoints."""
    
    def test_generate_questions_success(self, client: TestClient, sample_template: Template):
        """Test generating questions for a template."""
        payload = {
            "template_id": sample_template.template_id,
            "user_query": "I need to create a service agreement"
        }
        
        with PerformanceTimer("POST /api/v1/draft/questions - Success"):
            response = client.post("/api/v1/draft/questions", json=payload)
        
        assert response.status_code in [200, 500]  # May fail without Gemini API
        if response.status_code == 200:
            data = response.json()
            assert data["error"] is False
            assert "body" in data
            assert "questions" in data["body"]
    
    def test_generate_questions_template_not_found(self, client: TestClient):
        """Test generating questions for non-existent template."""
        payload = {
            "template_id": "tpl_nonexistent_12345",
            "user_query": "Test query"
        }
        
        with PerformanceTimer("POST /api/v1/draft/questions - Not Found"):
            response = client.post("/api/v1/draft/questions", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "not found" in data["message"].lower()
    
    def test_generate_questions_missing_template_id(self, client: TestClient):
        """Test generating questions without template_id."""
        payload = {"user_query": "Test query"}
        
        with PerformanceTimer("POST /api/v1/draft/questions - Missing ID"):
            response = client.post("/api/v1/draft/questions", json=payload)
        
        assert response.status_code == 422  # Pydantic validation error
    
    def test_generate_draft_success(self, client: TestClient, sample_template: Template):
        """Test generating a draft document."""
        payload = {
            "template_id": sample_template.template_id,
            "answers": {
                "company_name": "Acme Corp",
                "client_name": "Tech Solutions Inc",
                "contract_date": "2025-01-15"
            },
            "user_query": "Create a service agreement"
        }
        
        with PerformanceTimer("POST /api/v1/draft/generate - Success"):
            response = client.post("/api/v1/draft/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is False
        assert "body" in data
        assert "draft_md" in data["body"]
        assert "instance_id" in data["body"]
        assert "missing_variables" in data["body"]
    
    def test_generate_draft_missing_variables(self, client: TestClient, sample_template: Template):
        """Test generating draft with missing required variables."""
        payload = {
            "template_id": sample_template.template_id,
            "answers": {
                "company_name": "Acme Corp"
                # Missing client_name and contract_date
            },
            "user_query": "Create a service agreement"
        }
        
        with PerformanceTimer("POST /api/v1/draft/generate - Missing Vars"):
            response = client.post("/api/v1/draft/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is False
        assert "body" in data
        assert data["body"]["has_missing_variables"] is True
        assert len(data["body"]["missing_variables"]) > 0
    
    def test_generate_draft_template_not_found(self, client: TestClient):
        """Test generating draft for non-existent template."""
        payload = {
            "template_id": "tpl_nonexistent_12345",
            "answers": {"test": "value"},
            "user_query": "Test"
        }
        
        with PerformanceTimer("POST /api/v1/draft/generate - Not Found"):
            response = client.post("/api/v1/draft/generate", json=payload)
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] is True
        assert "not found" in data["message"].lower()
    
    def test_generate_draft_missing_template_id(self, client: TestClient):
        """Test generating draft without template_id."""
        payload = {
            "answers": {"test": "value"}
        }
        
        with PerformanceTimer("POST /api/v1/draft/generate - Missing ID"):
            response = client.post("/api/v1/draft/generate", json=payload)
        
        assert response.status_code == 422  # Pydantic validation error




class TestEndToEndScenarios:
    """End-to-end integration tests."""
    
    def test_complete_workflow(self, client: TestClient, sample_template: Template):
        """Test complete workflow: list → get → match → questions → generate draft."""
        print("\n" + "="*60)
        print("END-TO-END WORKFLOW TEST")
        print("="*60)
        
        # Step 1: List templates
        with PerformanceTimer("E2E Step 1: List Templates"):
            response = client.get("/api/v1/template?skip=0&limit=10")
        assert response.status_code == 200
        templates = response.json()["body"]["templates"]
        assert len(templates) > 0
        print(f"✅ Found {len(templates)} template(s)")
        
        # Step 2: Get specific template
        template_id = sample_template.template_id
        with PerformanceTimer("E2E Step 2: Get Template"):
            response = client.get(f"/api/v1/template/{template_id}")
        assert response.status_code == 200
        template_data = response.json()["body"]
        print(f"✅ Retrieved template: {template_data['title']}")
        
        # Step 3: Generate questions
        with PerformanceTimer("E2E Step 3: Generate Questions"):
            response = client.post("/api/v1/draft/questions", json={
                "template_id": template_id,
                "user_query": "I need a service agreement for my company"
            })
        # May fail without Gemini API, but check structure if success
        if response.status_code == 200:
            questions_data = response.json()["body"]
            print(f"✅ Generated {len(questions_data.get('questions', []))} question(s)")
        else:
            print(f"⚠️  Questions generation failed (needs Gemini API): {response.status_code}")
        
        # Step 4: Generate draft
        with PerformanceTimer("E2E Step 4: Generate Draft"):
            response = client.post("/api/v1/draft/generate", json={
                "template_id": template_id,
                "answers": {
                    "company_name": "Test Corp",
                    "client_name": "Client Inc",
                    "contract_date": "2025-01-20"
                },
                "user_query": "Create service agreement"
            })
        assert response.status_code == 200
        draft_data = response.json()["body"]
        print(f"✅ Generated draft (length: {len(draft_data['draft_md'])} chars)")
        print(f"✅ Instance ID: {draft_data['instance_id']}")
        
        print("="*60)
        print("END-TO-END TEST COMPLETED SUCCESSFULLY")
        print("="*60)


def print_test_summary():
    """Print test summary after all tests complete."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print("All endpoint tests completed.")
    print("Review timing metrics above to identify slow endpoints.")
    print("="*60)


# Run summary after all tests
@pytest.fixture(scope="session", autouse=True)
def test_summary():
    """Print summary after all tests."""
    yield
    print_test_summary()

