"""
Semantic Chunking Base Classes and Enums (OpenAI embeddings)
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List
from dataclasses import dataclass

# Import from parent modules
from ..domains import BaseNER
from ..config import ChunkingStrategy

@dataclass
class TextChunk:
   """Represents a text chunk with metadata"""
   id: int
   start: int
   end: int
   text: str
   overlap_start: bool = False  # True if this chunk starts with overlap
   overlap_end: bool = False    # True if this chunk ends with overlap

@dataclass
class SemanticChunkingConfig:
   """Configuration for semantic chunking with OpenAI embeddings"""
   strategy: ChunkingStrategy = ChunkingStrategy.PERCENTILE
   model_name: str = "text-embedding-3-small"  # OpenAI embeddings model
   percentile: float = 95.0  # For percentile strategy
   min_chunk_size: int = 100  # Minimum characters per chunk
   max_chunk_size: int = 100000  # Maximum characters per chunk


class SemanticChunkingStrategy(ABC):
   """Abstract base class for semantic chunking strategies using OpenAI embeddings"""
   
   def __init__(self, config: SemanticChunkingConfig):
       self.config = config
       self._embeddings_client = None
       
   @abstractmethod
   def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
       """
       Chunk text using semantic analysis with OpenAI embeddings
       
       Args:
           text: Input text to chunk
           domains: Optional domain information for domain-specific tuning
           
       Returns:
           List of TextChunk objects
       """
       pass
   
   @abstractmethod
   def estimate_ram_usage(self, text_length: int) -> int:
       """
       Estimate RAM usage in bytes for processing text of given length
       
       Args:
           text_length: Length of text in characters
           
       Returns:
           Estimated RAM usage in bytes
       """
       pass
   
   def _load_embeddings_client(self):
       """Lazy load OpenAI embeddings client"""
       if self._embeddings_client is None:
           try:
               print(f"📥 Loading OpenAI embeddings client: {self.config.model_name}...")
               from llm.embeddings_client import OpenAIEmbeddingsClient
               self._embeddings_client = OpenAIEmbeddingsClient(self.config.model_name)
               print(f"✅ OpenAI embeddings client loaded!")
           except ImportError:
               raise ImportError("OpenAI embeddings client required for semantic chunking")
       return self._embeddings_client
   
   def _create_chunks(self, text: str, sentences: List[str], boundaries: List[int]) -> List[TextChunk]:
       """Create TextChunk objects from sentence boundaries"""
       if not boundaries:
           # No boundaries found, return single chunk
           return [TextChunk(
               id=0,
               start=0,
               end=len(text),
               text=text
           )]
       
       chunks = []
       chunk_id = 0
       
       # Add boundary at start and end
       all_boundaries = [0] + boundaries + [len(sentences)]
       
       for i in range(len(all_boundaries) - 1):
           start_sentence = all_boundaries[i]
           end_sentence = all_boundaries[i + 1]
           
           # Get chunk sentences
           chunk_sentences = sentences[start_sentence:end_sentence]
           chunk_text = ' '.join(chunk_sentences)
           
           # Validate chunk size
           if (len(chunk_text) >= self.config.min_chunk_size and 
               len(chunk_text) <= self.config.max_chunk_size):
               
               # Find character positions in original text
               start_pos = text.find(chunk_sentences[0]) if chunk_sentences else 0
               end_pos = start_pos + len(chunk_text) if chunk_text else start_pos
               
               chunks.append(TextChunk(
                   id=chunk_id,
                   start=start_pos,
                   end=end_pos,
                   text=chunk_text
               ))
               chunk_id += 1
       
       return chunks if chunks else [TextChunk(0, 0, len(text), text)]