"""
Schemas for template endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.variable import VariableSchema
from app.schemas.common import PaginationMeta


class TemplateBase(BaseModel):
    """Base template schema with common fields."""
    
    template_id: str = Field(..., description="Unique template identifier (UUID)")
    title: str = Field(..., description="Template title")
    file_description: Optional[str] = Field(None, description="Description of the template")
    doc_type: Optional[str] = Field(None, description="Type of document (e.g., 'Lease Agreement', 'NDA')")
    jurisdiction: Optional[str] = Field(None, description="Legal jurisdiction (e.g., 'California', 'New York')")
    similarity_tags: List[str] = Field(default_factory=list, description="Tags for semantic search")
    created_at: Optional[str] = Field(None, description="ISO 8601 timestamp of creation")


class TemplateDetail(TemplateBase):
    """Detailed template schema including body and variables."""
    
    body_md: str = Field(..., description="Template content in Markdown with {{variable}} placeholders")
    template_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    variables: List[VariableSchema] = Field(default_factory=list, description="List of template variables")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "California Residential Lease",
                "file_description": "Standard residential lease agreement for California",
                "doc_type": "Lease Agreement",
                "jurisdiction": "California",
                "similarity_tags": ["rental", "lease", "residential", "California"],
                "body_md": "This lease agreement is made between {{landlord_name}} and {{tenant_name}}...",
                "template_metadata": {},
                "variables": [
                    {
                        "key": "tenant_name",
                        "label": "Tenant Name",
                        "required": True,
                        "dtype": "string"
                    }
                ],
                "created_at": "2024-10-21T10:00:00Z"
            }
        }


class TemplateListItem(TemplateBase):
    """Template item in list view (without full body)."""
    
    id: int = Field(..., description="Database ID")
    variables: List[VariableSchema] = Field(default_factory=list, description="List of template variables")
    
    class Config:
        from_attributes = True


class TemplateListResponseBody(BaseModel):
    """Response body for template list."""
    
    templates: List[TemplateListItem] = Field(..., description="List of templates")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "templates": [
                    {
                        "id": 1,
                        "template_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "California Residential Lease",
                        "doc_type": "Lease Agreement",
                        "jurisdiction": "California",
                        "similarity_tags": ["rental", "lease"],
                        "variables": [],
                        "created_at": "2024-10-21T10:00:00Z"
                    }
                ],
                "pagination": {
                    "total": 100,
                    "skip": 0,
                    "limit": 10,
                    "returned": 10
                }
            }
        }


class TemplateListResponse(BaseModel):
    """Complete template list response."""
    
    error: bool = Field(False, description="Always False for successful requests")
    message: str = Field(..., description="Success message")
    body: TemplateListResponseBody = Field(..., description="Template list data")


class TemplateResponse(BaseModel):
    """Complete single template response."""
    
    error: bool = Field(False, description="Always False for successful requests")
    message: str = Field(..., description="Success message")
    body: TemplateDetail = Field(..., description="Template data")


class TemplateDeleteResponseBody(BaseModel):
    """Response body for template deletion."""
    
    template_id: str = Field(..., description="ID of the deleted template")
    success: bool = Field(True, description="Always True for successful deletions")


class TemplateDeleteResponse(BaseModel):
    """Complete template deletion response."""
    
    error: bool = Field(False, description="Always False for successful deletions")
    message: str = Field(..., description="Deletion confirmation message")
    body: TemplateDeleteResponseBody = Field(..., description="Deletion result")

