"""
ner/storage/embedder.py

Entity embedding generation with dual strategy for semantic matching
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, List
from sentence_transformers import SentenceTransformer

from .models import StoredEntity, StoredChunk

logger = logging.getLogger(__name__)


class EntityEmbedder:
    """
    Generates dual embeddings for entities and single embeddings for chunks
    
    Strategy:
    - Name embeddings: Fast semantic matching for deduplication
    - Context embeddings: Rich contextual discovery for relationships
    - Chunk embeddings: Full text for contextual entity discovery
    """
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 cache_embeddings: bool = True):
        """
        Initialize embedder with sentence transformer model
        
        Args:
            model_name: HuggingFace model for embeddings
            cache_embeddings: Whether to cache embeddings to avoid recomputation
        """
        self.model_name = model_name
        self.cache_embeddings = cache_embeddings
        
        logger.info(f"🧠 Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Embedding cache for performance
        self._embedding_cache: Dict[str, np.ndarray] = {}
        
        logger.info(f"✅ EntityEmbedder initialized (dim: {self.embedding_dim})")
    
    def generate_entity_embeddings(self, entity: StoredEntity) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate dual embeddings for entity
        
        Returns:
            (name_embedding, context_embedding)
        """
        # Generate name embedding for fast matching
        name_text = entity.get_semantic_text_for_name()
        name_embedding = self._get_cached_embedding(name_text, "name")
        
        # Generate context embedding for rich discovery
        context_text = entity.get_semantic_text_for_context()
        context_embedding = self._get_cached_embedding(context_text, "context")
        
        return name_embedding, context_embedding
    
    def generate_chunk_embedding(self, chunk: StoredChunk) -> np.ndarray:
        """
        Generate embedding for chunk text
        
        Returns:
            text_embedding for contextual similarity
        """
        # For long chunks, use preview to avoid token limits
        text_for_embedding = self._prepare_chunk_text(chunk.text)
        return self._get_cached_embedding(text_for_embedding, "chunk")
    
    def update_entity_embeddings(self, entity: StoredEntity) -> bool:
        """
        Update entity embeddings in-place
        
        Returns:
            True if embeddings were updated
        """
        try:
            name_embedding, context_embedding = self.generate_entity_embeddings(entity)
            
            entity.name_embedding = name_embedding
            entity.context_embedding = context_embedding
            entity.update_timestamp()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update embeddings for entity {entity.id}: {e}")
            return False
    
    def update_chunk_embedding(self, chunk: StoredChunk) -> bool:
        """
        Update chunk embedding in-place
        
        Returns:
            True if embedding was updated
        """
        try:
            text_embedding = self.generate_chunk_embedding(chunk)
            chunk.text_embedding = text_embedding
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update embedding for chunk {chunk.id}: {e}")
            return False
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings
        
        Returns:
            Similarity score between 0 and 1
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        # Ensure embeddings are normalized
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Clamp to [0, 1] range and handle numerical issues
        return max(0.0, min(1.0, float(similarity)))
    
    def find_most_similar_entities(self, 
                                 query_embedding: np.ndarray,
                                 candidate_embeddings: List[np.ndarray],
                                 threshold: float = 0.8) -> List[Tuple[int, float]]:
        """
        Find most similar entities above threshold
        
        Args:
            query_embedding: Query embedding to match against
            candidate_embeddings: List of candidate embeddings
            threshold: Minimum similarity threshold
            
        Returns:
            List of (index, similarity_score) tuples sorted by similarity
        """
        if not candidate_embeddings or query_embedding is None:
            return []
        
        similarities = []
        for idx, candidate_embedding in enumerate(candidate_embeddings):
            if candidate_embedding is not None:
                similarity = self.compute_similarity(query_embedding, candidate_embedding)
                if similarity >= threshold:
                    similarities.append((idx, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of normalized embeddings
        """
        if not texts:
            return []
        
        try:
            # Use batch processing for efficiency
            embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
            return [embedding for embedding in embeddings]
            
        except Exception as e:
            logger.error(f"❌ Batch embedding generation failed: {e}")
            # Fallback to individual processing
            return [self._get_cached_embedding(text, "batch") for text in texts]
    
    def _get_cached_embedding(self, text: str, embedding_type: str) -> np.ndarray:
        """
        Get embedding with caching
        
        Args:
            text: Text to embed
            embedding_type: Type prefix for cache key
            
        Returns:
            Normalized embedding
        """
        if not text.strip():
            # Return zero embedding for empty text
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        # Create cache key
        cache_key = f"{embedding_type}:{hash(text.strip())}"
        
        # Check cache
        if self.cache_embeddings and cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        # Generate new embedding
        try:
            embedding = self.model.encode(text.strip(), normalize_embeddings=True)
            
            # Ensure correct dtype and shape
            embedding = np.array(embedding, dtype=np.float32)
            if embedding.ndim > 1:
                embedding = embedding.flatten()
            
            # Cache result
            if self.cache_embeddings:
                self._embedding_cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed for text '{text[:50]}...': {e}")
            # Return zero embedding as fallback
            return np.zeros(self.embedding_dim, dtype=np.float32)
    
    def _prepare_chunk_text(self, text: str, max_length: int = 1000) -> str:
        """
        Prepare chunk text for embedding (handle long texts)
        
        Args:
            text: Full chunk text
            max_length: Maximum character length for embedding
            
        Returns:
            Prepared text for embedding
        """
        if len(text) <= max_length:
            return text.strip()
        
        # For long texts, take beginning + end to preserve context
        half_length = max_length // 2 - 50  # Leave space for separator
        beginning = text[:half_length].strip()
        ending = text[-half_length:].strip()
        
        return f"{beginning} ... {ending}"
    
    def clear_cache(self):
        """Clear embedding cache to free memory"""
        self._embedding_cache.clear()
        logger.info("🧹 Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'cached_embeddings': len(self._embedding_cache),
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name
        }