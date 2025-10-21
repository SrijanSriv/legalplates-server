"""
Prompts for Gemini AI service.

This module contains all prompts used for interacting with the Gemini API.
Keeping prompts separate from business logic allows for easier iteration
and improvement of prompt engineering.
"""


class LegalDocumentPrompts:
    """Collection of prompts for legal document processing with Gemini AI."""
    
    @staticmethod
    def extract_variables_initial(text: str) -> str:
        """
        Prompt for extracting variables from the first chunk of a document.
        
        Args:
            text: Document text to analyze
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a legal document templating assistant. Your task is to identify reusable fields in legal documents that can be turned into template variables.

DOCUMENT TEXT:
{text}

INSTRUCTIONS:
1. Identify all fields that vary from case to case (names, dates, amounts, addresses, policy numbers, etc.)
2. Create snake_case keys for each variable (e.g., claimant_full_name, incident_date)
3. For each variable provide:
   - key: snake_case identifier
   - label: Human-readable name
   - description: Clear explanation of what this field represents
   - example: A realistic example value
   - required: true if mandatory, false if optional
   - dtype: data type (string, date, number, currency, address, email, phone)
   - regex: optional regex pattern for validation (e.g., for dates, policy numbers)
4. Deduplicate logically identical fields
5. Extract 3-7 relevant tags that describe this document type for retrieval
6. Do NOT create variables for statutory text, legal requirements, or boilerplate
7. Focus on party-specific facts and case details

Return ONLY valid JSON in this exact format:
{{
    "variables": [
        {{
            "key": "example_key",
            "label": "Example Label",
            "description": "Description of the field",
            "example": "Example value",
            "required": true,
            "dtype": "string",
            "regex": null
        }}
    ],
    "similarity_tags": ["tag1", "tag2", "tag3"],
    "doc_type": "document type",
    "jurisdiction": "jurisdiction if mentioned",
    "file_description": "Brief description of what this document is for"
}}"""
    
    @staticmethod
    def extract_variables_continuation(text: str, existing_variables_json: str) -> str:
        """
        Prompt for extracting variables from subsequent chunks of a document.
        
        Args:
            text: New chunk of document text to analyze
            existing_variables_json: JSON string of previously extracted variables
            
        Returns:
            Formatted prompt string
        """
        return f"""You are continuing to extract variables from a legal document. You've already identified these variables from previous chunks:

EXISTING VARIABLES:
{existing_variables_json}

NEW CHUNK TEXT:
{text}

INSTRUCTIONS:
1. Review the new chunk for any additional variable fields
2. If a field matches an existing variable, DO NOT create a new one - reuse the existing key
3. Only propose NEW variables for fields not covered by existing variables
4. Follow the same format and rules as before
5. If no new variables are needed, return an empty variables array

Return ONLY valid JSON in this exact format:
{{
    "variables": [
        {{
            "key": "new_variable_key",
            "label": "New Variable Label",
            "description": "Description",
            "example": "Example",
            "required": true,
            "dtype": "string",
            "regex": null
        }}
    ],
    "additional_tags": []
}}"""
    
    @staticmethod
    def find_matching_template(user_query: str, templates_json: str) -> str:
        """
        Prompt for finding the best matching template for a user query.
        
        Args:
            user_query: User's document request
            templates_json: JSON string of available templates
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a legal document matching assistant. A user wants to draft a document with this request:

USER REQUEST: "{user_query}"

AVAILABLE TEMPLATES:
{templates_json}

INSTRUCTIONS:
1. Analyze the user's request to understand what type of document they need
2. Match it against available templates based on doc_type, jurisdiction, and tags
3. Assign a confidence score (0.0 to 1.0) for each template
4. Provide a brief explanation for the top match
5. If confidence < 0.6 for all templates, indicate no good match found

Return ONLY valid JSON in this exact format:
{{
    "top_match": {{
        "template_id": "best_match_id",
        "confidence": 0.85,
        "explanation": "This template matches because..."
    }},
    "alternatives": [
        {{
            "template_id": "alternative_id",
            "confidence": 0.65,
            "explanation": "Could also work because..."
        }}
    ],
    "found": true
}}

If no match with confidence >= 0.6, return:
{{
    "top_match": null,
    "alternatives": [],
    "found": false
}}"""
    
    @staticmethod
    def generate_question_from_variable(
        key: str,
        label: str,
        description: str,
        example: str,
        dtype: str
    ) -> str:
        """
        Prompt for generating a user-friendly question from a variable definition.
        
        Args:
            key: Variable key (snake_case)
            label: Human-readable label
            description: Variable description
            example: Example value
            dtype: Data type
            
        Returns:
            Formatted prompt string
        """
        return f"""Convert this variable into a clear, polite question for a legal document:

Variable Key: {key}
Label: {label}
Description: {description}
Example: {example}
Type: {dtype}

INSTRUCTIONS:
Create a natural question that:
1. Is clear and unambiguous
2. Includes context from the description
3. Mentions the expected format if relevant (dates, currency, etc.)
4. Is polite and professional
5. Does NOT use the technical variable key

Return ONLY the question text, nothing else."""
    
    @staticmethod
    def prefill_variables(user_query: str, variables_info_json: str) -> str:
        """
        Prompt for extracting variable values from a user query.
        
        Args:
            user_query: User's input text
            variables_info_json: JSON string of variable definitions
            
        Returns:
            Formatted prompt string
        """
        return f"""Extract any information from the user's query that matches these variables:

USER QUERY: "{user_query}"

VARIABLES TO FILL:
{variables_info_json}

INSTRUCTIONS:
1. Extract any values mentioned in the query that match the variables
2. Only include values you're confident about
3. Format dates as ISO 8601 (YYYY-MM-DD)
4. If nothing can be extracted, return empty object

Return ONLY valid JSON as a flat object:
{{
    "variable_key": "extracted_value"
}}"""


# Convenience function to get all prompts
def get_all_prompts():
    """
    Returns a dictionary of all available prompt methods.
    Useful for documentation or testing purposes.
    """
    return {
        "extract_variables_initial": LegalDocumentPrompts.extract_variables_initial,
        "extract_variables_continuation": LegalDocumentPrompts.extract_variables_continuation,
        "find_matching_template": LegalDocumentPrompts.find_matching_template,
        "generate_question_from_variable": LegalDocumentPrompts.generate_question_from_variable,
        "prefill_variables": LegalDocumentPrompts.prefill_variables,
    }

