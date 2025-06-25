"""
Percentile-based Semantic Chunking Strategy
"""

import numpy as np
from typing import List
from sklearn.metrics.pairwise import cosine_similarity

from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class PercentileChunker(SemanticChunkingStrategy):
    """
    Percentile-based semantic chunking strategy
    
    Calculates similarity between all consecutive sentences, then cuts
    at points where similarity is below specified percentile threshold.
    Domain-agnostic approach that adapts to document characteristics.
    """
    
    def __init__(self, config: SemanticChunkingConfig):
        super().__init__(config)
        
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        """
        Chunk text using percentile-based semantic analysis
        
        Args:
            text: Input text to chunk
            domains: Optional domain information for percentile tuning
            
        Returns:
            List of TextChunk objects
        """
        # Get domain-specific percentile
        percentile = self._get_domain_percentile(domains)
        
        # Split into sentences
        sentences = [s.strip() for s in text.split('. ') if s.strip()]
        if sentences and not sentences[-1].endswith('.'):
            sentences[-1] += '.'  # Fix last sentence
        
        if len(sentences) < 2:
            # Too few sentences, return as single chunk
            return [TextChunk(
                id=0,
                start=0,
                end=len(text),
                text=text
            )]
        
        # Calculate all similarities and find percentile boundaries
        boundaries = self._find_percentile_boundaries(sentences, percentile)
        
        # Create chunks from boundaries
        return self._create_chunks(text, sentences, boundaries)
    
    def estimate_ram_usage(self, text_length: int) -> int:
        """
        Estimate RAM usage for percentile chunking
        
        Args:
            text_length: Length of text in characters
            
        Returns:
            Estimated RAM usage in bytes
        """
        # Estimate sentence count (rough: 50 chars per sentence)
        sentence_count = max(text_length // 50, 1)
        
        # Model size
        model_ram = 1000 * 1024 * 1024  # ~1GB for multilingual model
        
        # All sentence embeddings stored simultaneously
        embeddings_ram = sentence_count * 384 * 4  # sentences * 384 dims * 4 bytes
        
        # Similarity matrix (if we store it)
        similarities_ram = sentence_count * 8  # float64 per similarity
        
        # Processing overhead
        processing_overhead = 100 * 1024 * 1024  # 100MB
        
        return model_ram + embeddings_ram + similarities_ram + processing_overhead
    
    def _get_domain_percentile(self, domains: List[BaseNER] = None) -> float:
        """Get domain-specific percentile or use config default"""
        if domains and len(domains) > 0:
            domain_name = domains[0].config.name
            
            # Domain-specific percentile adjustments
            domain_percentiles = {
                "literary": 92.0,    # Less aggressive - preserve narrative flow
                "simple": 88.0,      # More aggressive for simple content
                "auto": 95.0         # Default
            }
            
            return domain_percentiles.get(domain_name, self.config.percentile)
        
        return self.config.percentile
    
    def _find_percentile_boundaries(self, sentences: List[str], percentile: float) -> List[int]:
        """
        Find chunk boundaries using percentile analysis
        
        Args:
            sentences: List of sentences
            percentile: Percentile threshold for cutting (e.g., 95.0)
            
        Returns:
            List of sentence indices where to cut
        """
        if len(sentences) < 2:
            return []
        
        print(f"🧠 Generating embeddings for {len(sentences)} sentences...")
        model = self._load_embedding_model()
        
        # Generate embeddings for all sentences
        embeddings = []
        print(f"🧠 Batch processing {len(sentences)} sentences...")
        embeddings = model.encode(sentences)  # ← BATCH!
        print(f"✅ Batch complete!")
        
        # Calculate similarities between consecutive sentences
        similarities = []
        for i in range(len(sentences) - 1):
            similarity = cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            similarities.append(similarity)
        
        # Convert similarities to distances (1 - similarity)
        distances = [1 - sim for sim in similarities]
        
        # Calculate percentile threshold
        if len(distances) == 0:
            return []
        
        threshold = np.percentile(distances, percentile)
        
        # Find boundaries where distance exceeds threshold
        boundaries = []
        for i, distance in enumerate(distances):
            if distance > threshold:
                # Cut after sentence i (before sentence i+1)
                boundary_idx = i + 1
                
                # Validate chunk size before adding boundary
                if self._should_add_boundary(sentences, boundaries, boundary_idx):
                    boundaries.append(boundary_idx)
        
        return boundaries
    
    def _should_add_boundary(self, sentences: List[str], existing_boundaries: List[int], 
                           new_boundary: int) -> bool:
        """
        Validate whether to add a new boundary based on chunk size constraints
        
        Args:
            sentences: All sentences
            existing_boundaries: Currently identified boundaries
            new_boundary: Proposed new boundary index
            
        Returns:
            True if boundary should be added
        """
        # Determine the start of the chunk that would be created
        if existing_boundaries:
            chunk_start = existing_boundaries[-1]
        else:
            chunk_start = 0
        
        # Check if resulting chunk meets size requirements
        chunk_sentences = sentences[chunk_start:new_boundary]
        chunk_text = ' '.join(chunk_sentences)
        
        # Validate chunk size
        chunk_size = len(chunk_text)
        if chunk_size < self.config.min_chunk_size:
            return False  # Chunk too small
        
        # Check remaining text after boundary
        remaining_sentences = sentences[new_boundary:]
        remaining_text = ' '.join(remaining_sentences)
        if len(remaining_text) < self.config.min_chunk_size:
            return False  # Would create too small final chunk
        
        return True
    
    def get_strategy_info(self) -> dict:
        """Return information about this strategy"""
        return {
            "name": "percentile",
            "description": "Global percentile-based semantic chunking",
            "memory_efficient": False,
            "streaming_capable": False,
            "domain_tunable": True,
            "percentile": self.config.percentile,
            "adaptive": True
        }