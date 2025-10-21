from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.base import get_db
from app.models.document import Document
import mimetypes
import logging
from app.services.document_parser import DocumentParser
from app.services.template_generator import TemplateGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload")

@router.post("")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a PDF document, extract text, generate a template, and save both to database.
    
    Args:
        file: PDF file to upload
        db: Database session
        
    Returns:
        Dictionary with upload results including template and questions
        
    Raises:
        HTTPException: If upload or processing fails
    """
    try:
        # Validate file
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")
        
        file_name = file.filename
        logger.info(f"Processing upload for file: {file_name}")
        
        # Determine MIME type
        file_mime_type = mimetypes.guess_type(file.filename)[0]
        if not file_mime_type:
            file_mime_type = "application/octet-stream"
        
        # Extract text from PDF
        try:
            document_parser = DocumentParser()
            extracted_file_content = document_parser.extract_text_from_pdf(file)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to extract text from PDF: {str(e)}"
            )
        
        # Save document to database
        try:
            document = Document(
                filename=file_name, 
                mime_type=file_mime_type, 
                raw_text=extracted_file_content, 
                embedding=None
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
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating template: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate template: {str(e)}"
            )
        
        logger.info(f"Successfully processed upload for file: {file_name}")
        return {
            "message": "File uploaded successfully",
            "document_id": document.id,
            "document_name": document.filename,
            "template": template.to_dict(),
            "questions": questions
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )