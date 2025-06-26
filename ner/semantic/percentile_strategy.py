"""
Percentile-based Semantic Chunking Strategy with OpenAI embeddings
"""

import numpy as np
from typing import List

from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class PercentileChunker(SemanticChunkingStrategy):
    """
    Percentile-based semantic chunking strategy using OpenAI embeddings
    
    Calculates similarity between all consecutive sentences, then cuts
    at points where similarity is below specified percentile threshold.
    Domain-agnostic approach that adapts to document characteristics.
    """
    
    def __init__(self, config: SemanticChunkingConfig):
        super().__init__(config)
        
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        # Chunk text using percentile-based semantic analysis with OpenAI embeddings
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
        # Estimate RAM usage for percentile chunking with OpenAI embeddings
        sentence_count = max(text_length // 50, 1)
        
        # OpenAI embeddings are generated via API - minimal local RAM
        api_overhead = 50 * 1024 * 1024  # 50MB for API client
        
        # Embeddings stored temporarily (1536 dims * 4 bytes)
        embeddings_ram = sentence_count * 1536 * 4
        
        # Similarity matrix
        similarities_ram = sentence_count * 8
        
        # Processing overhead
        processing_overhead = 100 * 1024 * 1024  # 100MB
        
        return api_overhead + embeddings_ram + similarities_ram + processing_overhead
    
    def _get_domain_percentile(self, domains: List[BaseNER] = None) -> float:
        # Get domain-specific percentile or use config default
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
        # Find chunk boundaries using percentile analysis with OpenAI embeddings
        if len(sentences) < 2:
            return []
        
        print(f"🧠 Generating embeddings for {len(sentences)} sentences...")
        client = self._load_embeddings_client()  # ← FIXED: use correct method name
        
        # Generate embeddings for all sentences using batch API
        print(f"🧠 Batch processing {len(sentences)} sentences...")
        embeddings = client.embed_batch(sentences)  # ← FIXED: use OpenAI client
        print(f"✅ Batch complete!")
        
        # Calculate similarities between consecutive sentences
        similarities = []
        for i in range(len(sentences) - 1):
            similarity = client.compute_similarity(embeddings[i], embeddings[i + 1])
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
        # Validate whether to add a new boundary based on chunk size constraints
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
        # Return information about this strategy
        return {
            "name": "percentile",
            "description": "Global percentile-based semantic chunking with OpenAI embeddings",
            "memory_efficient": True,  # API-based, minimal local RAM
            "streaming_capable": False,
            "domain_tunable": True,
            "percentile": self.config.percentile,
            "adaptive": True,
            "embedding_model": self.config.model_name
        }