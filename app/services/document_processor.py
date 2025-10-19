from unstructured.partition.auto import partition
from typing import Dict, Any, List
import os
from pathlib import Path


class DocumentProcessor:    
    @staticmethod
    def extract_content(file_path: str) -> Dict[str, Any]:
        """
        Extract raw content from PDF or DOCX
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Partition document
            elements = partition(
                filename=file_path,
                strategy="fast",
                include_page_breaks=False,
            )
            
            # Extract plain text from all elements
            text_parts = []
            metadata = {
                "total_elements": len(elements),
                "element_types": {},
                "file_type": Path(file_path).suffix
            }
            
            for element in elements:
                elem_type = type(element).__name__
                
                # Track element types
                metadata["element_types"][elem_type] = \
                    metadata["element_types"].get(elem_type, 0) + 1
                
                # Extract text
                text = element.text if hasattr(element, 'text') else str(element)
                text_parts.append(text)
            
            raw_text = "\n".join(text_parts)
            
            return {
                "success": True,
                "raw_text": raw_text,
                "metadata": metadata
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_text": "",
                "metadata": {}
            }
    
    @staticmethod
    def save_temp_file(file_content: bytes, filename: str, upload_dir: str = "/tmp/uploads") -> str:
        """Save uploaded file temporarily for processing"""
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return file_path
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Remove temporary file after processing"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning up temp file: {e}")