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
            self.model = genai.GenerativeModel('gemini-2.0-flash')
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
    
    def generate_template_body_intelligent(
        self,
        document_text: str,
        variables: List[Dict[str, Any]]
    ) -> str:
        """
        Intelligently replace variable values in document text with placeholders.
        Uses GenAI ONLY for smart replacement, not YAML generation.
        
        Args:
            document_text: Original document text
            variables: List of extracted variable definitions with examples
            
        Returns:
            Template body text with {{placeholders}} (no YAML frontmatter)
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not document_text:
            logger.error("Cannot generate template from empty text")
            raise ValueError("document_text cannot be empty")
        
        if not isinstance(variables, list):
            logger.error(f"variables must be a list, got {type(variables)}")
            raise ValueError("variables must be a list")
        
        try:
            logger.info(f"Generating template body with {len(variables)} variables")
            
            prompt = LegalDocumentPrompts.generate_template_body(
                document_text=document_text,
                variables=variables
            )
            
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                logger.error("Empty response from Gemini API")
                raise ValueError("Failed to generate template body - empty response")
            
            template_body = response.text.strip()
            
            # Remove markdown code blocks if present
            if template_body.startswith("```"):
                lines = template_body.split("\n")
                if len(lines) > 2:
                    # Remove first and last lines (code block delimiters)
                    template_body = "\n".join(lines[1:-1]).strip()
            
            logger.info(f"Successfully generated template body ({len(template_body)} chars)")
            return template_body
            
        except Exception as e:
            logger.error(f"Error generating template body: {e}")
            raise ValueError(f"Failed to generate template body: {str(e)}")
    
    def classify_document_type(self, document_text: str) -> Dict[str, Any]:
        """
        Classify whether a document is a legal document or needs to be converted to a legal template.
        
        Args:
            document_text: Text content of the document
            
        Returns:
            Dictionary with classification results
        """
        prompt = LegalDocumentPrompts.classify_document_type(document_text)
        
        try:
            logger.info("Classifying document type...")
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            logger.info(f"Document classified as: {result.get('document_type', 'unknown')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from document classification: {e}")
            logger.debug(f"Response text: {response.text[:500]}...")
            return {
                "is_legal_document": True,  # Default to legal to be safe
                "document_type": "unknown",
                "suggested_legal_template": None,
                "reasoning": "Failed to classify document",
                "legal_jurisdiction": "US",
                "conversion_notes": None
            }
        except Exception as e:
            logger.error(f"Error in document classification: {e}")
            return {
                "is_legal_document": True,  # Default to legal to be safe
                "document_type": "unknown", 
                "suggested_legal_template": None,
                "reasoning": f"Classification error: {str(e)}",
                "legal_jurisdiction": "US",
                "conversion_notes": None
            }
    
    def generate_legal_template_from_business_need(
        self,
        business_description: str,
        suggested_template_type: str,
        jurisdiction: str = "US"
    ) -> str:
        """
        Generate a legal template from a business need description.
        
        Args:
            business_description: Description of the business need
            suggested_template_type: Type of legal document to create
            jurisdiction: Legal jurisdiction
            
        Returns:
            Generated legal template text
        """
        prompt = LegalDocumentPrompts.generate_legal_template_from_business_need(
            business_description, suggested_template_type, jurisdiction
        )
        
        try:
            logger.info(f"Generating legal template from business need: {suggested_template_type}")
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```yaml" in result_text:
                result_text = result_text.split("```yaml")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            logger.info("Successfully generated legal template from business need")
            return result_text
            
        except Exception as e:
            logger.error(f"Error generating legal template from business need: {e}")
            raise ValueError(f"Failed to generate legal template: {str(e)}")
    
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

    def extract_variables_and_generate_template_combined(
        self, 
        document_text: str
    ) -> Dict[str, Any]:
        """
        OPTIMIZED: Single API call that extracts variables, generates template body, and creates questions
        
        Args:
            document_text: Raw document text
            
        Returns:
            Dictionary with variables, template_body, and questions
        """
        logger.info("Starting combined variable extraction, template generation, and question creation")
        
        prompt = LegalDocumentPrompts.extract_variables_and_generate_template_combined(document_text)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            logger.info(f"Combined processing completed: {len(result.get('variables', []))} variables extracted")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from combined processing: {e}")
            logger.debug(f"Response text: {response.text[:500]}...")
            raise ValueError(f"Failed to parse combined processing result: {str(e)}")
        except Exception as e:
            logger.error(f"Error in combined processing: {e}")
            raise ValueError(f"Combined processing failed: {str(e)}")

    def generate_questions_batch(
        self, 
        variables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        OPTIMIZED: Generate all questions in a single API call instead of individual calls
        
        Args:
            variables: List of variable definitions
            
        Returns:
            List of question dictionaries
        """
        if not variables:
            logger.warning("No variables provided for batch question generation")
            return []
        
        logger.info(f"Generating questions for {len(variables)} variables in batch")
        
        prompt = LegalDocumentPrompts.generate_questions_batch(variables)
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            questions = json.loads(result_text)
            
            logger.info(f"Successfully generated {len(questions)} questions in batch")
            return questions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from batch question generation: {e}")
            logger.debug(f"Response text: {response.text[:500]}...")
            # Fallback to individual generation
            logger.warning("Falling back to individual question generation")
            return self.generate_questions_from_variables(variables)
        except Exception as e:
            logger.error(f"Error in batch question generation: {e}")
            # Fallback to individual generation
            logger.warning("Falling back to individual question generation")
            return self.generate_questions_from_variables(variables)
    
    def prefill_variables_from_query(
        self, 
        user_query: str, 
        variables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Enhanced variable prefilling with confidence scoring and validation
        
        Args:
            user_query: User's input text
            variables: List of variable definitions
            
        Returns:
            Dictionary mapping variable keys to extracted values with confidence scores
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
            
            # Enhanced variable info with enum values and regex patterns
            variables_info = json.dumps([{
                "key": v.get("key"),
                "label": v.get("label"),
                "description": v.get("description"),
                "dtype": v.get("dtype", "string"),
                "regex": v.get("regex"),
                "enum_values": v.get("enum_values"),
                "required": v.get("required", False)
            } for v in variables if isinstance(v, dict) and v.get("key")], indent=2)
            
            prompt = LegalDocumentPrompts.prefill_variables(user_query, variables_info)
            
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Validate and clean the results
            validated_result = self._validate_prefilled_values(result, variables)
            
            if validated_result:
                logger.info(f"Successfully prefilled {len(validated_result)} variables from query")
            else:
                logger.info("No variables could be prefilled from query")
            
            return validated_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Gemini prefill response: {e}")
            logger.debug(f"Response text: {result_text[:500] if 'result_text' in locals() else 'N/A'}...")
            return {}
        except Exception as e:
            logger.error(f"Error in prefilling variables: {e}")
            return {}
    
    def _validate_prefilled_values(
        self, 
        prefilled_values: Dict[str, Any], 
        variables: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate and clean prefilled values against variable definitions
        
        Args:
            prefilled_values: Raw extracted values from Gemini
            variables: Variable definitions with validation rules
            
        Returns:
            Validated and cleaned values
        """
        if not prefilled_values:
            return {}
        
        validated = {}
        variable_map = {v.get("key"): v for v in variables if v.get("key")}
        
        for key, value in prefilled_values.items():
            if key not in variable_map:
                logger.warning(f"Unknown variable key in prefill result: {key}")
                continue
            
            var_def = variable_map[key]
            validated_value = self._validate_single_value(value, var_def)
            
            if validated_value is not None:
                validated[key] = validated_value
                logger.debug(f"Validated {key}: {value} → {validated_value}")
            else:
                logger.warning(f"Failed validation for {key}: {value}")
        
        return validated
    
    def _validate_single_value(self, value: Any, var_def: Dict[str, Any]) -> Any:
        """
        Validate a single prefilled value against its variable definition
        
        Args:
            value: The extracted value
            var_def: Variable definition with validation rules
            
        Returns:
            Validated value or None if invalid
        """
        if not value:
            return None
        
        # Convert to string for validation
        str_value = str(value).strip()
        if not str_value:
            return None
        
        # Check enum values
        enum_values = var_def.get("enum_values")
        if enum_values:
            # Case-insensitive matching
            for enum_val in enum_values:
                if str_value.lower() == enum_val.lower():
                    return enum_val  # Return original case
            logger.debug(f"Value '{str_value}' not in enum values: {enum_values}")
            return None
        
        # Check regex pattern
        regex_pattern = var_def.get("regex")
        if regex_pattern:
            import re
            if not re.match(regex_pattern, str_value):
                logger.debug(f"Value '{str_value}' doesn't match regex: {regex_pattern}")
                return None
        
        # Type-specific validation
        dtype = var_def.get("dtype", "string")
        
        if dtype == "date":
            # Validate date format (YYYY-MM-DD)
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', str_value):
                logger.debug(f"Invalid date format: {str_value}")
                return None
        
        elif dtype == "number":
            # Validate numeric format
            try:
                # Try to convert to float to validate
                float(str_value.replace('%', '').replace('$', '').replace(',', ''))
            except ValueError:
                logger.debug(f"Invalid number format: {str_value}")
                return None
        
        elif dtype == "boolean":
            # Convert to boolean
            if str_value.lower() in ['true', 'yes', 'enabled', '1']:
                return True
            elif str_value.lower() in ['false', 'no', 'disabled', '0']:
                return False
            else:
                logger.debug(f"Invalid boolean value: {str_value}")
                return None
        
        return str_value

