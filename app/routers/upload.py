from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.base import get_db
from app.models.document import Document
from app.schemas.upload import (
    UploadResponse, 
    UploadResponseBody, 
    DuplicateTemplateResponseBody,
    DuplicateTemplateInfo
)
import mimetypes
import logging
from app.services.document_parser import DocumentParser
from app.services.template_generator import TemplateGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a PDF document, extract text, generate a template, and save both to database.
    
    Args:
        file: PDF file to upload
        db: Database session
        
    Returns:
        UploadResponse with template and questions
        
    Raises:
        HTTPException: If upload or processing fails
    """
    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")
    
    allowed_extensions = {'.pdf', '.docx'}
    file_extension = None
    if '.' in file.filename:
        file_extension = '.' + file.filename.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Only PDF and DOCX files are supported. Received: {file_extension or 'unknown format'}"
        )
    
    try:
        
        file_name = file.filename
        logger.info(f"Processing upload for file: {file_name}")
        
        # Determine MIME type
        file_mime_type = mimetypes.guess_type(file.filename)[0]
        if not file_mime_type:
            file_mime_type = "application/octet-stream"
        
        # Extract text from document (PDF or DOCX)
        try:
            document_parser = DocumentParser()
            extracted_file_content = document_parser.extract_text_from_document(file)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from document: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract text from document: {str(e)}"
            )
        
        # Save document to database
        try:
            document = Document(
                filename=file_name, 
                mime_type=file_mime_type, 
                raw_text=extracted_file_content
            )
            db.add(document)
            db.commit()
            db.refresh(document)
            logger.info(f"Saved document to database with ID: {document.id}")
        except SQLAlchemyError as e:
            logger.error(f"Database error while saving document: {e}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save document to database: {str(e)}"
            )
        
        # Generate template from document
        try:
            template_generator = TemplateGenerator()
            template, questions = template_generator.generate_template(
                file_name=file_name, 
                document_raw_text=extracted_file_content, 
                db=db
            )
            
            logger.info(f"Successfully processed template: {template.title}")
            
        except HTTPException as http_exc:
            # Handle any remaining HTTP exceptions (shouldn't happen with new approach)
            logger.error(f"HTTP error in template generation: {http_exc}")
            raise
        except Exception as e:
            logger.error(f"Error generating template: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate template: {str(e)}"
            )
        
        logger.info(f"Successfully processed upload for file: {file_name}")
        
        return UploadResponse(
            error=False,
            message="File uploaded successfully",
            body=UploadResponseBody(
                document_id=document.id,
                document_name=document.filename,
                template=template.to_dict(),
                questions=questions
            )
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (handled by global exception handler)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )