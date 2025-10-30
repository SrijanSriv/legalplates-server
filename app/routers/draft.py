from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.db.base import get_db
from typing import Dict, Any, Optional, Generator, AsyncGenerator
import logging
import json
import asyncio
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
    GenerateDraftResponseBody
)
from app.models.template import Template
from app.models.template_variable import TemplateVariable
from app.models.instance import Instance
from app.services.template_generator import TemplateGenerator
from app.services.gemini_service import GeminiService
from app.services.web_template_generator import WebTemplateGenerator, SEARCH_THRESHOLD

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/draft", tags=["draft"])


def _create_no_match_response(message: str) -> TemplateMatchResponse:
    """Helper to create a standardized no-match response."""
    return TemplateMatchResponse(
        error=False,
        message=message,
        body=TemplateMatchResponseBody(
            top_match=None,
            alternatives=[],
            found=False,
            message=message
        )
    )


def _create_web_template_response(web_template, web_source: Dict[str, Any], message: str) -> TemplateMatchResponse:
    """Helper to create a response for web-sourced templates."""
    return TemplateMatchResponse(
        error=False,
        message=message,
        body=TemplateMatchResponseBody(
            top_match=TemplateMatch(
                template_id=web_template.template_id,
                title=web_template.title,
                confidence=0.85,
                explanation=f"Generated from web source: {web_source.get('url', 'unknown')}",
                doc_type=web_template.doc_type,
                jurisdiction=web_template.jurisdiction,
                semantic_similarity=None,
                source="web",
                web_url=web_source.get('url')
            ),
            alternatives=[],
            found=True,
            message="Template created from web source"
        )
    )


def _get_semantic_similarity(template_id: str, templates_data: list) -> float:
    """Get semantic similarity score for a template from the data."""
    for template_data in templates_data:
        if template_data["template_id"] == template_id:
            return template_data.get("semantic_similarity", 0.0)
    return 0.0


def _try_web_fallback(user_query: str, db: Session, match_quality: float = 0.0) -> Optional[TemplateMatchResponse]:
    """Attempt web fallback and return response if successful."""
    try:
        web_generator = WebTemplateGenerator()
        web_template, web_questions, web_source = web_generator.create_template_from_web(
            user_query=user_query,
            db=db
        )
        
        logger.info(f"Successfully created template from web: {web_template.template_id}")
        
        if match_quality > 0:
            message = f"Database match quality ({match_quality:.1%}) was below threshold, found better template from web"
        else:
            message = "No suitable template found in database, created one from web sources"
            
        return _create_web_template_response(web_template, web_source, message)
        
    except HTTPException as e:
        logger.warning(f"Web fallback failed: {e.detail}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in web fallback: {e}")
        return None




@router.post("/match-stream")
async def match_template_stream(
    request: TemplateMatchRequest,
    db: Session = Depends(get_db)
):
    """
    Find the best matching template with real-time status updates via Server-Sent Events (SSE).
    """
    user_query = request.user_query
    
    async def generate_updates() -> AsyncGenerator[str, None]:
        try:
            # Send initial status
            yield f"data: {json.dumps({'status': 'searching', 'message': 'Searching for matching templates...'})}\n\n"
            
            logger.info(f"Matching template for query: {user_query[:100]}...")
            
            # Initialize services
            template_service = TemplateGenerator()
            gemini = GeminiService()
            
            # Stage 1: Semantic Search
            similar_templates = template_service.find_similar_templates(
                user_query=user_query,
                db=db,
            top_k=5
        )
        
            if not similar_templates:
                logger.info("No templates with embeddings found in database - falling back to web search")
                
                # FALLBACK: Search web for templates when database is empty
                yield f"data: {json.dumps({'status': 'searching_web', 'message': 'No templates in database, searching the web for legal templates...'})}\n\n"
                
                try:
                    web_generator = WebTemplateGenerator()
                    
                    # Step 1: Search web for templates
                    yield f"data: {json.dumps({'status': 'fetching_content', 'message': 'Fetching document content from web...'})}\n\n"
                    
                    # Step 2: Generate template
                    yield f"data: {json.dumps({'status': 'generating_template', 'message': 'Generating template from web content...'})}\n\n"
                    
                    web_template, web_questions, web_source = web_generator.create_template_from_web(
                        user_query=user_query,
                        db=db
                    )
                    
                    # Step 3: Create variables
                    yield f"data: {json.dumps({'status': 'creating_variables', 'message': 'Creating variables and questions...'})}\n\n"
                    
                    # Step 4: Finalizing
                    yield f"data: {json.dumps({'status': 'finalizing', 'message': 'Finalizing template...'})}\n\n"
                    
                    logger.info(f"Successfully created template from web: {web_template.template_id}")
                    
                    message = "No templates found in database, created one from web sources"
                    web_response = _create_web_template_response(web_template, web_source, message)
                    
                    result = {
                        "status": "success",
                        "message": "Template created from web source",
                        "data": {
                            "top_match": web_response.body.top_match.dict(),
                "alternatives": [],
                            "found": True
                        }
                    }
                    yield f"data: {json.dumps(result)}\n\n"
                    return
                    
                except HTTPException as e:
                    logger.warning(f"Web fallback failed: {e.detail}")
                    yield f"data: {json.dumps({'status': 'error', 'message': f'Web search failed: {e.detail}'})}\n\n"
                    return
                except Exception as e:
                    logger.error(f"Unexpected error in web fallback: {e}")
                    yield f"data: {json.dumps({'status': 'error', 'message': 'An unexpected error occurred during web search'})}\n\n"
                    return
            
            logger.info(f"Semantic search returned {len(similar_templates)} candidates")
            
            # Stage 2: Prepare candidates for Gemini re-ranking
            templates_data = [
                {
                "template_id": template.template_id,
                "title": template.title,
                "file_description": template.file_description,
                "doc_type": template.doc_type,
                "jurisdiction": template.jurisdiction,
                    "similarity_tags": template.similarity_tags or [],
                    "semantic_similarity": round(similarity_score, 3)
                }
                for template, similarity_score in similar_templates
            ]
            
            # Stage 3: Use Gemini to re-rank and explain
            classification = gemini.find_matching_template(user_query, templates_data)
            
            if not classification.get("found") or not classification.get("top_match"):
                logger.info("No suitable template match found in database")
                
                # FALLBACK: Search web for templates
                yield f"data: {json.dumps({'status': 'searching_web', 'message': 'Searching the web for legal templates...'})}\n\n"
                
                try:
                    web_generator = WebTemplateGenerator()
                    
                    # Step 1: Search web for templates
                    yield f"data: {json.dumps({'status': 'fetching_content', 'message': 'Fetching document content from web...'})}\n\n"
                    
                    # Step 2: Generate template
                    yield f"data: {json.dumps({'status': 'generating_template', 'message': 'Generating template from web content...'})}\n\n"
                    
                    web_template, web_questions, web_source = web_generator.create_template_from_web(
                        user_query=user_query,
                        db=db
                    )
                    
                    # Step 3: Create variables
                    yield f"data: {json.dumps({'status': 'creating_variables', 'message': 'Creating variables and questions...'})}\n\n"
                    
                    # Step 4: Finalizing
                    yield f"data: {json.dumps({'status': 'finalizing', 'message': 'Finalizing template...'})}\n\n"
                    
                    logger.info(f"Successfully created template from web: {web_template.template_id}")
                    
                    message = "No suitable template found in database, created one from web sources"
                    web_response = _create_web_template_response(web_template, web_source, message)
                    
                    result = {
                        "status": "success",
                        "message": "Template created from web source",
                        "data": {
                            "top_match": web_response.body.top_match.dict(),
                "alternatives": [],
                            "found": True
                        }
                    }
                    yield f"data: {json.dumps(result)}\n\n"
                    return
                    
                except HTTPException as e:
                    logger.warning(f"Web fallback failed: {e.detail}")
                    yield f"data: {json.dumps({'status': 'error', 'message': f'Web search failed: {e.detail}'})}\n\n"
                    return
                except Exception as e:
                    logger.error(f"Unexpected error in web fallback: {e}")
                    yield f"data: {json.dumps({'status': 'error', 'message': 'An unexpected error occurred during web search'})}\n\n"
                    return
            
            # Found a good match in database
            top_match_data = classification["top_match"]
            alternatives_data = classification.get("alternatives", [])
            
            # Check if match quality is below threshold
            confidence = top_match_data.get("confidence", 0.0)
            best_semantic_similarity = _get_semantic_similarity(top_match_data["template_id"], templates_data)
            match_quality = max(confidence, best_semantic_similarity)
            
            if match_quality < SEARCH_THRESHOLD:
                logger.warning(f"Match quality ({match_quality:.1%}) below threshold ({SEARCH_THRESHOLD:.1%})")
                
                # FALLBACK: Try web search for better template
                yield f"data: {json.dumps({'status': 'searching_web', 'message': 'Searching the web for better templates...'})}\n\n"
                
                try:
                    web_generator = WebTemplateGenerator()
                    
                    # Step 1: Search web for templates
                    yield f"data: {json.dumps({'status': 'fetching_content', 'message': 'Fetching document content from web...'})}\n\n"
                    
                    # Step 2: Generate template
                    yield f"data: {json.dumps({'status': 'generating_template', 'message': 'Generating template from web content...'})}\n\n"
                    
                    web_template, web_questions, web_source = web_generator.create_template_from_web(
                        user_query=user_query,
                        db=db
                    )
                    
                    # Step 3: Create variables
                    yield f"data: {json.dumps({'status': 'creating_variables', 'message': 'Creating variables and questions...'})}\n\n"
                    
                    # Step 4: Finalizing
                    yield f"data: {json.dumps({'status': 'finalizing', 'message': 'Finalizing template...'})}\n\n"
                    
                    logger.info(f"Successfully created template from web: {web_template.template_id}")
                    
                    message = f"Database match quality ({match_quality:.1%}) was below threshold, found better template from web"
                    web_response = _create_web_template_response(web_template, web_source, message)
                    
                    result = {
                        "status": "success",
                        "message": f"Found better template from web (database match was only {match_quality:.1%})",
                        "data": {
                            "top_match": web_response.body.top_match.dict(),
                "alternatives": [],
                            "found": True
                        }
                    }
                    yield f"data: {json.dumps(result)}\n\n"
                    return
                    
                except HTTPException as e:
                    logger.warning(f"Web fallback failed: {e.detail}")
                    yield f"data: {json.dumps({'status': 'error', 'message': f'Web search failed: {e.detail}'})}\n\n"
                    return
                except Exception as e:
                    logger.error(f"Unexpected error in web fallback: {e}")
                    yield f"data: {json.dumps({'status': 'error', 'message': 'An unexpected error occurred during web search'})}\n\n"
                    return
            
            # Send success with database template
            result = {
                "status": "success",
                "message": "Template found in database",
                "data": {
                    "top_match": {
                        "template_id": top_match_data["template_id"],
                        "title": top_match_data.get("title", "Untitled Template"),
                        "confidence": confidence,
                        "explanation": top_match_data.get("explanation", ""),
                        "doc_type": top_match_data.get("doc_type"),
                        "jurisdiction": top_match_data.get("jurisdiction"),
                        "semantic_similarity": best_semantic_similarity,
                        "source": "database",
                        "web_url": None
                    },
                    "alternatives": [
                        {
                            "template_id": alt_data["template_id"],
                            "title": alt_data.get("title", "Untitled Template"),
                            "confidence": alt_data["confidence"],
                            "explanation": alt_data["explanation"],
                            "doc_type": alt_data.get("doc_type"),
                            "jurisdiction": alt_data.get("jurisdiction"),
                            "semantic_similarity": alt_data.get("semantic_similarity"),
                            "source": "database",
                            "web_url": None
                        }
                        for alt_data in alternatives_data
                    ],
                    "found": True
                }
            }
            yield f"data: {json.dumps(result)}\n\n"
                
        except Exception as e:
            logger.error(f"Unexpected error in match_template_stream: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': 'An unexpected error occurred'})}\n\n"
    
    return StreamingResponse(
        generate_updates(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )


def _get_template_by_id(template_id: str, db: Session) -> Template:
    """Get template by ID with proper error handling."""
    template = db.query(Template).filter(Template.template_id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

        
def _get_template_variables(template_id: str, db: Session) -> list:
    """Get template variables with proper error handling."""
    template = _get_template_by_id(template_id, db)
    variables = db.query(TemplateVariable).filter(
        TemplateVariable.template_id == template.id
    ).all()
    return variables, template


def _parse_question_from_variable(var: TemplateVariable) -> dict:
    """Parse question from variable with fallback handling."""
    if var.question:
        try:
            import json
            question_data = json.loads(var.question)
            return {
                "key": var.key,
                "question": question_data.get("question", f"What is the {var.label}?"),
                "description": var.description,
                "example": var.example,
                "required": var.required,
                "dtype": var.dtype,
                "regex": var.regex,
                "enum_values": var.enum_values
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in question for variable {var.key}: {e}")
    
    # Fallback to basic question
    return {
        "key": var.key,
        "question": f"What is the {var.label}?",
        "description": var.description,
        "example": var.example,
        "required": var.required,
        "dtype": var.dtype,
        "regex": var.regex,
        "enum_values": var.enum_values
    }


@router.post("/questions", response_model=QuestionResponse)
async def generate_questions(
    request: QuestionRequest,
    db: Session = Depends(get_db)
):
    """
    Generate human-friendly questions for template variables with optional prefilling.
    """
    template_id = request.template_id
    user_query = request.user_query or ""
    
    logger.info(f"Generating questions for template: {template_id}")
    
    try:
        # Get template and variables
        variables, template = _get_template_variables(template_id, db)
        
        if not variables:
            logger.info(f"No variables found for template {template_id}")
            return QuestionResponse(
                error=False,
                message="No variables defined for this template",
                body=QuestionResponseBody(
                    questions=[],
                    prefilled={},
                    template_id=template_id,
                    template_title=template.title,
                    message="No variables defined for this template"
                )
            )
        
        logger.info(f"Found {len(variables)} variables for template")
        
        # Parse questions from database
        questions = [_parse_question_from_variable(var) for var in variables]
        logger.info(f"Retrieved {len(questions)} questions from database")
        
        # Try to prefill from user query if provided
        prefilled = {}
        if user_query:
            try:
                logger.info(f"Attempting to prefill variables from query")
                gemini = GeminiService()
                variables_dict = [v.to_dict() for v in variables]
                prefilled = gemini.prefill_variables_from_query(user_query, variables_dict)
                logger.info(f"Prefilled {len(prefilled)} variables")
            except Exception as e:
                logger.warning(f"Error prefilling variables (continuing without prefill): {e}")
                prefilled = {}
        
        return QuestionResponse(
            error=False,
            message=f"Retrieved {len(questions)} questions successfully",
            body=QuestionResponseBody(
                questions=[Question(**q) for q in questions],
                prefilled=prefilled,
                template_id=template_id,
                template_title=template.title,
                message=None
            )
        )
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while fetching template/variables: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve template data")
    except Exception as e:
        logger.error(f"Unexpected error generating questions: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/generate", response_model=GenerateDraftResponse)
async def generate_draft(
    request: GenerateDraftRequest,
    db: Session = Depends(get_db)
):
    """
    Generate final draft document from template by filling in variable answers.
    """
    template_id = request.template_id
    answers = request.answers
    user_query = request.user_query
    
    logger.info(f"Generating draft for template: {template_id}")
    
    try:
        # Get template
        template = _get_template_by_id(template_id, db)
        
        # Render draft by replacing placeholders with answers
        template_service = TemplateGenerator()
        draft_md = template_service.render_draft(template, answers)
        logger.info(f"Successfully rendered draft ({len(draft_md)} chars)")
        
        # Check for missing variables
        missing = template_service.get_missing_variables(template, answers)
        if missing:
            logger.warning(f"Draft has {len(missing)} missing variables: {missing}")
        
        # Create instance record to save the generated draft
        instance = Instance(
            template_id=template.id,
            user_query=user_query,
            answers_json=answers,
            draft_md=draft_md
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)
        logger.info(f"Successfully created instance {instance.id} for template {template_id}")
        
        return GenerateDraftResponse(
            error=False,
            message="Draft generated successfully",
            body=GenerateDraftResponseBody(
                draft_md=draft_md,
                instance_id=instance.id,
                template_id=template.template_id,
                template_title=template.title,
                missing_variables=missing,
                has_missing_variables=len(missing) > 0
            )
        )
    
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error while generating draft: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.error(f"Unexpected error generating draft: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")