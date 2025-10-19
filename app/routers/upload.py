from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.document import Document
from app.services.document_processor import DocumentProcessor
import mimetypes

router = APIRouter(prefix="/api/v1/upload")

processor = DocumentProcessor()

@router.post("")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload and process a document (PDF or DOCX)
    Extracts raw content and stores in database
    """
    # Validate file type
    file_name = file.filename
    file_mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]
    
    if file_mime_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Please upload PDF or DOCX files."
        )
    
    # Read file content
    file_content = await file.read()
    
    # Save temporarily for processing
    temp_file_path = processor.save_temp_file(file_content, file_name)
    
    try:
        # Extract content
        extraction_result = processor.extract_content(temp_file_path)
        
        if not extraction_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document: {extraction_result.get('error')}"
            )
        
        # Store in database
        document = Document(
            filename=file_name,
            mime_type=file_mime_type,
            raw_text=extraction_result["raw_text"],
            embedding=None  # Will be generated later
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "success": True,
            "message": "File uploaded and processed successfully",
            "document": document.to_dict(),
            "extraction_metadata": extraction_result["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Cleanup temp file
        processor.cleanup_temp_file(temp_file_path)