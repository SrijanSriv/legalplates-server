"""
Schemas for draft generation endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any


# ============================================================================
# Template Matching
# ============================================================================

class TemplateMatchRequest(BaseModel):
    """Request for matching a user query to templates."""
    
    user_query: str = Field(..., min_length=1, max_length=5000, description="User's natural language query describing what document they need")
    
    @validator('user_query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('user_query cannot be empty or whitespace only')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_query": "I need a rental agreement for a house in California"
            }
        }


class TemplateMatch(BaseModel):
    """Information about a matched template."""
    
    template_id: str = Field(..., description="Unique template identifier")
    title: str = Field(..., description="Template title")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    explanation: str = Field(..., description="Explanation of why this template matches")
    doc_type: Optional[str] = Field(None, description="Type of document")
    jurisdiction: Optional[str] = Field(None, description="Legal jurisdiction")
    semantic_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Semantic similarity score from vector search")
    source: str = Field("database", description="Source of template: 'database' or 'web'")
    web_url: Optional[str] = Field(None, description="URL if template was sourced from web")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "California Residential Lease Agreement",
                "confidence": 0.92,
                "explanation": "This template matches because it's a residential lease specifically for California properties",
                "doc_type": "Lease Agreement",
                "jurisdiction": "California",
                "semantic_similarity": 0.87
            }
        }


class TemplateMatchResponseBody(BaseModel):
    """Response body for template matching."""
    
    top_match: Optional[TemplateMatch] = Field(None, description="Best matching template")
    alternatives: List[TemplateMatch] = Field(default_factory=list, description="Alternative template matches")
    found: bool = Field(..., description="Whether any suitable match was found")
    message: Optional[str] = Field(None, description="Additional information about the search")
    
    class Config:
        json_schema_extra = {
            "example": {
                "top_match": {
                    "template_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "California Residential Lease",
                    "confidence": 0.92,
                    "explanation": "Best match for California rental agreements",
                    "doc_type": "Lease Agreement",
                    "jurisdiction": "California",
                    "semantic_similarity": 0.87
                },
                "alternatives": [],
                "found": True,
                "message": None
            }
        }


class TemplateMatchResponse(BaseModel):
    """Complete template matching response."""
    
    error: bool = Field(False, description="Always False for successful requests")
    message: str = Field(..., description="Search result message")
    body: TemplateMatchResponseBody = Field(..., description="Match results")


# ============================================================================
# Question Generation
# ============================================================================

class QuestionRequest(BaseModel):
    """Request for generating questions from a template."""
    
    template_id: str = Field(..., min_length=1, description="Template identifier")
    user_query: Optional[str] = Field(None, max_length=5000, description="Optional user query for prefilling variables")
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v.strip():
            raise ValueError('template_id cannot be empty or whitespace only')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_query": "Lease for John Doe starting January 1st, 2024"
            }
        }


class Question(BaseModel):
    """A question for a template variable."""
    
    key: str = Field(..., description="Variable key")
    question: str = Field(..., description="Human-friendly question text")
    description: Optional[str] = Field(None, description="Additional description")
    example: Optional[str] = Field(None, description="Example value")
    required: bool = Field(False, description="Whether this field is required")
    dtype: str = Field("string", description="Data type")
    regex: Optional[str] = Field(None, description="Validation regex pattern")
    enum_values: Optional[List[str]] = Field(None, description="Allowed values for enum types")
    
    class Config:
        json_schema_extra = {
            "example": {
                "key": "tenant_name",
                "question": "What is the full legal name of the tenant?",
                "description": "The tenant's complete name as it should appear on the lease",
                "example": "John Doe",
                "required": True,
                "dtype": "string",
                "regex": None,
                "enum_values": None
            }
        }


class QuestionResponseBody(BaseModel):
    """Response body for question generation."""
    
    questions: List[Question] = Field(..., description="List of questions to ask the user")
    prefilled: Dict[str, Any] = Field(default_factory=dict, description="Pre-filled variable values from user query")
    template_id: str = Field(..., description="Template identifier")
    template_title: str = Field(..., description="Template title")
    message: Optional[str] = Field(None, description="Additional information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "questions": [
                    {
                        "key": "tenant_name",
                        "question": "What is the tenant's full name?",
                        "required": True,
                        "dtype": "string"
                    }
                ],
                "prefilled": {
                    "tenant_name": "John Doe"
                },
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "template_title": "California Residential Lease",
                "message": None
            }
        }


class QuestionResponse(BaseModel):
    """Complete question generation response."""
    
    error: bool = Field(False, description="Always False for successful requests")
    message: str = Field(..., description="Result message")
    body: QuestionResponseBody = Field(..., description="Questions and prefilled data")


# ============================================================================
# Draft Generation
# ============================================================================

class GenerateDraftRequest(BaseModel):
    """Request for generating a draft document."""
    
    template_id: str = Field(..., min_length=1, description="Template identifier")
    answers: Dict[str, Any] = Field(..., description="Variable key-value pairs for filling the template")
    user_query: Optional[str] = Field("", description="Original user query (for record keeping)")
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v.strip():
            raise ValueError('template_id cannot be empty or whitespace only')
        return v.strip()
    
    @validator('answers')
    def validate_answers(cls, v):
        if not isinstance(v, dict):
            raise ValueError('answers must be a dictionary')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "answers": {
                    "tenant_name": "John Doe",
                    "landlord_name": "Jane Smith",
                    "property_address": "123 Main St, Los Angeles, CA 90001",
                    "monthly_rent": "$2500",
                    "lease_start_date": "2024-01-01"
                },
                "user_query": "Lease for John Doe"
            }
        }


class GenerateDraftResponseBody(BaseModel):
    """Response body for draft generation."""
    
    draft_md: str = Field(..., description="Generated draft document in Markdown format")
    instance_id: int = Field(..., description="Database ID of the saved draft instance")
    template_id: str = Field(..., description="Template identifier used")
    template_title: str = Field(..., description="Template title")
    missing_variables: List[str] = Field(default_factory=list, description="List of variables that were not provided")
    has_missing_variables: bool = Field(..., description="Whether there are missing variables")
    
    class Config:
        json_schema_extra = {
            "example": {
                "draft_md": "# Lease Agreement\n\nThis agreement is made between Jane Smith (Landlord) and John Doe (Tenant)...",
                "instance_id": 456,
                "template_id": "550e8400-e29b-41d4-a716-446655440000",
                "template_title": "California Residential Lease",
                "missing_variables": [],
                "has_missing_variables": False
            }
        }


class GenerateDraftResponse(BaseModel):
    """Complete draft generation response."""
    
    error: bool = Field(False, description="Always False for successful requests")
    message: str = Field(..., description="Generation result message")
    body: GenerateDraftResponseBody = Field(..., description="Generated draft data")

