import os
import pdfplumber
from fastapi import UploadFile, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DocumentParser:
    def __init__(self):
        self.max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "10000"))
        self.supported_mime_types = ["application/pdf"]
    
    def extract_text_from_pdf(self, file: UploadFile) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            file: UploadFile object containing the PDF
            
        Returns:
            str: Extracted text content from all pages
            
        Raises:
            HTTPException: If file is invalid or extraction fails
        """
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid file: filename is missing")
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Only PDF files are supported. Received: {file.filename}"
            )
        
        try:
            extracted_text = ""
            with pdfplumber.open(file.file) as pdf:
                if len(pdf.pages) == 0:
                    raise HTTPException(status_code=400, detail="PDF file contains no pages")
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                        else:
                            logger.warning(f"Page {page_num} contained no extractable text")
                    except Exception as e:
                        logger.error(f"Error extracting text from page {page_num}: {e}")
                        # Continue with other pages
                        continue
            
            if not extracted_text.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="No text could be extracted from the PDF. The file may be image-based or corrupted."
                )
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF: {file.filename}")
            return extracted_text.strip()
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error while processing PDF {file.filename}: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to process PDF file: {str(e)}"
            )