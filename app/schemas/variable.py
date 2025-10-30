"""
Schemas for template variables.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class VariableSchema(BaseModel):
    """Schema for a template variable definition."""
    
    key: str = Field(..., description="Variable key (snake_case identifier)")
    label: str = Field(..., description="Human-readable label for the variable")
    description: Optional[str] = Field(None, description="Detailed description of what this variable represents")
    example: Optional[str] = Field(None, description="Example value for this variable")
    required: bool = Field(False, description="Whether this variable is required")
    dtype: str = Field("string", description="Data type (string, date, number, currency, address, email, phone)")
    regex: Optional[str] = Field(None, description="Optional regex pattern for validation")
    enum_values: Optional[List[str]] = Field(None, description="List of allowed values (for enum types)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "key": "tenant_name",
                "label": "Tenant Full Name",
                "description": "The full legal name of the tenant",
                "example": "John Doe",
                "required": True,
                "dtype": "string",
                "regex": None,
                "enum_values": None
            }
        }

