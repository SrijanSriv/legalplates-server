from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.services.gemini_service import GeminiService
from typing import List, Dict, Any, Tuple
from app.models.template import Template
from fastapi import HTTPException
import uuid
import logging

logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self):
        try:
            self.gemini = GeminiService()
        except Exception as e:
            logger.error(f"Failed to initialize GeminiService: {e}")
            raise ValueError(f"Failed to initialize template generator: {str(e)}")
    
    def generate_template(
        self, 
        file_name: str, 
        document_raw_text: str, 
        db: Session
    ) -> Tuple[Template, List[Dict[str, Any]]]:
        """
        Generate a template from document text using AI, and save it to the database.
        
        Args:
            file_name: Name of the source document file
            document_raw_text: Extracted text content from the document
            db: Database session for persisting the template
            
        Returns:
            Tuple containing the saved Template record and generated questions
            
        Raises:
            HTTPException: If template generation or database operation fails
        """
        if not file_name:
            raise HTTPException(status_code=400, detail="file_name is required")
        
        if not document_raw_text or len(document_raw_text.strip()) == 0:
            raise HTTPException(
                status_code=400, 
                detail="document_raw_text cannot be empty"
            )
        
        if len(document_raw_text) > 1_000_000:  # 1MB limit
            raise HTTPException(
                status_code=400,
                detail="Document text is too large (max 1MB)"
            )
        
        try:
            # Extract variables and metadata from document using Gemini
            logger.info(f"Extracting variables from document: {file_name}")
            result = self.gemini.extract_variables_from_chunk(document_raw_text)
            
            if not result:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to extract variables from document"
                )
            
            variables = result.get("variables", [])
            similarity_tags = result.get("similarity_tags", [])
            doc_type = result.get("doc_type")
            jurisdiction = result.get("jurisdiction")
            file_description = result.get("file_description")
            
            logger.info(f"Extracted {len(variables)} variables from document")
            
            # Generate template by replacing values with placeholders
            logger.info("Generating template text with placeholders")
            template_text = self.gemini.generate_template_from_text(document_raw_text, variables)
            
            if not template_text:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate template text"
                )
            
            # Generate user-friendly questions from variables
            logger.info("Generating questions from variables")
            questions = self.gemini.generate_questions_from_variables(variables)
            
            # Generate unique template_id
            template_id = str(uuid.uuid4())
            
            # Save template to database
            logger.info(f"Saving template to database with ID: {template_id}")
            template_record = Template(
                template_id=template_id,
                title=file_name,
                body_md=template_text,
                similarity_tags=similarity_tags,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                file_description=file_description
            )
            
            db.add(template_record)
            db.commit()
            db.refresh(template_record)  # Refresh to get auto-generated fields
            
            logger.info(f"Successfully created template with ID: {template_id}")
            return template_record, questions
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            db.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error while saving template: {e}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save template to database: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error in template generation: {e}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate template: {str(e)}"
            )
    
    def find_matching_template(
        self, 
        user_query: str, 
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Find the best matching template for a user query.
        
        Args:
            user_query: User's document request description
            templates: List of available template dictionaries
            
        Returns:
            Dictionary with matching results
            
        Raises:
            HTTPException: If matching fails
        """
        if not user_query or not user_query.strip():
            raise HTTPException(status_code=400, detail="user_query cannot be empty")
        
        if not templates:
            return {"top_match": None, "alternatives": [], "found": False}
        
        try:
            logger.info(f"Finding matching template for query: {user_query[:100]}...")
            result = self.gemini.find_matching_template(user_query, templates)
            return result
        except Exception as e:
            logger.error(f"Error finding matching template: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to find matching template: {str(e)}"
            )
    
    def prefill_variables_from_query(
        self, 
        user_query: str, 
        variables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract variable values from user query.
        
        Args:
            user_query: User's input text
            variables: List of variable definitions
            
        Returns:
            Dictionary mapping variable keys to extracted values
            
        Raises:
            HTTPException: If prefilling fails
        """
        if not user_query or not user_query.strip():
            return {}
        
        if not variables:
            return {}
        
        try:
            logger.info("Prefilling variables from user query")
            result = self.gemini.prefill_variables_from_query(user_query, variables)
            return result
        except Exception as e:
            logger.error(f"Error prefilling variables: {e}")
            # Don't raise exception here, just return empty dict
            return {}