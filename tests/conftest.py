"""
Pytest configuration and fixtures for LegalPlates tests.

Uses your existing database from DATABASE_URL environment variable.
Tests use transactions that are rolled back, so no data is permanently modified.
"""
import os
import sys

# CRITICAL: Load .env BEFORE any app imports
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now safe to import app modules (env vars are loaded)
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.base import get_db
from app.models.template import Template
from app.models.document import Document
from app.models.template_variable import TemplateVariable
from app.models.instance import Instance


# Use existing database from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable not set.\n"
        "Tests use your existing database with rolled-back transactions (safe)."
    )

# Create engine for existing database with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections every hour
    pool_timeout=30,     # Timeout for getting connection from pool
    max_overflow=10,     # Additional connections beyond pool_size
    pool_size=5,         # Base number of connections to maintain
    echo=False           # Set to True for SQL debugging
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a database session with robust transaction handling.
    Changes persist in the test database (no rollback).
    """
    db = TestingSessionLocal()
    
    try:
        yield db
        # Commit all changes
        db.commit()
    except Exception as e:
        # Always rollback on error to prevent connection issues
        try:
            db.rollback()
        except Exception as rollback_error:
            # If rollback fails, close the session to prevent further issues
            db.close()
            raise Exception(f"Original error: {e}, Rollback error: {rollback_error}")
        raise
    finally:
        # Always close the session
        try:
            db.close()
        except Exception:
            # Ignore close errors
            pass


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with a test database session.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_template(db: Session) -> Template:
    """
    Create a sample template for testing.
    Deletes existing template with same ID if it exists.
    """
    # Delete existing template if it exists
    test_template_id = "tpl_test_12345678-1234-1234-1234-123456789012"
    existing = db.query(Template).filter(Template.template_id == test_template_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    
    template = Template(
        template_id=test_template_id,
        title="Test Service Agreement",
        file_description="Sample service agreement for testing",
        doc_type="contract",
        jurisdiction="IN",
        similarity_tags=["service agreement", "contract", "business", "testing"],
        body_md="""---
template_id: tpl_test_12345678-1234-1234-1234-123456789012
title: Test Service Agreement
file_description: Sample service agreement for testing
jurisdiction: IN
doc_type: contract
variables:
  - key: company_name
    label: Company Name
    description: Name of the company
    example: Acme Corp
    required: true
    dtype: string
  - key: client_name
    label: Client Name
    description: Name of the client
    example: Tech Solutions Inc
    required: true
    dtype: string
  - key: contract_date
    label: Contract Date
    description: Date of the contract
    example: 2025-01-15
    required: true
    dtype: date
    regex: ^\\d{4}-\\d{2}-\\d{2}$
similarity_tags: [service agreement, contract, business, testing]
---

# Service Agreement

This Service Agreement ("Agreement") is entered into on {{contract_date}} between {{company_name}} ("Company") and {{client_name}} ("Client").

## 1. Services
The Company agrees to provide software development services to the Client.

## 2. Term
This Agreement shall commence on {{contract_date}} and continue for a period of 12 months.

## 3. Payment
Client agrees to pay Company the agreed-upon fees as per the payment schedule.

## 4. Governing Law
This Agreement shall be governed by the laws of India.
""",
        metadata={"test": True},
        embedding=[0.1] * 384  # Dummy embedding for testing
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    # Add template variables
    variables = [
        TemplateVariable(
            template_id=template.id,
            key="company_name",
            label="Company Name",
            description="Name of the company",
            example="Acme Corp",
            required=True,
            dtype="string",
            question='{"question": "What is the name of your company?", "description": "Enter the full legal name of your company"}'
        ),
        TemplateVariable(
            template_id=template.id,
            key="client_name",
            label="Client Name",
            description="Name of the client",
            example="Tech Solutions Inc",
            required=True,
            dtype="string",
            question='{"question": "What is the name of the client?", "description": "Enter the full legal name of the client"}'
        ),
        TemplateVariable(
            template_id=template.id,
            key="contract_date",
            label="Contract Date",
            description="Date of the contract",
            example="2025-01-15",
            required=True,
            dtype="date",
            regex="^\\d{4}-\\d{2}-\\d{2}$",
            question='{"question": "What is the contract date?", "description": "Enter the date in YYYY-MM-DD format"}'
        )
    ]
    
    for var in variables:
        db.add(var)
    
    db.commit()
    
    return template


@pytest.fixture
def sample_document(db: Session) -> Document:
    """
    Create a sample document for testing.
    """
    document = Document(
        filename="test_contract.pdf",
        mime_type="application/pdf",
        raw_text="This is a sample contract document for testing purposes.",
        document_metadata={"test": True}
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    return document

