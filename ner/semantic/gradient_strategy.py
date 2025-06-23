"""
Gradient-based Semantic Chunking Strategy
"""

import numpy as np
from typing import List
from sklearn.metrics.pairwise import cosine_similarity

from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class GradientChunker(SemanticChunkingStrategy):
    """
    Gradient-based semantic chunking strategy
    
    Compares consecutive sentences and cuts when semantic gradient
    exceeds threshold. Memory efficient - only needs 3 embeddings at a time.
    """
    
    def __init__(self, config: SemanticChunkingConfig):
        super().__init__(config)
        
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        """
        Chunk text using gradient-based semantic analysis
        
        Args:
            text: Input text to chunk
            domains: Optional domain information for threshold tuning
            
        Returns:
            List of TextChunk objects
        """
        # Get domain-specific threshold
        threshold = self._get_domain_threshold(domains)
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if len(sentences) < 3:
            # Too few sentences, return as single chunk
            return [TextChunk(
                id=0,
                start=0,
                end=len(text),
                text=text
            )]
        
        # Find gradient-based boundaries
        boundaries = self._find_gradient_boundaries(sentences, threshold)
        
        # Create chunks from boundaries
        return self._create_chunks(text, sentences, boundaries)
    
    def estimate_ram_usage(self, text_length: int) -> int:
        """
        Estimate RAM usage for gradient chunking
        
        Args:
            text_length: Length of text in characters
            
        Returns:
            Estimated RAM usage in bytes
        """
        # Model size + 3 embeddings (streaming processing)
        model_ram = 1000 * 1024 * 1024  # ~1GB for multilingual model
        embedding_ram = 3 * 384 * 4  # 3 embeddings * 384 dims * 4 bytes (float32)
        processing_overhead = 50 * 1024 * 1024  # 50MB processing overhead
        
        return model_ram + embedding_ram + processing_overhead
    
    def _get_domain_threshold(self, domains: List[BaseNER] = None) -> float:
        """Get domain-specific threshold or use config default"""
        if domains and len(domains) > 0:
            domain_name = domains[0].config.name
            
            # Domain-specific threshold adjustments
            domain_adjustments = {
                "literary": 0.12,    # Subtle narrative transitions
                "simple": 0.10,      # More aggressive for simple content
                "auto": 0.15         # Default
            }
            
            return domain_adjustments.get(domain_name, self.config.threshold)
        
        return self.config.threshold
    
    def _find_gradient_boundaries(self, sentences: List[str], threshold: float) -> List[int]:
        """
        Find chunk boundaries using gradient analysis
        
        Args:
            sentences: List of sentences
            threshold: Gradient threshold for cutting
            
        Returns:
            List of sentence indices where to cut
        """
        if len(sentences) < 3:
            return []
        
        boundaries = []
        model = self._load_embedding_model()
        
        # Initialize with first two embeddings
        prev_embedding = model.encode(sentences[0])
        curr_embedding = model.encode(sentences[1])
        prev_similarity = cosine_similarity([prev_embedding], [curr_embedding])[0][0]
        
        # Stream through remaining sentences
        for i in range(2, len(sentences)):
            # Get next embedding
            next_embedding = model.encode(sentences[i])
            next_similarity = cosine_similarity([curr_embedding], [next_embedding])[0][0]
            
            # Calculate gradient (change in similarity)
            gradient = abs(prev_similarity - next_similarity)
            
            # Check if gradient exceeds threshold
            if gradient > threshold:
                # Cut before current sentence (i-1)
                boundaries.append(i - 1)
                
                # Optional: Add minimum chunk size validation
                if boundaries and self._validate_chunk_size(sentences, boundaries[-2:]):
                    pass  # Keep boundary
                else:
                    boundaries.pop()  # Remove boundary if chunk too small
            
            # Shift sliding window
            prev_embedding = curr_embedding
            curr_embedding = next_embedding
            prev_similarity = next_similarity
        
        return boundaries
    
    def _validate_chunk_size(self, sentences: List[str], boundary_pair: List[int]) -> bool:
        """
        Validate that chunk between boundaries meets size requirements
        
        Args:
            sentences: All sentences
            boundary_pair: Pair of boundary indices to check
            
        Returns:
            True if chunk size is valid
        """
        if len(boundary_pair) < 2:
            return True  # Can't validate single boundary
        
        start_idx = boundary_pair[0] if boundary_pair[0] >= 0 else 0
        end_idx = boundary_pair[1] if boundary_pair[1] < len(sentences) else len(sentences)
        
        chunk_sentences = sentences[start_idx:end_idx]
        chunk_text = ' '.join(chunk_sentences)
        
        return (len(chunk_text) >= self.config.min_chunk_size and 
                len(chunk_text) <= self.config.max_chunk_size)
    
    def get_strategy_info(self) -> dict:
        """Return information about this strategy"""
        return {
            "name": "gradient",
            "description": "Local gradient-based semantic chunking",
            "memory_efficient": True,
            "streaming_capable": True,
            "domain_tunable": True,
            "threshold": self.config.threshold
        }