"""
Schemas for file upload endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class UploadResponseBody(BaseModel):
    """Response body for file upload."""
    
    document_id: int = Field(..., description="Database ID of the uploaded document")
    document_name: str = Field(..., description="Name of the uploaded document")
    template: Dict[str, Any] = Field(..., description="Generated template data")
    questions: List[Dict[str, Any]] = Field(..., description="Generated questions for variables")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 123,
                "document_name": "Lease_Agreement.pdf",
                "template": {
                    "template_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Lease_Agreement.pdf",
                    "doc_type": "Lease Agreement",
                    "jurisdiction": "California"
                },
                "questions": [
                    {
                        "key": "tenant_name",
                        "question": "What is the full name of the tenant?",
                        "required": True,
                        "dtype": "string"
                    }
                ]
            }
        }


class DuplicateTemplateInfo(BaseModel):
    """Information about an existing similar template."""
    
    id: int = Field(..., description="Database ID of the existing template")
    template_id: str = Field(..., description="UUID of the existing template")
    title: str = Field(..., description="Title of the existing template")
    doc_type: Optional[str] = Field(None, description="Document type")
    jurisdiction: Optional[str] = Field(None, description="Legal jurisdiction")
    file_description: Optional[str] = Field(None, description="Description of the template")
    similarity_score: float = Field(..., description="Cosine similarity score (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 42,
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Lease_Agreement_Template.pdf",
                "doc_type": "Lease Agreement",
                "jurisdiction": "California",
                "file_description": "Standard residential lease agreement",
                "similarity_score": 0.953
            }
        }


class DuplicateTemplateResponseBody(BaseModel):
    """Response body when duplicate template is detected."""
    
    existing_template: DuplicateTemplateInfo = Field(..., description="Details of the existing similar template")
    
    class Config:
        json_schema_extra = {
            "example": {
                "existing_template": {
                    "id": 42,
                    "template_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Lease_Agreement_Template.pdf",
                    "similarity_score": 0.953
                }
            }
        }


class DuplicateTemplateResponse(BaseModel):
    """Response when a duplicate template is detected."""
    
    error: bool = Field(True, description="Always True for duplicate detection")
    message: str = Field(..., description="Explanation of duplicate detection")
    body: DuplicateTemplateResponseBody = Field(..., description="Existing template information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "message": "A very similar template already exists (similarity: 95.3%)",
                "body": {
                    "existing_template": {
                        "id": 42,
                        "template_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "Lease_Agreement_Template.pdf",
                        "similarity_score": 0.953
                    }
                }
            }
        }


class UploadResponse(BaseModel):
    """Complete upload response following API standard."""
    
    error: bool = Field(False, description="False for successful uploads, True for duplicate detection")
    message: str = Field(..., description="Success or duplicate detection message")
    body: UploadResponseBody | DuplicateTemplateResponseBody = Field(..., description="Upload result or duplicate info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": False,
                "message": "File uploaded successfully",
                "body": {
                    "document_id": 123,
                    "document_name": "Lease_Agreement.pdf",
                    "template": {"template_id": "550e8400-e29b-41d4-a716-446655440000"},
                    "questions": []
                }
            }
        }

