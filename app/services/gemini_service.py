import google.generativeai as genai
import json
import os
import re
import logging
from typing import Dict, List, Any, Optional
from app.services.prompts import LegalDocumentPrompts

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-flash-latest')
            logger.info("GeminiService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise ValueError(f"Failed to initialize Gemini model: {str(e)}")
    
    def extract_variables_from_chunk(
        self, 
        text: str, 
        existing_variables: Optional[List[Dict[str, Any]]] = None,
        is_first_chunk: bool = True
    ) -> Dict[str, Any]:
        
        if is_first_chunk or not existing_variables:
            prompt = LegalDocumentPrompts.extract_variables_initial(text)
        else:
            # For subsequent chunks, provide existing variables
            existing_vars_json = json.dumps(existing_variables, indent=2)
            prompt = LegalDocumentPrompts.extract_variables_continuation(text, existing_vars_json)
        
        try:
            logger.info("Calling Gemini API to extract variables from document chunk")
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Extract JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            logger.info(f"Successfully extracted {len(result.get('variables', []))} variables")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini response: {e}")
            logger.debug(f"Response text: {response.text[:500]}...")
            return {"variables": [], "similarity_tags": []}
        except Exception as e:
            logger.error(f"Error calling Gemini API for variable extraction: {e}")
            return {"variables": [], "similarity_tags": []}
    
    def generate_template_from_text(
        self, 
        text: str, 
        variables: List[Dict[str, Any]]
    ) -> str:
        """
        Convert document text to template by replacing variable values with {{placeholders}}
        
        Args:
            text: Original document text
            variables: List of variable definitions with examples
            
        Returns:
            Template text with placeholders
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not text:
            logger.error("Cannot generate template from empty text")
            raise ValueError("text cannot be empty")
        
        if not isinstance(variables, list):
            logger.error(f"variables must be a list, got {type(variables)}")
            raise ValueError("variables must be a list")
        
        try:
            logger.info(f"Generating template from text with {len(variables)} variables")
            
            # Create a mapping of examples to variable keys
            replacements = []
            for var in variables:
                if not isinstance(var, dict):
                    logger.warning(f"Skipping invalid variable: {var}")
                    continue
                    
                if var.get("example"):
                    # Escape special regex characters in the example
                    example = re.escape(str(var.get("example")))
                    key = var.get("key")
                    if key:
                        replacements.append((example, f"{{{{{key}}}}}"))
            
            # Sort by length (longest first) to avoid partial replacements
            replacements.sort(key=lambda x: len(x[0]), reverse=True)
            
            template = text
            replacements_made = 0
            for example, placeholder in replacements:
                # Use word boundaries for better matching
                pattern = r'\b' + example + r'\b'
                new_template = re.sub(pattern, placeholder, template, flags=re.IGNORECASE)
                if new_template != template:
                    replacements_made += 1
                template = new_template
            
            logger.info(f"Successfully generated template with {replacements_made} replacements")
            return template
            
        except Exception as e:
            logger.error(f"Error generating template from text: {e}")
            # Return original text if template generation fails
            return text
    
    def find_matching_template(
        self, 
        user_query: str, 
        templates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use Gemini to classify and find the best matching template
        """
        templates_info = []
        for t in templates:
            templates_info.append({
                "template_id": t["template_id"],
                "title": t["title"],
                "description": t.get("file_description", ""),
                "doc_type": t.get("doc_type", ""),
                "jurisdiction": t.get("jurisdiction", ""),
                "tags": t.get("similarity_tags", [])
            })
        
        templates_json = json.dumps(templates_info, indent=2)
        prompt = LegalDocumentPrompts.find_matching_template(user_query, templates_json)
        
        try:
            logger.info(f"Finding matching template for query: {user_query[:100]}...")
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            if result.get("found"):
                logger.info(f"Found matching template with confidence: {result['top_match'].get('confidence', 0)}")
            else:
                logger.info("No matching template found")
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini template matching response: {e}")
            logger.debug(f"Response text: {response.text[:500]}...")
            return {"top_match": None, "alternatives": [], "found": False}
        except Exception as e:
            logger.error(f"Error in template matching: {e}")
            return {"top_match": None, "alternatives": [], "found": False}
    
    def generate_questions_from_variables(
        self, 
        variables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert variable metadata into human-friendly questions
        
        Args:
            variables: List of variable definitions
            
        Returns:
            List of question dictionaries with keys, questions, and metadata
        """
        if not variables:
            logger.warning("No variables provided for question generation")
            return []
        
        if not isinstance(variables, list):
            logger.error(f"variables must be a list, got {type(variables)}")
            return []
        
        logger.info(f"Generating questions for {len(variables)} variables")
        questions = []
        
        for idx, var in enumerate(variables, start=1):
            if not isinstance(var, dict):
                logger.warning(f"Skipping invalid variable at index {idx}: {var}")
                continue
            
            try:
                if not var.get("key") or not var.get("label"):
                    logger.warning(f"Variable at index {idx} missing key or label, skipping")
                    continue
                
                # Generate prompt for this variable
                prompt = LegalDocumentPrompts.generate_question_from_variable(
                    key=var['key'],
                    label=var['label'],
                    description=var.get('description', ''),
                    example=var.get('example', ''),
                    dtype=var.get('dtype', 'string')
                )
                
                response = self.model.generate_content(prompt)
                question_text = response.text.strip()
                
                questions.append({
                    "key": var["key"],
                    "question": question_text,
                    "description": var.get("description"),
                    "example": var.get("example"),
                    "required": var.get("required", False),
                    "dtype": var.get("dtype", "string"),
                    "regex": var.get("regex"),
                    "enum_values": var.get("enum_values")
                })
                logger.debug(f"Generated question for variable: {var['key']}")
                
            except Exception as e:
                # Fallback to simple question
                logger.warning(f"Error generating question for variable {var.get('key', 'unknown')}: {e}. Using fallback.")
                try:
                    question_text = f"What is the {var['label'].lower()}?"
                    questions.append({
                        "key": var["key"],
                        "question": question_text,
                        "description": var.get("description"),
                        "example": var.get("example"),
                        "required": var.get("required", False),
                        "dtype": var.get("dtype", "string")
                    })
                except Exception as e2:
                    logger.error(f"Failed to create fallback question for variable: {e2}")
                    continue
        
        logger.info(f"Successfully generated {len(questions)} questions")
        return questions
    
    def prefill_variables_from_query(
        self, 
        user_query: str, 
        variables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Try to extract variable values from the user's initial query
        
        Args:
            user_query: User's input text
            variables: List of variable definitions
            
        Returns:
            Dictionary mapping variable keys to extracted values
        """
        if not user_query or not user_query.strip():
            logger.info("Empty query provided for prefilling")
            return {}
        
        if not variables:
            logger.info("No variables provided for prefilling")
            return {}
        
        if not isinstance(variables, list):
            logger.error(f"variables must be a list, got {type(variables)}")
            return {}
        
        try:
            logger.info(f"Attempting to prefill {len(variables)} variables from user query")
            
            variables_info = json.dumps([{
                "key": v.get("key"),
                "label": v.get("label"),
                "description": v.get("description"),
                "dtype": v.get("dtype", "string")
            } for v in variables if isinstance(v, dict) and v.get("key")], indent=2)
            
            prompt = LegalDocumentPrompts.prefill_variables(user_query, variables_info)
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            if result:
                logger.info(f"Successfully prefilled {len(result)} variables from query")
            else:
                logger.info("No variables could be prefilled from query")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini prefill response: {e}")
            logger.debug(f"Response text: {result_text[:500] if 'result_text' in locals() else 'N/A'}...")
            return {}
        except Exception as e:
            logger.error(f"Error in prefilling variables: {e}")
            return {}

