"""
Common schemas used across the API.
"""

from pydantic import BaseModel, Field
from typing import Any, Optional, Generic, TypeVar, Literal

# Generic type for response body
T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response format.
    
    All API responses follow this structure:
    - error: Boolean indicating if an error occurred
    - message: Human-readable message describing the result
    - body: The actual response data (can be any type)
    """
    error: bool = Field(..., description="True if an error occurred, False otherwise")
    message: str = Field(..., description="Human-readable message describing the result")
    body: Optional[T] = Field(None, description="Response data payload")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "error": False,
                    "message": "Operation completed successfully",
                    "body": {"key": "value"}
                },
                {
                    "error": True,
                    "message": "An error occurred",
                    "body": None
                }
            ]
        }


class SuccessResponse(APIResponse[T]):
    """Success response with data."""
    error: Literal[False] = Field(default=False)


class ErrorResponse(APIResponse[None]):
    """Error response without body."""
    error: Literal[True] = Field(default=True)
    body: Literal[None] = Field(default=None)


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    returned: int = Field(..., description="Actual number of items returned")

