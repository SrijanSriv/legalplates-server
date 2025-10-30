from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.services.gemini_service import GeminiService
from app.services.embedding_service import EmbeddingService
from typing import List, Dict, Any, Tuple, Optional
from app.models.template import Template
from app.models.template_variable import TemplateVariable
from fastapi import HTTPException
import uuid
import logging
import yaml
import asyncio
import concurrent.futures

logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self):
        try:
            self.gemini = GeminiService()
            self.embedder = EmbeddingService()
            logger.info("Template generator initialized with Gemini and Embedding services")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise ValueError(f"Failed to initialize template generator: {str(e)}")
    
    def _build_yaml_frontmatter(
        self,
        template_id: str,
        template_name: str,
        variables: List[Dict[str, Any]],
        doc_type: str = None,
        jurisdiction: str = None,
        file_description: str = None,
        similarity_tags: List[str] = None
    ) -> str:
        """
        Programmatically build YAML frontmatter from structured data.
        This ensures consistent, valid YAML formatting.
        
        Args:
            template_id: Unique template identifier
            template_name: Generated template title
            variables: List of variable dictionaries
            doc_type: Document type
            jurisdiction: Legal jurisdiction
            file_description: Description of template purpose
            similarity_tags: Tags for semantic search
            
        Returns:
            YAML frontmatter string with --- delimiters
        """
        try:
            # Build frontmatter dictionary
            frontmatter_dict = {
                'template_id': template_id,
                'title': template_name,
                'file_description': file_description or 'Legal document template',
                'jurisdiction': jurisdiction or 'IN',
                'doc_type': doc_type or 'legal_document',
                'variables': []
            }
            
            # Add variables
            for var in variables:
                var_dict = {
                    'key': var.get('key'),
                    'label': var.get('label'),
                    'description': var.get('description'),
                    'example': var.get('example'),
                    'required': var.get('required', False),
                    'dtype': var.get('dtype', 'string')
                }
                if var.get('regex'):
                    var_dict['regex'] = var.get('regex')
                frontmatter_dict['variables'].append(var_dict)
            
            # Add similarity tags
            if similarity_tags:
                frontmatter_dict['similarity_tags'] = similarity_tags
            else:
                frontmatter_dict['similarity_tags'] = []
            
            # Convert to YAML string
            yaml_str = yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Wrap in delimiters
            frontmatter = f"---\n{yaml_str}---\n\n"
            
            logger.info(f"Built YAML frontmatter with {len(variables)} variables")
            return frontmatter
            
        except Exception as e:
            logger.error(f"Error building YAML frontmatter: {e}")
            raise ValueError(f"Failed to build YAML frontmatter: {str(e)}")
    
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
            # Step 1: Classify document type to ensure it's legal or can be converted
            logger.info("Classifying document type...")
            classification = self.gemini.classify_document_type(document_raw_text)
            
            if not classification.get("is_legal_document", True):
                # Document is not legal - convert to legal template
                suggested_template_type = classification.get("suggested_legal_template")
                jurisdiction = classification.get("legal_jurisdiction", "US")
                conversion_notes = classification.get("conversion_notes", "")
                
                if not suggested_template_type:
                    raise HTTPException(
                        status_code=400,
                        detail="Document is not a legal document and no suitable legal template type could be determined. Please upload a legal document or provide more context about the type of legal document needed."
                    )
                
                logger.info(f"Converting business need to legal template: {suggested_template_type}")
                
                # Generate legal template from business description
                legal_template_text = self.gemini.generate_legal_template_from_business_need(
                    business_description=document_raw_text,
                    suggested_template_type=suggested_template_type,
                    jurisdiction=jurisdiction
                )
                
                # Parse the generated legal template to extract variables
                logger.info("Extracting variables from generated legal template...")
                result = self.gemini.extract_variables_from_chunk(legal_template_text)
                
                if not result:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to extract variables from generated legal template"
                    )
                
                variables = result.get("variables", [])
                similarity_tags = result.get("similarity_tags", [])
                doc_type = suggested_template_type.lower().replace(" ", "_")
                jurisdiction = jurisdiction
                file_description = f"Generated legal template for {suggested_template_type}"
                template_name = result.get("template_name", f"{suggested_template_type} Template")
                
                # Use the generated legal template as the body
                template_body = legal_template_text
                
            else:
                # Document is already legal - proceed with OPTIMIZED processing
                logger.info("Document classified as legal document, proceeding with optimized template generation")
                
                # OPTIMIZED: Single API call for variables, template body, and questions
                logger.info(f"Starting optimized combined processing for document: {file_name}")
                result = self.gemini.extract_variables_and_generate_template_combined(document_raw_text)
                
                if not result:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to process document with combined approach"
                    )
                
                variables = result.get("variables", [])
                template_body = result.get("template_body", "")
                questions = result.get("questions", [])
                similarity_tags = result.get("similarity_tags", [])
                doc_type = result.get("doc_type")
                jurisdiction = result.get("jurisdiction")
                file_description = result.get("file_description")
                template_name = result.get("template_name")
                
                logger.info(f"Optimized processing completed: {len(variables)} variables, {len(questions)} questions")
                
                if not template_body:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to generate template body"
                    )
            
            # Generate unique template_id
            template_id = str(uuid.uuid4())
            
            # Step 2: Use template name from initial extraction (already generated)
            if not template_name:
                logger.warning("No template name generated, using filename as fallback")
                template_name = file_name
            else:
                logger.info(f"Using generated template name: '{template_name}'")
            
            # Step 3: Programmatically build YAML frontmatter from structured data
            logger.info("Building YAML frontmatter programmatically")
            yaml_frontmatter = self._build_yaml_frontmatter(
                template_id=template_id,
                template_name=template_name,
                variables=variables,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                file_description=file_description,
                similarity_tags=similarity_tags
            )
            
            # Step 4: Combine YAML frontmatter with GenAI-generated body
            template_with_frontmatter = f"{yaml_frontmatter}\n\n{template_body}"
            
            # Questions are already generated in the combined approach, no need to generate separately
            
            # OPTIMIZED: Generate embedding in parallel with database operations
            logger.info("Starting parallel embedding generation")
            embedding_future = self._generate_embedding_async(
                document_text=document_raw_text,
                file_name=file_name, 
                file_description=file_description, 
                doc_type=doc_type, 
                jurisdiction=jurisdiction, 
                similarity_tags=similarity_tags
            )
            
            # Wait for embedding generation to complete first
            logger.info("Waiting for embedding generation to complete")
            embedding = embedding_future.result()
            
            # Check for duplicate templates BEFORE saving
            if embedding:
                duplicate_check = self.check_duplicate_template(
                    embedding=embedding,
                    db=db,
                    similarity_threshold=0.90  # 90% similarity threshold
                )
                
                if duplicate_check:
                    existing_template, similarity_score = duplicate_check
                    logger.info(f"Found similar template: {existing_template.template_id} (similarity: {similarity_score:.3f})")
                    
                    # Return the existing similar template instead of creating a new one
                    logger.info(f"Returning existing template instead of creating duplicate")
                    
                    # Get the questions for the existing template
                    existing_questions = []
                    try:
                        variables = db.query(TemplateVariable).filter(
                            TemplateVariable.template_id == existing_template.id
                        ).order_by(TemplateVariable.id).all()
                        
                        for var in variables:
                            question_data = None
                            if var.question:
                                import json
                                try:
                                    question_data = json.loads(var.question)
                                except json.JSONDecodeError:
                                    pass
                            
                            existing_questions.append({
                                "key": var.key,
                                "question": question_data.get("question", f"What is the {var.label}?") if question_data else f"What is the {var.label}?",
                                "description": var.description,
                                "example": var.example,
                                "required": var.required,
                                "dtype": var.dtype,
                                "regex": var.regex,
                                "enum_values": var.enum_values
                            })
                        
                        logger.info(f"Retrieved {len(existing_questions)} questions for existing template")
                        
                    except Exception as e:
                        logger.error(f"Error retrieving questions for existing template: {e}")
                        existing_questions = []
                    
                    logger.info(f"RETURNING EXISTING TEMPLATE: {existing_template.template_id}")
                    return existing_template, existing_questions
            
            # Save template to database (only after duplicate check passes)
            logger.info("Saving template to database")
            template_record = Template(
                template_id=template_id,
                title=template_name,
                body_md=template_with_frontmatter,
                similarity_tags=similarity_tags,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                file_description=file_description,
                embedding=embedding
            )
            
            db.add(template_record)
            db.commit()
            db.refresh(template_record)
            logger.info(f"Template saved with embedding of dimension {len(embedding) if embedding else 0}")
            
            # Save template variables to database
            logger.info(f"Saving {len(variables)} template variables to database")
            for var in variables:
                # Find the corresponding question for this variable by key
                var_question = None
                for question in questions:
                    if question.get('key') == var.get('key'):
                        var_question = question
                        break
                
                # Convert question to JSON string if it exists
                question_json = None
                if var_question:
                    import json
                    question_json = json.dumps(var_question)
                
                variable_record = TemplateVariable(
                    template_id=template_record.id,  # Foreign key to template.id (not template_id string)
                    key=var.get('key'),
                    label=var.get('label'),
                    description=var.get('description'),
                    example=var.get('example'),
                    required=var.get('required', False),
                    dtype=var.get('dtype', 'string'),
                    regex=var.get('regex'),
                    enum_values=var.get('enum_values'),
                    question=question_json
                )
                db.add(variable_record)
            
            db.commit()
            logger.info(f"Successfully saved template and {len(variables)} variables to database")
            
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
    
    def generate_markdown_with_frontmatter(
        self,
        template: Any,
        variables: List[Any] = None
    ) -> str:
        """
        Return the template's markdown content which already includes YAML frontmatter.
        
        Since templates are now generated with YAML frontmatter by GenAI,
        this method simply returns the body_md field as-is.
        
        Args:
            template: Template model instance with body_md
            variables: (Optional, unused) List of TemplateVariable model instances
            
        Returns:
            Markdown string with YAML front-matter
            
        Raises:
            ValueError: If template is invalid
        """
        if not template:
            raise ValueError("Template cannot be None")
        
        if not hasattr(template, 'body_md') or not template.body_md:
            raise ValueError("Template must have body_md content")
        
        try:
            logger.info(f"Returning markdown with frontmatter for template: {template.template_id}")
            
            # Template already contains YAML frontmatter generated by GenAI
            markdown_content = template.body_md
            
            logger.info(f"Successfully retrieved markdown ({len(markdown_content)} chars)")
            return markdown_content
            
        except Exception as e:
            logger.error(f"Error retrieving markdown with front-matter: {e}")
            raise ValueError(f"Failed to retrieve markdown: {str(e)}")
    
    def render_draft(
        self,
        template: Any,
        answers: Dict[str, Any]
    ) -> str:
        """
        Render a draft document by replacing template placeholders with actual values.
        
        Args:
            template: Template model instance with body_md
            answers: Dictionary mapping variable keys to their values
            
        Returns:
            Rendered markdown string with placeholders replaced
            
        Raises:
            ValueError: If template is invalid
        """
        if not template:
            raise ValueError("Template cannot be None")
        
        if not hasattr(template, 'body_md') or not template.body_md:
            raise ValueError("Template must have body_md content")
        
        if not isinstance(answers, dict):
            raise ValueError("Answers must be a dictionary")
        
        try:
            logger.info(f"Rendering draft for template: {template.template_id}")
            
            body_md = template.body_md
            
            # Extract only the template body (skip YAML frontmatter if present)
            if body_md.startswith("---"):
                # Split by the second occurrence of "---"
                parts = body_md.split("---", 2)
                if len(parts) >= 3:
                    # parts[0] is empty, parts[1] is frontmatter, parts[2] is body
                    draft = parts[2].strip()
                    logger.info("Extracted template body from YAML frontmatter")
                else:
                    # Malformed frontmatter, use entire content
                    draft = body_md
                    logger.warning("Malformed YAML frontmatter, using entire content")
            else:
                # No frontmatter, use entire content
                draft = body_md
            
            # Replace each placeholder with its corresponding answer
            replaced_count = 0
            for key, value in answers.items():
                placeholder = f"{{{{{key}}}}}"  # {{variable_key}}
                if placeholder in draft:
                    # Convert value to string if it's not already
                    value_str = str(value) if value is not None else ""
                    draft = draft.replace(placeholder, value_str)
                    replaced_count += 1
            
            logger.info(f"Successfully rendered draft with {replaced_count} replacements")
            return draft
            
        except Exception as e:
            logger.error(f"Error rendering draft: {e}")
            raise ValueError(f"Failed to render draft: {str(e)}")
    
    def get_missing_variables(
        self,
        template: Any,
        answers: Dict[str, Any]
    ) -> List[str]:
        """
        Identify which template variables were not provided in answers.
        
        Args:
            template: Template model instance with body_md
            answers: Dictionary mapping variable keys to their values
            
        Returns:
            List of variable keys that are still in template (not filled)
        """
        if not template:
            return []
        
        if not hasattr(template, 'body_md') or not template.body_md:
            return []
        
        if not isinstance(answers, dict):
            answers = {}
        
        try:
            import re
            
            body_md = template.body_md
            
            # Extract only the template body (skip YAML frontmatter if present)
            if body_md.startswith("---"):
                parts = body_md.split("---", 2)
                if len(parts) >= 3:
                    body_md = parts[2]
            
            # Find all placeholders in template {{variable_key}}
            pattern = r'\{\{(\w+)\}\}'
            placeholders = re.findall(pattern, body_md)
            
            # Find which placeholders are not in answers
            missing = []
            for placeholder in set(placeholders):  # Use set to avoid duplicates
                if placeholder not in answers or answers[placeholder] is None or str(answers[placeholder]).strip() == "":
                    missing.append(placeholder)
            
            logger.info(f"Found {len(missing)} missing variables out of {len(set(placeholders))} total")
            return missing
            
        except Exception as e:
            logger.error(f"Error checking for missing variables: {e}")
            return []
    
    def check_duplicate_template(
        self,
        embedding: List[float],
        db: Session,
        similarity_threshold: float = 0.90
    ) -> Optional[Tuple[Template, float]]:
        """
        Check if a very similar template already exists in the database.
        
        Args:
            embedding: Embedding vector of the new template
            db: Database session
            similarity_threshold: Minimum cosine similarity to consider as duplicate (default 0.90 = 90%)
            
        Returns:
            Tuple of (existing_template, similarity_score) if duplicate found, None otherwise
            
        Raises:
            HTTPException: If check fails
        """
        if not embedding:
            logger.warning("No embedding provided for duplicate check")
            return None
        
        if not isinstance(embedding, list):
            raise ValueError("embedding must be a list")
        
        if similarity_threshold < 0.0 or similarity_threshold > 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        
        try:
            from sqlalchemy import text
            
            logger.info(f"Checking for duplicate templates with similarity >= {similarity_threshold}")
            
            # Find the most similar template using cosine distance
            # cosine_distance = 1 - cosine_similarity
            # So similarity >= threshold means distance <= (1 - threshold)
            max_distance = 1.0 - similarity_threshold
            
            result = db.query(
                Template,
                Template.embedding.cosine_distance(embedding).label('distance')
            ).filter(
                Template.embedding.isnot(None)
            ).order_by(
                text('distance')
            ).first()
            
            if result:
                template, distance = result
                similarity = 1.0 - float(distance)
                
                logger.info(f"Most similar template: {template.template_id} with similarity {similarity:.3f}")
                
                if similarity >= similarity_threshold:
                    logger.warning(f"Duplicate template detected! Similarity: {similarity:.3f} (threshold: {similarity_threshold})")
                    return (template, similarity)
                else:
                    logger.info(f"Template is unique. Highest similarity: {similarity:.3f}")
                    return None
            else:
                logger.info("No existing templates found")
                return None
                
        except Exception as e:
            logger.error(f"Error checking for duplicate templates: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to check for duplicate templates: {str(e)}"
            )
    
    def find_similar_templates(
        self,
        user_query: str,
        db: Session,
        top_k: int = 5
    ) -> List[Tuple[Template, float]]:
        """
        Find templates using semantic similarity search.
        
        Args:
            user_query: User's natural language query
            db: Database session
            top_k: Number of top results to return
            
        Returns:
            List of (Template, similarity_score) tuples, sorted by similarity (highest first)
            
        Raises:
            HTTPException: If search fails
        """
        if not user_query or not user_query.strip():
            raise HTTPException(status_code=400, detail="user_query cannot be empty")
        
        if top_k < 1 or top_k > 50:
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 50")
        
        try:
            logger.info(f"Finding similar templates for query: {user_query[:100]}...")
            
            # Generate embedding for user query
            try:
                query_embedding = self.embedder.generate_embedding(user_query)
                logger.info(f"Generated query embedding of dimension {len(query_embedding)}")
            except Exception as e:
                logger.error(f"Failed to generate query embedding: {e}")
                raise HTTPException(status_code=500, detail="Failed to process query")
            
            # Use pgvector for efficient similarity search
            try:
                # Query using cosine distance (pgvector's <=> operator)
                from sqlalchemy import text
                
                results = db.query(
                    Template,
                    Template.embedding.cosine_distance(query_embedding).label('distance')
                ).filter(
                    Template.embedding.isnot(None)
                ).order_by(
                    text('distance')
                ).limit(top_k).all()
                
                if not results:
                    logger.warning("No templates with embeddings found in database")
                    return []
                
                # Convert distance to similarity score (1 - distance for cosine)
                # Cosine distance is 1 - cosine_similarity
                similar_templates = [
                    (template, 1.0 - float(distance))
                    for template, distance in results
                ]
                
                logger.info(f"Found {len(similar_templates)} similar templates")
                for i, (template, score) in enumerate(similar_templates[:3], 1):
                    logger.debug(f"  {i}. {template.title} (similarity: {score:.3f})")
                
                return similar_templates
                
            except SQLAlchemyError as e:
                logger.error(f"Database error during similarity search: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to search templates in database"
                )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in similarity search: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {str(e)}"
            )

    def _generate_embedding_async(
        self,
        document_text: str,
        file_name: str,
        file_description: Optional[str],
        doc_type: Optional[str],
        jurisdiction: Optional[str],
        similarity_tags: List[str]
    ) -> concurrent.futures.Future:
        """
        OPTIMIZED: Generate embedding asynchronously in parallel with other operations
        
        Returns:
            Future object that will contain the embedding when ready
        """
        def generate_embedding():
            try:
                # Use document content for better duplicate detection
                embedding_text = document_text[:1000]  # Use first 1000 chars for embedding
                logger.info(f"Generating embedding for template from document content: {embedding_text[:100]}...")
                
                embedding = self.embedder.generate_embedding(embedding_text)
                logger.info(f"Generated embedding of dimension {len(embedding)}")
                return embedding
                
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                return None
        
        # Submit to thread pool for parallel execution
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(generate_embedding)
            return future