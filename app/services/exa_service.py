"""
Service for web retrieval using exa.ai to find legal document templates.
"""
import os
from typing import List, Dict, Any, Optional
import requests
import logging

logger = logging.getLogger(__name__)


class ExaService:
    """Service for web retrieval using exa.ai"""
    
    def __init__(self):
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            logger.warning("EXA_API_KEY not found in environment variables - web search will be disabled")
            self.client = None
        else:
            try:
                from exa_py import Exa
                self.client = Exa(api_key=api_key)
                logger.info("ExaService initialized successfully")
            except ImportError:
                logger.error("exa_py package not installed - web search will be disabled")
                self.client = None
    
    def is_available(self) -> bool:
        """Check if Exa service is available"""
        return self.client is not None
    
    def search_legal_templates(
        self,
        user_query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for legal document templates on the web with enhanced legal-specific terms.
        
        Args:
            user_query: User's search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with title, url, text, highlights, score
        """
        if not self.is_available():
            logger.warning("Exa service not available, returning empty results")
            return []
        
        # Enhanced query with comprehensive legal context
        legal_terms = [
            "legal document template",
            "contract template",
            "agreement template", 
            "legal form",
            "legal document sample",
            "legal template free",
            "legal document format",
            "contract sample",
            "agreement sample",
            "legal document example",
            "legal form template",
            "legal document draft",
            "sample legal document",
            "template legal form",
            "free legal template",
            "legal document format example"
        ]
        
        # Add jurisdiction-specific terms if detected
        jurisdiction_terms = []
        query_lower = user_query.lower()
        if any(term in query_lower for term in ["india", "indian", "delhi", "mumbai", "bangalore", "chennai", "kolkata"]):
            jurisdiction_terms.extend(["india", "indian law", "indian contract act", "indian legal"])
        elif any(term in query_lower for term in ["us", "usa", "united states", "california", "new york", "texas"]):
            jurisdiction_terms.extend(["united states", "us law", "american law", "us legal"])
        elif any(term in query_lower for term in ["uk", "britain", "england", "london", "scotland"]):
            jurisdiction_terms.extend(["uk law", "british law", "english law", "uk legal"])
        
        # Add document-type specific terms
        doc_type_terms = []
        if any(term in query_lower for term in ["affidavit", "sworn", "statement"]):
            doc_type_terms.extend(["affidavit template", "sworn statement", "legal affidavit", "affidavit sample", "affidavit format"])
        elif any(term in query_lower for term in ["contract", "agreement", "deal"]):
            doc_type_terms.extend(["contract template", "agreement template", "legal contract", "contract sample"])
        elif any(term in query_lower for term in ["notice", "demand", "legal notice"]):
            doc_type_terms.extend(["legal notice", "demand notice", "legal notice template", "notice sample"])
        elif any(term in query_lower for term in ["sla", "service level", "service agreement"]):
            doc_type_terms.extend(["service level agreement", "sla template", "service agreement", "sla sample"])
        
        # Build comprehensive search query with focus on actual templates
        enhanced_query_parts = [user_query]
        enhanced_query_parts.extend(legal_terms[:5])  # Add more legal terms
        if jurisdiction_terms:
            enhanced_query_parts.extend(jurisdiction_terms[:2])  # Add jurisdiction terms
        if doc_type_terms:
            enhanced_query_parts.extend(doc_type_terms[:3])  # Add more document type terms
        
        # Add template-specific terms
        enhanced_query_parts.extend(["template", "sample", "format", "example", "draft"])
        
        enhanced_query = " ".join(enhanced_query_parts)
        
        try:
            logger.info(f"Searching web for legal templates: {enhanced_query}")
            
            # Search with exa.ai using enhanced query
            results = self.client.search_and_contents(
                enhanced_query,
                num_results=max_results * 2,  # Get more results to filter better
                text=True,
                highlights=True,
                use_autoprompt=True,  # Let Exa enhance the query further
                type="neural",  # Use neural search for better results
                exclude_domains=["contracteasily.com", "evaakil.com", "lawrato.com", "vakilsearch.com", "legalraasta.com"]  # Exclude commercial sites
            )
            
            search_results = []
            for result in results.results:
                # Filter for legal-relevant content and exclude commercial sites
                if self._is_legal_content(result) and self._is_actual_template(result):
                    search_results.append({
                        "title": result.title,
                        "url": result.url,
                        "text": result.text if hasattr(result, 'text') else None,
                        "highlights": result.highlights if hasattr(result, 'highlights') else None,
                        "score": result.score if hasattr(result, 'score') else None
                    })
                    
                    # Stop when we have enough good results
                    if len(search_results) >= max_results:
                        break
            
            logger.info(f"Found {len(search_results)} legal-relevant web results")
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching with exa.ai: {e}")
            return []
    
    def _is_legal_content(self, result) -> bool:
        """
        Check if search result contains legal content.
        
        Args:
            result: Exa search result
            
        Returns:
            True if content appears to be legal-related
        """
        legal_keywords = [
            "agreement", "contract", "terms", "conditions", "liability",
            "indemnity", "warranty", "disclaimer", "governing law",
            "jurisdiction", "party", "parties", "whereas", "hereby",
            "legal", "law", "statute", "regulation", "clause", "section",
            "template", "form", "document", "provision", "stipulation",
            "affidavit", "sworn", "statement", "notice", "demand",
            "service level", "sla", "agreement", "binding", "enforceable",
            "breach", "remedy", "damages", "penalty", "termination"
        ]
        
        # Check title first - if title contains legal terms, it's likely legal
        title_lower = result.title.lower() if result.title else ""
        title_legal_score = sum(1 for keyword in legal_keywords if keyword in title_lower)
        
        # If title has 2+ legal keywords, it's likely legal
        if title_legal_score >= 2:
            return True
        
        # Check text content
        text_content = ""
        if hasattr(result, 'text') and result.text:
            text_content = result.text.lower()
        elif hasattr(result, 'highlights') and result.highlights:
            text_content = " ".join(result.highlights).lower()
        
        # Count legal keywords in content
        legal_keyword_count = sum(1 for keyword in legal_keywords if keyword in text_content)
        
        # Also check for legal phrases
        legal_phrases = [
            "governing law", "legal document", "binding agreement", "terms and conditions",
            "legal notice", "service level agreement", "affidavit of", "sworn statement",
            "legal template", "contract template", "agreement template"
        ]
        
        phrase_count = sum(1 for phrase in legal_phrases if phrase in text_content)
        
        # Consider it legal if it has:
        # - At least 4 legal keywords, OR
        # - At least 2 legal keywords + 1 legal phrase, OR
        # - At least 1 legal phrase + title has 1+ legal keyword
        return (
            legal_keyword_count >= 4 or
            (legal_keyword_count >= 2 and phrase_count >= 1) or
            (phrase_count >= 1 and title_legal_score >= 1)
        )
    
    def _is_actual_template(self, result) -> bool:
        """
        Check if search result is an actual legal template, not commercial content.
        
        Args:
            result: Exa search result
            
        Returns:
            True if content appears to be an actual legal template
        """
        title = result.title.lower() if result.title else ""
        url = result.url.lower() if result.url else ""
        
        # Simple check: if title or URL contains template-related keywords, it's likely a template
        template_keywords = ["template", "sample", "form", "draft", "example", "agreement", "contract"]
        
        # Check title
        if any(keyword in title for keyword in template_keywords):
            return True
            
        # Check URL
        if any(keyword in url for keyword in template_keywords):
            return True
            
        # If it's legal content and doesn't look like a commercial site, include it
        # Exclude obvious commercial sites
        commercial_domains = ["amazon", "ebay", "etsy", "shopify", "wix", "squarespace"]
        if any(domain in url for domain in commercial_domains):
            return False
            
        # For legal content, be more permissive
        return True
    
    def fetch_document_content(self, url: str) -> Optional[str]:
        """
        Fetch full content from a URL.
        
        Args:
            url: URL to fetch content from
            
        Returns:
            Document content as string, or None if fetch fails
        """
        try:
            logger.info(f"Fetching document from: {url}")
            response = requests.get(
                url, 
                timeout=10,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            logger.info(f"Successfully fetched {len(response.text)} characters from {url}")
            return response.text
            
        except Exception as e:
            logger.error(f"Error fetching document from {url}: {e}")
            return None
    
    def search_for_similar_template(
        self,
        doc_type: str,
        jurisdiction: str = "",
        additional_context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Search for templates similar to specified criteria.
        
        Args:
            doc_type: Type of legal document
            jurisdiction: Legal jurisdiction (e.g., "California", "IN")
            additional_context: Additional search context
            
        Returns:
            List of search results
        """
        query_parts = ["legal template", doc_type]
        
        if jurisdiction:
            query_parts.append(jurisdiction)
        
        if additional_context:
            query_parts.append(additional_context)
        
        query = " ".join(query_parts)
        logger.info(f"Searching for similar template: {query}")
        
        return self.search_legal_templates(query, max_results=5)
    
    def get_best_template_from_web(
        self,
        user_query: str,
        max_results: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Search web and return the best matching template with its content.
        
        Args:
            user_query: User's search query
            max_results: Number of results to fetch
            
        Returns:
            Dictionary with template info and content, or None if not found
        """
        if not self.is_available():
            return None
        
        # Search for templates
        results = self.search_legal_templates(user_query, max_results=max_results)
        
        if not results:
            logger.warning("No web results found")
            return None
        
        # Try to fetch content from the best result
        for result in results:
            url = result.get("url")
            if not url:
                continue
            
            # Use the text from search results if available
            content = result.get("text")
            
            # If no text in results, try fetching from URL
            if not content or len(content.strip()) < 100:
                content = self.fetch_document_content(url)
            
            if content and len(content.strip()) >= 100:
                logger.info(f"Found suitable template from: {url}")
                return {
                    "title": result.get("title", "Web Template"),
                    "url": url,
                    "content": content,
                    "score": result.get("score"),
                    "highlights": result.get("highlights")
                }
        
        logger.warning("No suitable content found in web results")
        return None

