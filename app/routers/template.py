from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
from app.db.base import get_db
from app.models.template import Template
from app.models.template_variable import TemplateVariable
from app.services.template_generator import TemplateGenerator
from app.schemas.template import (
    TemplateListResponse,
    TemplateListResponseBody,
    TemplateListItem,
    TemplateResponse,
    TemplateDetail,
    TemplateDeleteResponse,
    TemplateDeleteResponseBody
)
from app.schemas.common import PaginationMeta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/template", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all templates with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        
    Returns:
        TemplateListResponse with templates and pagination metadata
        
    Raises:
        HTTPException: If database query fails
    """
    # Validate pagination parameters
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip parameter must be >= 0")
    
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=400, 
            detail="limit parameter must be between 1 and 1000"
        )
    
    try:
        logger.info(f"Fetching templates: skip={skip}, limit={limit}")
        
        # Query templates with pagination
        templates = db.query(Template).offset(skip).limit(limit).all()
        total = db.query(Template).count()
        
        # Get variables for each template
        template_responses = []
        for template in templates:
            try:
                variables = db.query(TemplateVariable).filter(
                    TemplateVariable.template_id == template.id
                ).all()
                
                template_dict = template.to_dict()
                template_dict["variables"] = [v.to_dict() for v in variables]
                template_responses.append(template_dict)
            except Exception as e:
                logger.error(f"Error processing template {template.id}: {e}")
                # Continue processing other templates
                continue
        
        logger.info(f"Successfully fetched {len(template_responses)} templates (total: {total})")
        
        return TemplateListResponse(
            error=False,
            message=f"Retrieved {len(template_responses)} templates",
            body=TemplateListResponseBody(
                templates=template_responses,
                pagination=PaginationMeta(
                    total=total,
                    skip=skip,
                    limit=limit,
                    returned=len(template_responses)
                )
            )
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Database error while listing templates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve templates from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error while listing templates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific template by ID with its variables.
    
    Args:
        template_id: Unique template identifier (UUID)
        db: Database session
        
    Returns:
        TemplateResponse with complete template data
        
    Raises:
        HTTPException: If template not found or database error occurs
    """
    # Validate template_id
    if not template_id or not template_id.strip():
        raise HTTPException(status_code=400, detail="template_id cannot be empty")
    
    try:
        logger.info(f"Fetching template: {template_id}")
        
        # Query template
        template = db.query(Template).filter(
            Template.template_id == template_id
        ).first()
        
        if not template:
            logger.warning(f"Template not found: {template_id}")
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Get variables for this template
        variables = db.query(TemplateVariable).filter(
            TemplateVariable.template_id == template.id
        ).all()
        
        template_dict = template.to_dict()
        template_dict["variables"] = [v.to_dict() for v in variables]
        
        logger.info(f"Successfully retrieved template {template_id} with {len(variables)} variables")
        
        return TemplateResponse(
            error=False,
            message="Template retrieved successfully",
            body=TemplateDetail(**template_dict)
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching template {template_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve template from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching template {template_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.delete("/{template_id}", response_model=TemplateDeleteResponse)
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a template and its associated variables.
    
    Args:
        template_id: Unique template identifier (UUID)
        db: Database session
        
    Returns:
        TemplateDeleteResponse with deletion confirmation
        
    Raises:
        HTTPException: If template not found or deletion fails
    """
    # Validate template_id
    if not template_id or not template_id.strip():
        raise HTTPException(status_code=400, detail="template_id cannot be empty")
    
    try:
        logger.info(f"Attempting to delete template: {template_id}")
        
        # Find template
        template = db.query(Template).filter(
            Template.template_id == template_id
        ).first()
        
        if not template:
            logger.warning(f"Template not found for deletion: {template_id}")
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Delete associated variables (if not cascading)
        variables_count = db.query(TemplateVariable).filter(
            TemplateVariable.template_id == template.id
        ).count()
        
        logger.info(f"Deleting template {template_id} with {variables_count} variables")
        
        # Delete template (cascade should handle variables)
        db.delete(template)
        db.commit()
        
        logger.info(f"Successfully deleted template: {template_id}")
        
        return TemplateDeleteResponse(
            error=False,
            message="Template deleted successfully",
            body=TemplateDeleteResponseBody(
                template_id=template_id,
                success=True
            )
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        db.rollback()
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while deleting template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete template from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error while deleting template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{template_id}/download")
async def download_template_markdown(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    Download template as Markdown file with YAML front-matter.
    
    Args:
        template_id: Unique template identifier (UUID)
        db: Database session
        
    Returns:
        Markdown file as downloadable response
        
    Raises:
        HTTPException: If template not found or generation fails
    """
    # Validate template_id
    if not template_id or not template_id.strip():
        raise HTTPException(status_code=400, detail="template_id cannot be empty")
    
    try:
        logger.info(f"Generating markdown download for template: {template_id}")
        
        # Find template
        template = db.query(Template).filter(
            Template.template_id == template_id
        ).first()
        
        if not template:
            logger.warning(f"Template not found for download: {template_id}")
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Get variables
        variables = db.query(TemplateVariable).filter(
            TemplateVariable.template_id == template.id
        ).all()
        
        logger.info(f"Generating markdown with {len(variables)} variables")
        
        # Generate markdown with front-matter
        try:
            template_service = TemplateGenerator()
            markdown = template_service.generate_markdown_with_frontmatter(template, variables)
        except Exception as e:
            logger.error(f"Error generating markdown for template {template_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate markdown: {str(e)}"
            )
        
        # Create safe filename
        safe_filename = template.title.replace(" ", "_") if template.title else template_id
        safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")
        
        logger.info(f"Successfully generated markdown for template: {template_id}")
        
        from fastapi.responses import Response
        return Response(
            content=markdown,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={safe_filename}.md"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching template {template_id} for download: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve template from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error while downloading template {template_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

