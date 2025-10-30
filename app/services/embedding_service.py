# Embedding service for semantic search
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import os
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and comparing embeddings for semantic search."""
    
    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        try:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded successfully (dimension: {self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise ValueError(f"Failed to initialize embedding service: {str(e)}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            ValueError: If text is empty or embedding generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            raise ValueError("Text cannot be empty")
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding_list = embedding.tolist()
            logger.debug(f"Generated embedding of dimension {len(embedding_list)} for text: {text[:50]}...")
            return embedding_list
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise ValueError(f"Failed to generate embedding: {str(e)}")
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1 (higher is more similar)
        """
        if not embedding1 or not embedding2:
            logger.warning("Empty embedding provided for similarity computation")
            return 0.0
        
        if len(embedding1) != len(embedding2):
            logger.error(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
            return 0.0
        
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero-norm vector encountered in similarity computation")
                return 0.0
            
            similarity = float(dot_product / (norm1 * norm2))
            # Clamp to [0, 1] range (cosine similarity can be -1 to 1)
            similarity = max(0.0, min(1.0, (similarity + 1) / 2))
            
            return similarity
        except Exception as e:
            logger.error(f"Error computing similarity: {e}")
            return 0.0
    
    def find_most_similar(
        self, 
        query_embedding: List[float], 
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[int]:
        """
        Find indices of most similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embedding vectors
            top_k: Number of top results to return
            
        Returns:
            List of indices sorted by similarity (highest first)
        """
        if not query_embedding or not candidate_embeddings:
            logger.warning("Empty embeddings provided for similarity search")
            return []
        
        try:
            similarities = []
            for i, candidate in enumerate(candidate_embeddings):
                sim = self.compute_similarity(query_embedding, candidate)
                similarities.append((i, sim))
            
            # Sort by similarity descending
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Return top k indices
            result_indices = [idx for idx, _ in similarities[:top_k]]
            logger.info(f"Found {len(result_indices)} most similar candidates from {len(candidate_embeddings)} total")
            
            return result_indices
        except Exception as e:
            logger.error(f"Error finding most similar: {e}")
            return []
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this service.
        
        Returns:
            Embedding dimension (e.g., 384 for all-MiniLM-L6-v2)
        """
        return self.embedding_dim

