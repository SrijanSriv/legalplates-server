"""
Pydantic schemas for request/response validation.
"""

from app.schemas.common import (
    APIResponse,
    ErrorResponse,
    SuccessResponse,
)

from app.schemas.upload import (
    UploadResponse,
    UploadResponseBody,
)

from app.schemas.template import (
    TemplateResponse,
    TemplateListResponse,
    TemplateListResponseBody,
    TemplateDeleteResponse,
)

from app.schemas.draft import (
    TemplateMatchRequest,
    TemplateMatchResponse,
    TemplateMatchResponseBody,
    TemplateMatch,
    QuestionRequest,
    QuestionResponse,
    QuestionResponseBody,
    Question,
    GenerateDraftRequest,
    GenerateDraftResponse,
    GenerateDraftResponseBody,
)

from app.schemas.variable import (
    VariableSchema,
)

__all__ = [
    # Common
    "APIResponse",
    "ErrorResponse",
    "SuccessResponse",
    # Upload
    "UploadResponse",
    "UploadResponseBody",
    # Template
    "TemplateResponse",
    "TemplateListResponse",
    "TemplateListResponseBody",
    "TemplateDeleteResponse",
    # Draft
    "TemplateMatchRequest",
    "TemplateMatchResponse",
    "TemplateMatchResponseBody",
    "TemplateMatch",
    "QuestionRequest",
    "QuestionResponse",
    "QuestionResponseBody",
    "Question",
    "GenerateDraftRequest",
    "GenerateDraftResponse",
    "GenerateDraftResponseBody",
    # Variable
    "VariableSchema",
]

