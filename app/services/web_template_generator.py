"""
Service for generating templates from web-sourced documents.
"""
import logging
from typing import Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.services.exa_service import ExaService
from app.services.gemini_service import GeminiService
from app.services.template_generator import TemplateGenerator
from app.models.template import Template

logger = logging.getLogger(__name__)


SEARCH_THRESHOLD = 0.75  # 75% similarity


class WebTemplateGenerator:
    """Service for creating templates from web sources when local templates aren't good enough."""
    
    def __init__(self):
        self.exa_service = ExaService()
        self.gemini_service = GeminiService()
        self.template_generator = TemplateGenerator()
        logger.info("WebTemplateGenerator initialized")
    
    def is_match_good_enough(self, similarity_score: float) -> bool:
        """
        Determine if a template match is "good enough" to use.
        
        Args:
            similarity_score: Cosine similarity score (0-1)
            
        Returns:
            True if match is good enough, False if we should search web
        """
        is_good = similarity_score >= SEARCH_THRESHOLD
        logger.info(f"Match quality check: {similarity_score:.1%} - {'GOOD ENOUGH' if is_good else 'NOT GOOD ENOUGH, will search web'}")
        return is_good
    
    def create_template_from_web(
        self,
        user_query: str,
        db: Session
    ) -> Tuple[Template, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Search web for a template, fetch it, and convert to our template format.
        
        Args:
            user_query: User's search query
            db: Database session
            
        Returns:
            Tuple of (Template, questions, web_source_info)
            
        Raises:
            HTTPException: If web search or template creation fails
        """
        if not self.exa_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="Web search service is not available. Please configure EXA_API_KEY."
            )
        
        try:
            logger.info(f"Searching web for template matching: {user_query}")
            
            # Search web for best template
            web_result = self.exa_service.get_best_template_from_web(
                user_query=user_query,
                max_results=3
            )
            
            if not web_result:
                raise HTTPException(
                    status_code=404,
                    detail="No suitable templates found on the web for your query"
                )
            
            logger.info(f"Found web template from: {web_result['url']}")
            
            # Extract template title and content
            title = web_result.get("title", "Web Template")
            content = web_result.get("content", "")
            
            if not content or len(content.strip()) < 100:
                raise HTTPException(
                    status_code=400,
                    detail="Web template content is too short or empty"
                )
            
            # Generate template from web content using existing flow
            logger.info("Converting web content to template")
            template, questions = self.template_generator.generate_template(
                file_name=title,
                document_raw_text=content,
                db=db
            )
            
            # Add metadata about web source
            web_source_info = {
                "source": "web",
                "url": web_result.get("url"),
                "original_title": web_result.get("title"),
                "search_score": web_result.get("score")
            }
            
            logger.info(f"Successfully created template from web source: {template.template_id}")
            return template, questions, web_source_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating template from web: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create template from web: {str(e)}"
            )
    
    def _generate_template_from_query(self, user_query: str, db: Session) -> Tuple[Template, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Generate a legal template directly from user query when web search fails.
        
        Args:
            user_query: User's search query
            db: Database session
            
        Returns:
            Tuple of (Template, questions, source_info)
        """
        try:
            logger.info(f"Generating legal template from query: {user_query}")
            
            # Use Gemini to generate a legal template from the query
            legal_template_text = self.gemini.generate_legal_template_from_business_need(
                business_description=user_query,
                suggested_template_type="Legal Document",  # Generic type
                jurisdiction="US"  # Default jurisdiction
            )
            
            # Generate template from the legal text
            template, questions = self.template_generator.generate_template(
                file_name=f"generated_template_{user_query[:30]}",
                document_raw_text=legal_template_text,
                db=db
            )
            
            source_info = {
                "source": "ai_generated",
                "url": None,
                "original_title": f"Generated template for: {user_query}",
                "search_score": None
            }
            
            logger.info(f"Successfully generated template from query: {template.template_id}")
            return template, questions, source_info
            
        except Exception as e:
            logger.error(f"Error generating template from query: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate template from query: {str(e)}"
            )

