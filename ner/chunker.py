"""
NER Text Chunker - Intelligent text splitting with model-aware sizing
Memory-efficient chunking for large documents with automatic chunk size calculation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .utils import log_memory_usage, validate_text_content
from .config import NERConfig, create_default_ner_config
from llm.models import Models, get_model_input_limit


@dataclass
class TextChunk:
    """Represents a text chunk with metadata"""
    id: int
    start: int
    end: int
    text: str
    overlap_start: bool = False  # True if this chunk starts with overlap
    overlap_end: bool = False    # True if this chunk ends with overlap


class TextChunker:
    """
    Intelligent text chunker with model-aware sizing
    
    Features:
    - Auto-calculates chunk size based on model input limits
    - Accounts for real meta-prompt overhead from domains
    - Memory-safe processing
    - Smart boundary detection (sentences, paragraphs)
    """
    
    def __init__(self, 
                 config: Optional[NERConfig] = None, 
                 model_name: str = None, 
                 domains: List = None):
        """
        Initialize chunker with model-aware configuration
        
        Args:
            config: NERConfig object with chunking settings, creates default if None
            model_name: LLM model name for auto-sizing (defaults to GPT_4O_MINI)
            domains: List of domain objects for overhead calculation
        """
        self.config = config if config is not None else create_default_ner_config()
        self.model_name = model_name or Models.GPT_4O_MINI
        self.domains = domains or []
        
        # Calculate REAL meta-prompt overhead from domains
        self.meta_overhead = self._calculate_meta_overhead()
        
        # Smart chunk size based on model input limits and actual overhead
        model_input_limit = get_model_input_limit(self.model_name)
        self.chunk_size = int((model_input_limit - self.meta_overhead) * 0.75)
        
        # Use config overlap or calculate based on chunk size
        self.overlap_size = self.config.get_chunk_overlap()
        if self.overlap_size <= 0:
            self.overlap_size = min(400, self.chunk_size // 10)  # 10% or 400, whichever smaller
        
        self.max_iterations = self.config.get_max_iterations()
        
        # Import here to avoid circular imports
        from llm.models import get_model_output_limit
        model_output_limit = get_model_output_limit(self.model_name)
        
        log_memory_usage(f"🧠 Chunker: {self.model_name} | IN:{model_input_limit} OUT:{model_output_limit} | chunk:{self.chunk_size} overhead:{self.meta_overhead}")
    
    def _calculate_meta_overhead(self) -> int:
        """
        Calculate REAL meta-prompt overhead from domain strategies
        
        Returns:
            Estimated tokens needed for meta-prompts + formatting buffer
        """
        if not self.domains:
            return 1500  # reasonable fallback when no domains
        
        sample_text = "Sample text for meta-prompt overhead calculation."
        max_overhead = 0
        
        for domain in self.domains:
            try:
                # Get actual meta-prompt from domain
                meta_prompt = domain.get_meta_analysis_prompt(sample_text)
                
                # Token estimation: words * 1.33 (based on OpenAI research)
                # This is more accurate than character-based estimation
                word_count = len(meta_prompt.split())
                estimated_tokens = int(word_count * 1.33)
                
                max_overhead = max(max_overhead, estimated_tokens)
                
            except Exception as e:
                # If domain fails, use safe fallback
                max_overhead = max(max_overhead, 1500)
                log_memory_usage(f"⚠️ Domain overhead calculation failed: {e}")
        
        # Add buffer for JSON formatting, instructions, etc.
        total_overhead = max_overhead + 300
        
        log_memory_usage(f"📊 Meta-prompt overhead: {total_overhead} tokens (from {len(self.domains)} domains)")
        return total_overhead
    
    def chunk_text(self, text: str, smart_boundaries: bool = True) -> List[TextChunk]:
        """
        Split text into overlapping chunks with model-aware sizing
        
        Args:
            text: Input text to chunk
            smart_boundaries: Try to break at sentence/paragraph boundaries
            
        Returns:
            List of TextChunk objects
        """
        if not validate_text_content(text):
            return []
        
        log_memory_usage("🔄 Chunking start")
        
        text_len = len(text)
        chunks = []
        
        # Safety limit
        max_chunks = min(self.max_iterations, 
                        (text_len // (self.chunk_size - self.overlap_size)) + 1)
        
        for i in range(max_chunks):
            # Calculate chunk boundaries
            start = i * (self.chunk_size - self.overlap_size)
            if start >= text_len:
                break
            
            end = min(start + self.chunk_size, text_len)
            
            # Smart boundary adjustment
            if smart_boundaries and end < text_len:
                end = self._find_smart_boundary(text, start, end)
            
            # Extract chunk text
            chunk_text = text[start:end]
            
            # Create chunk object
            chunk = TextChunk(
                id=i,
                start=start,
                end=end,
                text=chunk_text,
                overlap_start=(i > 0),  # All chunks except first have overlap at start
                overlap_end=(end < text_len)  # All chunks except last have overlap at end
            )
            
            chunks.append(chunk)
            
            # Memory check every 10 chunks
            if (i + 1) % 10 == 0:
                log_memory_usage(f"📊 Processed {i+1} chunks")
            
            # If we've covered the whole text, stop
            if end >= text_len:
                break
        
        log_memory_usage(f"✅ Chunking complete: {len(chunks)} chunks (avg size: {sum(len(c.text) for c in chunks)//len(chunks) if chunks else 0})")
        return chunks
    
    def _find_smart_boundary(self, text: str, start: int, proposed_end: int) -> int:
        """
        Find a smart boundary near the proposed end position
        Try to break at sentence or paragraph boundaries
        """
        # Look back from proposed_end for good break points
        search_start = max(proposed_end - 200, start + self.chunk_size // 2)
        search_text = text[search_start:proposed_end + 100]  # Small buffer forward
        
        # Priority order: paragraph > sentence > word boundary
        boundaries = []
        
        # Look for paragraph breaks (double newline)
        pos = 0
        while True:
            pos = search_text.find('\n\n', pos)
            if pos == -1:
                break
            boundaries.append(('paragraph', search_start + pos + 2))
            pos += 2
        
        # Look for sentence breaks
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        for ending in sentence_endings:
            pos = 0
            while True:
                pos = search_text.find(ending, pos)
                if pos == -1:
                    break
                boundaries.append(('sentence', search_start + pos + len(ending)))
                pos += len(ending)
        
        # Look for word boundaries (spaces)
        pos = search_text.rfind(' ', 0, proposed_end - search_start)
        if pos != -1:
            boundaries.append(('word', search_start + pos + 1))
        
        # Sort boundaries by position
        boundaries.sort(key=lambda x: x[1])
        
        # Find the best boundary close to proposed_end
        best_boundary = proposed_end
        for boundary_type, boundary_pos in boundaries:
            if boundary_pos <= proposed_end and boundary_pos > start + self.chunk_size // 2:
                best_boundary = boundary_pos
        
        return min(best_boundary, len(text))
    
    def get_chunk_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about the chunks"""
        if not chunks:
            return {"total_chunks": 0}
        
        chunk_sizes = [len(chunk.text) for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "total_text_length": sum(chunk_sizes),
            "avg_chunk_size": sum(chunk_sizes) / len(chunks),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "overlapping_chunks": sum(1 for chunk in chunks if chunk.overlap_start or chunk.overlap_end),
            "model_config": {
                "model_name": self.model_name,
                "model_input_limit": get_model_input_limit(self.model_name),
                "calculated_chunk_size": self.chunk_size,
                "meta_overhead": self.meta_overhead,
                "overlap_size": self.overlap_size,
            }
        }
    
    def chunk_to_dict(self, chunk: TextChunk) -> Dict[str, Any]:
        """Convert TextChunk to dictionary for serialization"""
        return {
            "id": chunk.id,
            "start": chunk.start,
            "end": chunk.end,
            "text_length": len(chunk.text),
            "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text,
            "overlap_start": chunk.overlap_start,
            "overlap_end": chunk.overlap_end
        }
    
    def get_overlap_region(self, chunk1: TextChunk, chunk2: TextChunk) -> Optional[str]:
        """Get overlapping text between two consecutive chunks"""
        if chunk2.id != chunk1.id + 1:
            return None
        
        # Overlap is from chunk2.start to chunk1.end
        if chunk2.start < chunk1.end:
            overlap_start = chunk2.start
            overlap_end = min(chunk1.end, chunk2.end)
            return chunk1.text[overlap_start - chunk1.start:overlap_end - chunk1.start]
        
        return None