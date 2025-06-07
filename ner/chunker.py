"""
NER Text Chunker - Intelligent text splitting with overlap
Memory-efficient chunking for large documents
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .utils import load_ner_config, log_memory_usage, validate_text_content


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
    Intelligent text chunker with configurable overlap
    
    Features:
    - Configurable chunk size and overlap
    - Memory-safe processing
    - Smart boundary detection (sentences, paragraphs)
    - Metadata preservation
    """
    
    def __init__(self, config_path: str = "ner/ner_config.json"):
        self.config = load_ner_config(config_path)
        self.chunk_size = self.config.get("chunk_size", 5000)
        self.overlap_size = self.config.get("chunk_overlap", 400)
        self.max_iterations = self.config.get("max_iterations", 100)
    
    def chunk_text(self, text: str, smart_boundaries: bool = True) -> List[TextChunk]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text to chunk
            smart_boundaries: Try to break at sentence/paragraph boundaries
            
        Returns:
            List of TextChunk objects
        """
        if not validate_text_content(text):
            return []
        
        log_memory_usage("Chunking start")
        
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
                log_memory_usage(f"Processed {i+1} chunks")
            
            # If we've covered the whole text, stop
            if end >= text_len:
                break
        
        log_memory_usage(f"Chunking complete: {len(chunks)} chunks")
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
        para_breaks = []
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
            "config_used": {
                "chunk_size": self.chunk_size,
                "overlap_size": self.overlap_size,
                "max_iterations": self.max_iterations
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