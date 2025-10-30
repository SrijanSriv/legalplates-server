"""
Prompts for Gemini AI service.

This module contains all prompts used for interacting with the Gemini API.
Keeping prompts separate from business logic allows for easier iteration
and improvement of prompt engineering.
"""
from typing import List, Dict, Any


class LegalDocumentPrompts:
    """Collection of prompts for legal document processing with Gemini AI."""
    
    @staticmethod
    def generate_template_body(
        document_text: str,
        variables: List[Dict[str, Any]]
    ) -> str:
        """
        Prompt for intelligently replacing variable values in document text.
        Uses GenAI ONLY for intelligent body text replacement, not YAML generation.
        
        Args:
            document_text: Original document text
            variables: List of extracted variable definitions with examples
            
        Returns:
            Formatted prompt string
        """
        import json
        
        variables_json = json.dumps(variables, indent=2)
        
        return f"""You are a senior legal advocate who makes and edits legal documents for a living. Your ONLY task is to intelligently replace ALL instances of variable values in the document with placeholders, using your legal expertise to ensure accuracy.

ORIGINAL DOCUMENT:
{document_text}

EXTRACTED VARIABLES (with example values to replace):
{variables_json}

CRITICAL INSTRUCTIONS:

1. **Intelligent Variable Replacement:**
   - Find ALL instances of each variable's example value in the document
   - Replace variations and similar phrasings:
     * Names: "Tom Holland", "Mr. Tom Holland", "Tom Holland Esq.", "B. Kumar" → {{{{claimant_full_name}}}}
     * Dates: "12/07/2025", "July 12 2025", "12-07-2025", "2025-07-12" → {{{{incident_date}}}}
     * Amounts: "450000", "4,50,000", "Rs. 450000", "INR 450000" → {{{{demand_amount_inr}}}}
     * Policy #: "302786965", "Policy No. 302786965", "#302786965" → {{{{policy_number}}}}
   - Use semantic understanding, not just exact text matching
   - Replace with {{{{variable_key}}}} placeholder format (double curly braces)
   - If a variable appears multiple times, replace ALL occurrences

2. **NEVER Replace These (Keep As-Is):**
   ❌ DO NOT replace statutory references (e.g., "Section 138 of the Negotiable Instruments Act, 1881")
   ❌ DO NOT replace legal definitions and requirements
   ❌ DO NOT replace Acts, regulations, or law citations
   ❌ DO NOT replace mandatory legal language or boilerplate clauses
   ❌ DO NOT replace standard legal terms and conditions
   ❌ DO NOT replace legal disclaimers and warranties
   
   ✅ ONLY replace party-specific facts and case-specific details that are in the variables list

3. **Output:**
   - Return ONLY the document text with placeholders
   - Do NOT include YAML frontmatter
   - Do NOT include any explanations
   - **MAINTAIN PROPER MARKDOWN FORMATTING:**
     * Use # for main headings
     * Use ## for section headings  
     * Use ### for subsection headings
     * Use - or * for bullet points
     * Use **bold** for emphasis
     * Use *italics* for emphasis
     * Use proper line breaks and spacing
   - Preserve all original formatting, line breaks, and structure
   - Keep all static/boilerplate text unchanged
   - Keep legal language and statutory references COMPLETELY INTACT
   - **CLEAN UP DOCUMENT ARTIFACTS:**
     * Remove all page numbers (standalone numbers at end of paragraphs)
     * Remove incomplete phrases and sentence fragments
     * Remove footer/header text from PDF extraction
     * Remove random numbers that don't belong to content
     * Clean up line endings with trailing numbers

**CRITICAL FORMATTING REQUIREMENTS (MANDATORY):**
- **CONVERT ALL NUMBERED SECTIONS TO HEADINGS:**
  - "1. That my maiden name is..." → "# Declaration Items" (create a heading for numbered sections)
  - "2. That I got married to..." → "## Marriage Details" (convert numbered items to subheadings)
  - "3. After marriage my name is..." → "## Name Change Details"
  - "4. I have not obtained..." → "## Certificate Status"
  - "5. I state that..." → "## Identity Confirmation"
- **CONVERT ALL NUMBERED LISTS TO MARKDOWN LISTS:**
  - "1. Affidavit should be on..." → "- Affidavit should be on..."
  - "2. Please fill up the details..." → "- Please fill up the details..."
  - "3. Please affix passport size..." → "- Please affix passport size..."
- **CONVERT ALL BULLET POINTS (a., b., i., ii., •, ○) to proper Markdown lists (- or 1.)**
**CRITICAL: NO TABLES ALLOWED - USE BULLET POINTS ONLY**

- **CONVERT ALL TABULAR DATA to simple bullet point lists (NO TABLES - use bullet points instead)**
- **NEVER use | separators or table format**
- **NEVER use --- for table separators**
- **ALWAYS convert tabular data to bullet points**
- **REMOVE ALL NUMBERING from headings** (e.g., "1. Introduction" → "# Introduction", NOT "# 1. Introduction")
- **USE PROPER INDENTATION for nested lists**
- **CONVERT TABULAR DATA to bullet points for service levels, uptime percentages, and service credits**

**CRITICAL CLEANUP REQUIREMENTS:**
- **REMOVE ALL PAGE NUMBERS:** Delete any standalone numbers at the end of paragraphs or lines (e.g., "1", "2", "3", "15", "23")
- **REMOVE INCOMPLETE PHRASES:** Delete any incomplete sentences or phrases that appear to be cut off
- **REMOVE FOOTER TEXT:** Delete any text that appears to be from document footers or headers
- **REMOVE RANDOM NUMBERS:** Delete any isolated numbers that don't belong to the document content
- **CLEAN UP LINE ENDINGS:** Remove any trailing numbers or incomplete text at the end of paragraphs
- **REMOVE DOCUMENT ARTIFACTS:** Delete any text that appears to be PDF extraction artifacts

**SPECIFIC CLEANUP EXAMPLES:**
- "This agreement governs the use of services. 15" → "This agreement governs the use of services."
- "The terms are as follows: 23" → "The terms are as follows:"
- "Service level agreement between parties 7" → "Service level agreement between parties"
- "Incomplete sentence fragment 12" → "Incomplete sentence fragment" (or remove entirely if it's just a fragment)
- "Random text at end 45" → "Random text at end"

EXAMPLE INPUT:
"Dear Sir/Madam, On July 12, 2025, Tom Holland (Mr. Tom Holland) hereby notifies you under Policy #302786965 per Section 138 of the Negotiable Instruments Act, 1881. We demand Rs. 4,50,000. 15"

EXAMPLE OUTPUT (CORRECT):
"Dear Sir/Madam, On {{{{incident_date}}}}, {{{{claimant_full_name}}}} ({{{{claimant_full_name}}}}) hereby notifies you under Policy {{{{policy_number}}}} per Section 138 of the Negotiable Instruments Act, 1881. We demand {{{{demand_amount_inr}}}}."

EXAMPLE OUTPUT (WRONG - DO NOT DO THIS):
"Dear Sir/Madam, On {{{{incident_date}}}}, {{{{claimant_full_name}}}} ({{{{claimant_full_name}}}}) hereby notifies you under Policy {{{{policy_number}}}} per {{{{statute_reference}}}}. We demand {{{{demand_amount_inr}}}}."
 WRONG because "Section 138 of the Negotiable Instruments Act, 1881" is statutory text and must remain unchanged!

MARKDOWN FORMATTING EXAMPLE:
INPUT (with numbered sections):
"1. That my maiden name is Jane Smith.
2. That I got married to John Doe on January 15, 2024.
3. After marriage my name is Jane Doe.
NOTES:
1. Affidavit should be on Non-judicial stamp paper.
2. Please fill up the details as per documents."

OUTPUT (properly formatted Markdown):
"# Declaration Items

## Maiden Name
That my maiden name is {{{{maiden_name}}}}.

## Marriage Details  
That I got married to {{{{husband_name}}}} on {{{{marriage_date}}}}.

## Name Change
After marriage my name is {{{{new_name}}}}.

# Notes
- Affidavit should be on Non-judicial stamp paper.
- Please fill up the details as per documents."

CLEANUP EXAMPLE:
INPUT: "This Service Level Agreement governs the use of services. The terms are as follows: 23"
OUTPUT: "This Service Level Agreement governs the use of services. The terms are as follows:"

INPUT: "Service level agreement between parties. Incomplete sentence fragment 7"
OUTPUT: "Service level agreement between parties."

INPUT: "Random text at end of document 45"
OUTPUT: "Random text at end of document"

MARKDOWN FORMATTING REQUIREMENTS:
You MUST convert the document to proper Markdown format with rich formatting:

1. **Headings Hierarchy (CRITICAL - Handle ALL Numbered Formats):**
   - Main sections: "# Section Name"
   - Subsections: "## Subsection Name"  
   - Sub-subsections: "### Sub-subsection Name"
   - Sub-sub-subsections: "#### Detail Name"
   
   **SPECIFIC CONVERSION RULES:**
   - "1. Introduction" → "# Introduction"
   - "2. Definitions" → "# Definitions"
   - "3. Terms" → "# Terms"
   - "2.1 Support Terms" → "## Support Terms"
   - "2.2 Our objective" → "## Our objective"
   - "3.1.1 Subsection" → "### Subsection"
   - "3.1.2 Another subsection" → "### Another subsection"
   - "4.1.1.1 Detail" → "#### Detail"
   - "4.1.1.2 Another detail" → "#### Another detail"
   
   **REMOVE ALL NUMBERING FROM HEADINGS:**
   - "1. Background" → "# Background" (NOT "# 1. Background")
   - "2.1 Terms" → "## Terms" (NOT "## 2.1 Terms")
   - "3.1.1 Specific Terms" → "### Specific Terms" (NOT "### 3.1.1 Specific Terms")

2. **Lists and Bullets (CRITICAL - Handle ALL List Formats):**
   - Convert bullet points to proper Markdown: "- Item" or "* Item"
   - Convert numbered lists: "1. First item", "2. Second item"
   - Use nested lists with proper indentation
   
   **SPECIFIC CONVERSION RULES:**
   - "• Item" → "- Item"
   - "○ Item" → "- Item"
   - "a. Item" → "- Item" (convert letter bullets to dashes)
   - "b. Item" → "- Item"
   - "i. Item" → "- Item" (convert roman numerals to dashes)
   - "ii. Item" → "- Item"
   - "1. Item" → "1. Item" (keep numbered lists as-is)
   - "2. Item" → "2. Item"
   
   **NESTED LISTS:**
   - Use proper indentation for sub-items
   - "1. Main item" → "1. Main item"
   - "   a. Sub item" → "   - Sub item"
   - "   b. Another sub item" → "   - Another sub item"

3. **Tabular Data (CRITICAL - Convert ALL Tabular Data to Bullet Points):**
   - Convert tabular data to simple bullet point lists (NO TABLES)
   - Use clear, descriptive bullet points instead of table format
   
   **SPECIFIC CONVERSION RULES:**
   - Service level tables → Bullet point lists
   - Uptime percentage tables → Bullet point lists
   - Service credit tables → Bullet point lists
   - Any data in rows/columns → Bullet point lists
   
   **BULLET POINT FORMAT (instead of tables):**
   ```
   - Service Level: 99.9% uptime guarantee
   - Response Time: Maximum 2 hours for critical issues  
   - Support Hours: 24/7 technical support
   - Penalties: Service credits for downtime exceeding SLA
   ```

4. **Emphasis and Formatting:**
   - Use **bold** for important terms, company names, key concepts
   - Use *italics* for emphasis, legal terms, definitions
   - Use `code` for technical terms, percentages, specific values
   - Use > for important quotes or callouts

5. **Structure and Spacing:**
   - Add proper line breaks between sections
   - Use horizontal rules (---) to separate major sections
   - Maintain consistent spacing
   - Keep paragraphs well-formatted with proper line breaks

6. **Special Formatting:**
   - Convert percentages: "99.5%" → "**99.5%**"
   - Convert time periods: "15 minutes" → "**15 minutes**"
   - Convert service names: "F5 Silverline" → "**F5 Silverline**"
   - Convert legal references: "Section 138" → "*Section 138*"
   - Convert contact info: "support@example.com" → "`support@example.com`"

CRITICAL: The output MUST be valid Markdown that renders properly with headings, lists, and formatting. Do NOT return plain text! NO TABLES - use bullet points instead.

EXAMPLE OF PROPER MARKDOWN OUTPUT:
```markdown
# Service Level Agreement
**Last updated:** {{{{agreement_date}}}}

## Introduction and Applicability
This Service Level Agreement ("SLA") applies to your access and use of the applicable SaaS Offering(s) purchased under the End ULA ("Agreement"). This SLA is divided into the following sections:

- **Section 1:** Monthly Uptime Percentages or other Performance Standards
- **Section 2:** Service Credits  
- **Section 3:** Miscellaneous Terms
- **Section 4:** Definitions

---

## Monthly Uptime Percentages

### F5 Silverline - Web Application Firewall (WAF) Service

- **Monthly Uptime Percentage: 99.999%** - Subject to the special conditions below, we will use commercially reasonable efforts to make the Silverline WAF Service Available to you at least at the Monthly Uptime Percentage of time in the Applicable Monthly Period.
- **Initial Incident Response: 15 minutes** - The amount of time within which we will respond to an initial support request (e-mail or phone) from you.

**Special Conditions:** Periods of Excluded Downtime are not included in the calculation of the Monthly Uptime Percentage.

---

## Service Credits

### F5 Silverline - Web Application Firewall (WAF) Service

- **Service Outage greater than 60 consecutive seconds** → **2 days** of Service Credit
- **Service Outage greater than 60 consecutive minutes** → **5 days** of Service Credit  
- **Service Outage greater than 24 consecutive hours** → **10 days** of Service Credit
- **Initial Incident Response: 15 minutes** → **1 day** of Service Credit

---

## Definitions

**"Applicable Monthly Period"** means each month during a Service Term in which you are entitled to access the applicable SaaS Offering(s).

**"Available"** means the SaaS Offering is available for access and use by you materially in accordance with the functional specifications set forth in the applicable documentation.

**"Monthly Uptime Percentage"** is calculated by subtracting from **100%** the percentage of total minutes during the billing month in which the SaaS Offering subscribed to by you experiences Downtime.

---

## Support Terms

### Our Objective
We are committed to delivering exceptional customer support. Our objective is to provide the best experience.

### Support Levels
1. **Level 1:** 24/7, 365 days a year
2. **Level 2:** Support during weekends and holidays
3. **Level 3:** Monday through Friday business hours
4. **Level 4:** Monday through Friday (except holidays)

### Support Responsibilities
- Address your support needs in an expedient manner
- Create a positive user experience
- Prioritize your issues by importance and time-to-solve
- Establish transparency and expectations on resolution timeline
- Capture feedback and suggestions for improvement

### Escalation Process
1. **Initial Response:** Within 15 minutes
2. **Tier 2 Escalation:** Within 15 minutes
3. **Tier 3 Escalation:** Within 15 minutes
4. **Resolution:** Based on severity level

---

## Service Level Measurement

### Availability Calculation
- **Monthly Uptime Percentage** is calculated by subtracting from 100% the percentage of total minutes during the billing month
- **Downtime** means the total cumulative number of minutes during which the SaaS Offering is Unavailable
- **Excluded Downtime** includes scheduled maintenance, force majeure events, and customer-caused issues

### Response Time Measurement
- **Initial Response Time** commences when an incident or support ticket is generated
- **Resolution Time** is measured from incident creation to resolution
- **Escalation Time** is the maximum allowable time to escalate to higher support tiers

NOW, process the document above. Return ONLY the template body with placeholders in proper Markdown format. NO additional text."""
    
    @staticmethod
    def classify_document_type(text: str) -> str:
        """
        Prompt for classifying whether a document is a legal document or needs to be converted to a legal template.
        
        Args:
            text: Document text to analyze
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a legal document classification assistant. Analyze the following document and determine if it's a legal document or if it describes a business need that should be converted into a legal template.

DOCUMENT TEXT:
{text}

CLASSIFICATION TASK:
1. **LEGAL DOCUMENT**: Contains legal language, terms, clauses, statutory references, or formal legal structure
2. **BUSINESS NEED**: Describes a business requirement, process, or need that should be converted to a legal document

CLASSIFICATION CRITERIA:

**LEGAL DOCUMENT INDICATORS:**
- Contains legal terminology (agreement, contract, terms, conditions, liability, indemnity, etc.)
- References laws, acts, regulations, or statutory provisions
- Contains formal legal clauses (warranties, disclaimers, governing law, etc.)
- Has legal structure (parties, recitals, definitions, terms, signatures)
- Uses formal legal language and boilerplate text

**BUSINESS NEED INDICATORS:**
- Describes business processes, workflows, or requirements
- Mentions business goals, objectives, or outcomes
- Contains informal language or business jargon
- Describes operational procedures or service descriptions
- Lacks formal legal structure or terminology

**CONVERSION SCENARIOS:**
If it's a business need, identify what type of legal document it should become:
- Service Level Agreement (SLA) for service descriptions
- Contract/Agreement for business partnerships
- Terms of Service for service offerings
- Privacy Policy for data handling
- Employment Agreement for HR processes
- Non-Disclosure Agreement (NDA) for confidentiality
- Purchase Agreement for procurement
- License Agreement for intellectual property

Return ONLY valid JSON in this exact format:
{{
    "is_legal_document": true/false,
    "document_type": "legal_document_type" or "business_need_type",
    "suggested_legal_template": "specific_legal_document_type" (if business need),
    "reasoning": "brief explanation of classification",
    "legal_jurisdiction": "jurisdiction if mentioned or inferred",
    "conversion_notes": "how to convert to legal template" (if business need)
}}"""

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

CRITICAL RULES - WHAT NOT TO VARIABLE-IZE:
❌ NEVER create variables for:
   - Statutory references (e.g., "Section 138 of the Negotiable Instruments Act, 1881")
   - Legal definitions and requirements
   - Acts, regulations, or law citations
   - Mandatory legal language or boilerplate clauses
   - Standard legal terms and conditions
   - Legal disclaimers and warranties

✅ ONLY create variables for:
   - Party-specific facts (names, addresses, contact info)
   - Case-specific details (dates, amounts, policy numbers, case numbers)
   - Customizable terms (payment amounts, durations, quantities)
   - Identifiers (account numbers, reference IDs, property descriptions)

**COMPREHENSIVE VARIABLE DETECTION - BE THOROUGH:**

1. **PROPER NOUNS & NAMES:**
   - Company names: "Acme Corp", "Tech Solutions Inc", "ABC Company Ltd"
   - Person names: "John Smith", "Dr. Jane Doe", "Mr. Robert Johnson"
   - Product names: "SoftwareX Pro", "CloudService Enterprise"
   - Location names: "New York", "California", "United States"

2. **NUMBERS & VALUES (LOOK CLOSELY):**
   - Monetary amounts: "$50,000", "Rs. 1,00,000", "€25,000", "INR 50000"
   - Percentages: "99.9%", "95% uptime", "100% availability"
   - Time periods: "24 hours", "2 business days", "30 days", "1 year"
   - Quantities: "100 users", "50GB storage", "10 concurrent sessions"
   - Service levels: "99.9% uptime", "4 hours response time", "2 business days delivery"

3. **DATES & TIMESTAMPS:**
   - Specific dates: "January 15, 2025", "12/31/2024", "2025-01-15"
   - Time periods: "Q1 2025", "FY 2024-25", "January-March 2025"
   - Deadlines: "within 30 days", "by end of month", "before December 31"

4. **IDENTIFIERS & CODES:**
   - Policy numbers: "POL-2025-001", "Policy #12345"
   - Account numbers: "ACC-789456", "Account #987654"
   - Reference numbers: "REF-2025-ABC", "Case #456789"
   - License numbers: "LIC-2025-XYZ", "License #789123"

5. **SERVICE-SPECIFIC METRICS (SLA EXAMPLES):**
   - Uptime requirements: "99.9% uptime", "99.95% availability"
   - Response times: "2 hours", "4 business hours", "same day"
   - Performance metrics: "1000 requests/second", "50ms latency"
   - Capacity limits: "1000 users", "50GB bandwidth", "10TB storage"

6. **CONTRACT-SPECIFIC TERMS:**
   - Renewal periods: "annual renewal", "monthly billing", "quarterly review"
   - Termination clauses: "30 days notice", "immediate termination"
   - Payment terms: "net 30", "due on receipt", "quarterly payments"
   - Service credits: "1 day credit", "5% discount", "free month"

VARIABLE CREATION INSTRUCTIONS:
1. Identify all fields that vary from case to case (names, dates, amounts, addresses, policy numbers, etc.)
2. Create snake_case keys for each variable (e.g., claimant_full_name, incident_date)

**EXTRACTION EXAMPLES FOR SLA DOCUMENTS:**
- "Service Level Agreement between Acme Corp and Tech Solutions Inc" → company_name, client_name
- "99.9% uptime guarantee with 4-hour response time" → uptime_percentage, response_time_hours
- "Contract effective January 1, 2025, expires December 31, 2025" → effective_date, expiration_date
- "Payment of $50,000 due within 30 days" → payment_amount, payment_terms_days
- "Support for up to 1000 concurrent users" → max_concurrent_users
- "Monthly billing at $500 per user" → billing_frequency, price_per_user
- "Service credits of 1 day for each hour of downtime" → service_credit_days_per_hour
- "24/7 support with 2-hour response time" → support_availability, support_response_hours

**CRITICAL: GENERIC TEMPLATE REQUIREMENTS:**
- Create templates for GENERAL entities, not specific companies
- Template names should be generic: "SaaS SLA Template", not "Microsoft SLA Template"
- Template titles should be professional and reusable: "Service Level Agreement", not "Microsoft Office 365 SLA"
- Remove company-specific branding and make templates universally applicable
- Focus on the document TYPE, not the specific parties involved
3. For each variable provide:
   - key: snake_case identifier
   - label: Human-readable name
   - description: Clear explanation of what this field represents
   - example: A **GENERIC, REALISTIC** example value (NOT from the document text)
   - required: true if mandatory, false if optional
   - dtype: data type (string, date, number, currency, address, email, phone)
   - regex: **REQUIRED** regex pattern for validation where applicable:
     * Dates MUST use ISO 8601: "^\\d{{4}}-\\d{{2}}-\\d{{2}}$" (YYYY-MM-DD)
     * Currency MUST be numbers only: "^\\d+(\\.\\d{{2}})?$"
     * Policy/ID numbers: appropriate regex for format validation
     * Phone numbers: appropriate country-specific regex
     * Email: standard email regex

**CRITICAL: BE EXTREMELY THOROUGH - LOOK FOR EVERY POSSIBLE VARIABLE:**
- Scan the ENTIRE document line by line
- Don't miss any numbers, percentages, or time periods
- Extract ALL proper nouns and company names
- Find every date, amount, and identifier
- Look for service metrics, uptime requirements, response times
- Identify payment terms, renewal periods, and contract specifics
- The more variables you extract, the better the template will be

FORMAT REQUIREMENTS:
- All dates MUST be stored as ISO 8601 format (YYYY-MM-DD)
- All currency values MUST be numeric without symbols (e.g., 450000, not Rs. 450000)
- All identifiers (policy numbers, IDs) MUST have regex validation if they follow a pattern

EXAMPLE GENERATION RULES:
- **DO NOT** use values from the document text (e.g., "Sana", "Some Company Name", "Tom Holland")
- **DO** use generic, realistic examples that could apply to any document of this type
- For names: Use common names like "John Doe", "Jane Smith", "ABC Corporation"
- For dates: Use recent dates like "2024-01-15", "2024-12-31"
- For amounts: Use realistic amounts like "50000", "100000", "250000"
- For addresses: Use generic addresses like "123 Main Street, City, State"

4. Deduplicate logically identical fields
5. Extract 7-12 comprehensive tags that describe this document type for retrieval:
   - 3-5 existing document type tags (e.g., "insurance", "notice", "contract", "agreement")
   - 2 short phrases describing specific content/information type (e.g., "incident reporting", "policy claims", "service level terms", "payment schedules")
   - 2 natural language search phrases in "X for Y" format (e.g., "sla for software licensing", "notice for insurance claims", "agreement for data processing")
6. Generate a professional, descriptive template name that:
   - Clearly identifies the document type and purpose
   - Includes jurisdiction if mentioned (e.g., "California Service Level Agreement Template")
   - Uses title case format (2-8 words)
   - Is concise but informative
   - Does NOT use the filename or document name

EXAMPLE:
Good variable: {{"key": "incident_date", "label": "Incident Date", "dtype": "date", "regex": "^\\\\d{{4}}-\\\\d{{2}}-\\\\d{{2}}$", "example": "2024-01-15"}}
Good variable: {{"key": "claim_amount_inr", "label": "Claim Amount (INR)", "dtype": "currency", "regex": "^\\\\d+(\\\\.\\\\d{{2}})?$", "example": "50000"}}
Good variable: {{"key": "claimant_name", "label": "Claimant Full Name", "dtype": "string", "regex": "^[A-Za-z\\\\s]{{2,100}}$", "example": "John Doe"}}
Bad variable: {{"key": "statutory_notice_period", ...}} ← This is a legal requirement, NOT a variable!
Bad example: {{"key": "claimant_name", "example": "Tom Holland"}} ← Using document-specific name!
Good example: {{"key": "claimant_name", "example": "John Doe"}} ← Using generic name!

Return ONLY valid JSON in this exact format:
{{
    "variables": [
        {{
            "key": "example_key",
            "label": "Example Label",
            "description": "Description of the field",
            "example": "Generic Example Value",
            "required": true,
            "dtype": "string",
            "regex": "^appropriate_regex$"
        }}
    ],
    "similarity_tags": ["insurance", "notice", "incident reporting", "policy claims", "notice for insurance claims", "claim for motor vehicle"],
    "doc_type": "document type",
    "jurisdiction": "jurisdiction if mentioned",
    "file_description": "Brief description of what this document is for",
    "template_name": "Professional descriptive name for this template (e.g., 'California Service Level Agreement Template')"
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

CRITICAL RULES - WHAT NOT TO VARIABLE-IZE:
❌ NEVER create variables for:
   - Statutory references (e.g., "Section 138 of the Negotiable Instruments Act, 1881")
   - Legal definitions and requirements
   - Acts, regulations, or law citations
   - Mandatory legal language or boilerplate clauses
   - Standard legal terms and conditions
   - Legal disclaimers and warranties

✅ ONLY create variables for:
   - Party-specific facts (names, addresses, contact info)
   - Case-specific details (dates, amounts, policy numbers, case numbers)
   - Customizable terms (payment amounts, durations, quantities)
   - Identifiers (account numbers, reference IDs, property descriptions)

INSTRUCTIONS:
1. Review the new chunk for any additional variable fields
2. If a field matches an existing variable, DO NOT create a new one - reuse the existing key
3. Only propose NEW variables for fields not covered by existing variables
4. Follow the same format and rules as before, including:
   - ISO 8601 dates (YYYY-MM-DD) with regex: "^\\d{{4}}-\\d{{2}}-\\d{{2}}$"
   - Numeric currency values with regex: "^\\d+(\\.\\d{{2}})?$"
   - Appropriate regex patterns for IDs, emails, phone numbers
5. If no new variables are needed, return an empty variables array
6. Do NOT add new similarity_tags in continuation - tags are only generated from the initial chunk

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
            "regex": "^appropriate_regex$"
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
        return f"""You are a senior legal advocate who makes and edits legal documents for a living. Use your legal expertise to match documents with templates. A user wants to draft a document with this request:

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
        "title": "Template Title",
        "confidence": 0.85,
        "explanation": "This template matches because..."
    }},
    "alternatives": [
        {{
            "template_id": "alternative_id",
            "title": "Alternative Template Title",
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
    def generate_legal_template_from_business_need(
        business_description: str,
        suggested_template_type: str,
        jurisdiction: str = "US"
    ) -> str:
        """
        Prompt for generating a legal template from a business need description.
        
        Args:
            business_description: Description of the business need/process
            suggested_template_type: Type of legal document to create
            jurisdiction: Legal jurisdiction
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a senior legal advocate who makes and edits legal documents for a living. Use your legal expertise to convert the following business description into a proper legal document template.

BUSINESS DESCRIPTION:
{business_description}

TARGET LEGAL DOCUMENT TYPE: {suggested_template_type}
JURISDICTION: {jurisdiction}

LEGAL DOCUMENT GENERATION REQUIREMENTS:

1. **STRUCTURE**: Create a complete legal document with proper sections:
   - Title and parties
   - Recitals/Background
   - Definitions
   - Main terms and conditions
   - Legal clauses (warranties, liability, indemnity, governing law)
   - Signatures

2. **LEGAL LANGUAGE**: Use formal legal terminology and boilerplate clauses appropriate for the document type

3. **VARIABLES**: Identify key fields that should be templated:
   - Party names and contact information
   - Dates (effective dates, termination dates)
   - Financial terms (amounts, payment schedules)
   - Specific terms and conditions
   - Jurisdiction-specific requirements

4. **COMPLIANCE**: Include standard legal clauses:
   - Governing law and jurisdiction
   - Dispute resolution
   - Liability limitations
   - Confidentiality (if applicable)
   - Termination clauses

5. **FORMATTING**: Use proper Markdown formatting:
   - Headers (# ## ###)
   - Lists (- or 1.)
   - Bullet points for schedules/terms (NO TABLES)
   - Bold for emphasis

Return ONLY the complete legal document template with placeholders in {{{{variable_name}}}} format. Include YAML frontmatter with metadata.

EXAMPLE OUTPUT FORMAT:
```yaml
---
template_id: tpl_[type]_v1
title: [Document Title] Template
doc_type: [document_type]
jurisdiction: {jurisdiction}
file_description: [Brief description]
variables:
  - key: party_name
    label: Party Name
    description: Name of the contracting party
    example: "ABC Corporation"
    required: true
    dtype: string
similarity_tags: ["[type]", "agreement", "contract", "[jurisdiction]"]
---

# [DOCUMENT TITLE]

## Parties
This [document type] is entered into between {{{{party_name}}}} ("Party A") and {{{{counterparty_name}}}} ("Party B")...

[Complete legal document with proper structure and placeholders]
```"""

    @staticmethod
    def prefill_variables(user_query: str, variables_info_json: str) -> str:
        """
        Enhanced prompt for extracting variable values from a user query.
        
        Args:
            user_query: User's input text
            variables_info_json: JSON string of variable definitions
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a senior legal advocate who makes and edits legal documents for a living. Use your legal expertise to extract structured information from natural language queries. Extract any information from the user's query that matches these variables:

USER QUERY: "{user_query}"

VARIABLES TO FILL:
{variables_info_json}

ENHANCED EXTRACTION RULES:
1. **Smart Entity Recognition:**
   - Company names: Extract from "Company A with Company B", "between X and Y", "for Company Z"
   - Person names: Extract from "John Doe", "Mr. Smith", "Dr. Johnson"
   - Dates: Convert "March 15, 2024", "15/03/2024", "2024-03-15" to ISO format (YYYY-MM-DD)
   - Amounts: Extract "99.9%", "$50,000", "1000 USD", "INR 50000"
   - Addresses: Extract full addresses, cities, states, countries

2. **Context-Aware Extraction:**
   - "SLA for TechCorp with Acme" → company_name: "TechCorp", client_name: "Acme"
   - "99.9% uptime guarantee" → uptime_percentage: "99.9"
   - "web hosting services" → service_type: "web hosting"
   - "signed on March 15" → agreement_date: "2024-03-15" (assume current year if not specified)

3. **Data Type Handling:**
   - Numbers: Extract as strings but ensure they're numeric
   - Dates: Always format as YYYY-MM-DD
   - Booleans: Convert "yes/no", "true/false", "enabled/disabled"
   - Enums: Match against provided enum values

4. **Confidence Scoring:**
   - Only include values you're highly confident about
   - If uncertain, don't include the variable
   - Prefer exact matches over approximate ones

5. **Formatting Standards:**
   - Dates: ISO 8601 format (YYYY-MM-DD)
   - Currency: Include currency symbol if mentioned
   - Percentages: Include % symbol
   - Names: Preserve original capitalization

Return ONLY valid JSON as a flat object:
{{
    "variable_key": "extracted_value"
}}

If no variables can be confidently extracted, return an empty object: {{}}"""

    @staticmethod
    def extract_variables_and_generate_template_combined(document_text: str) -> str:
        """
        OPTIMIZED: Combined prompt for extracting variables, generating template body, and creating questions
        
        Args:
            document_text: Raw document text
            
        Returns:
            Formatted prompt string
        """
        return f"""You are a senior legal advocate who makes and edits legal documents for a living. Perform ALL these tasks in ONE response with the precision and expertise of a seasoned legal professional:

ORIGINAL DOCUMENT:
{document_text}

TASK 1: EXTRACT VARIABLES
Extract variables following these rules:
❌ NEVER variable-ize: Statutory references, legal definitions, Acts/regulations, mandatory legal language, boilerplate clauses
✅ ONLY variable-ize: Party-specific facts, case-specific details, customizable terms, identifiers

**COMPREHENSIVE VARIABLE DETECTION - LOOK CLOSELY FOR:**

1. **PROPER NOUNS & NAMES:**
   - Company names: "Acme Corp", "Tech Solutions Inc", "ABC Company Ltd"
   - Person names: "John Smith", "Dr. Jane Doe", "Mr. Robert Johnson"
   - Product names: "SoftwareX Pro", "CloudService Enterprise"
   - Location names: "New York", "California", "United States"

2. **NUMBERS & VALUES:**
   - Monetary amounts: "$50,000", "Rs. 1,00,000", "€25,000", "INR 50000"
   - Percentages: "99.9%", "95% uptime", "100% availability"
   - Time periods: "24 hours", "2 business days", "30 days", "1 year"
   - Quantities: "100 users", "50GB storage", "10 concurrent sessions"
   - Service levels: "99.9% uptime", "4 hours response time", "2 business days delivery"

3. **DATES & TIMESTAMPS:**
   - Specific dates: "January 15, 2025", "12/31/2024", "2025-01-15"
   - Time periods: "Q1 2025", "FY 2024-25", "January-March 2025"
   - Deadlines: "within 30 days", "by end of month", "before December 31"

4. **IDENTIFIERS & CODES:**
   - Policy numbers: "POL-2025-001", "Policy #12345"
   - Account numbers: "ACC-789456", "Account #987654"
   - Reference numbers: "REF-2025-ABC", "Case #456789"
   - License numbers: "LIC-2025-XYZ", "License #789123"

5. **SERVICE-SPECIFIC METRICS:**
   - Uptime requirements: "99.9% uptime", "99.95% availability"
   - Response times: "2 hours", "4 business hours", "same day"
   - Performance metrics: "1000 requests/second", "50ms latency"
   - Capacity limits: "1000 users", "50GB bandwidth", "10TB storage"

6. **CONTRACT-SPECIFIC TERMS:**
   - Renewal periods: "annual renewal", "monthly billing", "quarterly review"
   - Termination clauses: "30 days notice", "immediate termination"
   - Payment terms: "net 30", "due on receipt", "quarterly payments"
   - Service credits: "1 day credit", "5% discount", "free month"

**EXTRACTION EXAMPLES:**
- "Service Level Agreement between Acme Corp and Tech Solutions Inc" → company_name, client_name
- "99.9% uptime guarantee with 4-hour response time" → uptime_percentage, response_time_hours
- "Contract effective January 1, 2025, expires December 31, 2025" → effective_date, expiration_date
- "Payment of $50,000 due within 30 days" → payment_amount, payment_terms_days
- "Support for up to 1000 concurrent users" → max_concurrent_users
- "Monthly billing at $500 per user" → billing_frequency, price_per_user

**CRITICAL: GENERIC TEMPLATE REQUIREMENTS:**
- Create templates for GENERAL entities, not specific companies
- Template names should be generic: "SaaS SLA Template", not "Microsoft SLA Template"
- Template titles should be professional and reusable: "Service Level Agreement", not "Microsoft Office 365 SLA"
- Remove company-specific branding and make templates universally applicable
- Focus on the document TYPE, not the specific parties involved

TASK 2: GENERATE TEMPLATE BODY
Replace ALL variable values with {{{{variable_key}}}} placeholders and convert to proper Markdown:
- Convert numbered headings (1., 2.1, 3.1.1) to proper Markdown headings (# ## ### ####)
- Convert bullet points (a., b., i., ii., •, ○) to proper Markdown lists (- or 1.)
- **CRITICAL: Convert tabular data to simple bullet point lists (NO TABLES - use bullet points instead)**
- **NEVER use | separators or table format**
- **NEVER use --- for table separators**
- Remove page numbers and incomplete phrases
- Maintain proper formatting and structure
- **MAKE CONTENT GENERIC: Remove company-specific references and make universally applicable**

TASK 3: GENERATE QUESTIONS
Create user-friendly questions for each variable that are polite, clear, and professional.

Return ONLY valid JSON in this exact format:
{{
    "variables": [
        {{
            "key": "example_key",
            "label": "Example Label",
            "description": "Description of the field",
            "example": "Generic Example Value",
            "required": true,
            "dtype": "string",
            "regex": "^appropriate_regex$"
        }}
    ],
    "template_body": "# Template Title\\n\\nTemplate content with {{{{placeholders}}}}...",
    "questions": [
        {{
            "key": "example_key",
            "question": "What is the example label?",
            "description": "Description of the field",
            "example": "Generic Example Value",
            "required": true,
            "dtype": "string",
            "regex": "^appropriate_regex$"
        }}
    ],
    "similarity_tags": ["tag1", "tag2", "tag3"],
    "doc_type": "document type",
    "jurisdiction": "jurisdiction if mentioned",
    "file_description": "Brief description of what this document is for",
    "template_name": "GENERIC template name (e.g., 'SaaS SLA Template', 'Service Level Agreement', 'Employment Contract Template')"
}}

**TEMPLATE NAME REQUIREMENTS:**
- Use GENERIC names that work for any company
- Examples: "SaaS SLA Template", "Service Level Agreement", "Employment Contract Template"
- NOT: "Microsoft SLA Template", "Google Employment Contract", "Amazon Service Agreement"
- Focus on document TYPE, not specific entities"""

    @staticmethod
    def generate_questions_batch(variables: List[Dict[str, Any]]) -> str:
        """
        OPTIMIZED: Generate all questions in a single API call
        
        Args:
            variables: List of variable definitions
            
        Returns:
            Formatted prompt string
        """
        import json
        variables_json = json.dumps(variables, indent=2)
        
        return f"""Generate user-friendly questions for ALL these variables in ONE response:

VARIABLES:
{variables_json}

INSTRUCTIONS:
Create natural, polite questions that:
1. Are professional and clear
2. Ask for the specific information needed
3. Use appropriate legal terminology
4. Are easy to understand
5. Include helpful context when needed

EXAMPLES:
- For "claimant_name": "What is the full name of the claimant?"
- For "incident_date": "On what date did the incident occur? (Please provide in YYYY-MM-DD format)"
- For "policy_number": "What is the policy number?"
- For "damage_amount": "What is the total amount of damages claimed?"

Return ONLY valid JSON array in this exact format:
[
    {{
        "key": "variable_key",
        "question": "What is the variable label?",
        "description": "Description of the field",
        "example": "Example value",
        "required": true,
        "dtype": "string",
        "regex": "^appropriate_regex$"
    }}
]"""
    


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

