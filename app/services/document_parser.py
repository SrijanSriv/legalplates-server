import os
import pdfplumber
from fastapi import UploadFile, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DocumentParser:
    def __init__(self):
        self.max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "10000"))
        self.supported_mime_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    
    def extract_text_from_document(self, file: UploadFile) -> str:
        """
        Extract text content from a PDF or DOCX file.
        
        Args:
            file: UploadFile object containing the document
            
        Returns:
            str: Extracted text content from all pages
            
        Raises:
            HTTPException: If file is invalid or extraction fails
        """
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="Invalid file: filename is missing")
        
        # Check file extension
        file_extension = None
        if '.' in file.filename:
            file_extension = '.' + file.filename.split('.')[-1].lower()
        
        if file_extension not in ['.pdf', '.docx']:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Only PDF and DOCX files are supported. Received: {file_extension or 'unknown format'}"
            )
        
        # Route to appropriate extraction method
        if file_extension == '.pdf':
            return self._extract_text_from_pdf(file)
        elif file_extension == '.docx':
            return self._extract_text_from_docx(file)
    
    def _extract_text_from_pdf(self, file: UploadFile) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            file: UploadFile object containing the PDF
            
        Returns:
            str: Extracted text content from all pages
            
        Raises:
            HTTPException: If file is invalid or extraction fails
        """
        
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
    
    def _extract_text_from_docx(self, file: UploadFile) -> str:
        """
        Extract text content from a DOCX file.
        
        Args:
            file: UploadFile object containing the DOCX
            
        Returns:
            str: Extracted text content from the document
            
        Raises:
            HTTPException: If file is invalid or extraction fails
        """
        try:
            from docx import Document as DocxDocument
            
            # Reset file pointer to beginning
            file.file.seek(0)
            
            # Load DOCX document
            doc = DocxDocument(file.file)
            
            # Extract text from all paragraphs
            extracted_text = ""
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    extracted_text += paragraph.text + "\n"
            
            if not extracted_text.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="No text could be extracted from the DOCX file. The file may be empty or corrupted."
                )
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from DOCX: {file.filename}")
            return extracted_text.strip()
            
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="DOCX processing requires python-docx package. Please install it: pip install python-docx"
            )
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error while processing DOCX {file.filename}: {e}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to process DOCX file: {str(e)}"
            )