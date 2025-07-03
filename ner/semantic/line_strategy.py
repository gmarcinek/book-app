"""
Line-based Chunking Strategy - ULTRA SIMPLE VERSION
Plik: ner/semantic/line_strategy.py
"""

from typing import List
from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class LineChunker(SemanticChunkingStrategy):
    """
    Ultra simple line-based chunking strategy
    
    Dzieli tekst co 10 linii. Koniec. Bez validacji, bez łączenia, bez gadania.
    """
    
    def __init__(self, config: SemanticChunkingConfig, lines_per_chunk: int = 10):
        super().__init__(config)
        self.lines_per_chunk = lines_per_chunk
        
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        """Chunk text by splitting every N lines. ULTRA SIMPLE."""
        
        # Podziel tekst na linie
        lines = text.split('\n')
        
        print(f"📄 Dzielę tekst na chunki po {self.lines_per_chunk} linii ({len(lines)} linii total)")
        
        # Utwórz chunki - bez walidacji, bez łączenia, bez myślenia
        chunks = []
        chunk_id = 0
        
        for i in range(0, len(lines), self.lines_per_chunk):
            # Pobierz linie dla tego chunka
            chunk_lines = lines[i:i + self.lines_per_chunk]
            chunk_text = '\n'.join(chunk_lines)
            
            # Znajdź pozycję początkową w oryginalnym tekście
            start_pos = self._find_start_position(text, lines, i)
            end_pos = start_pos + len(chunk_text)
            
            # Dodaj chunk - bez walidacji!
            chunks.append(TextChunk(
                id=chunk_id,
                start=start_pos,
                end=end_pos,
                text=chunk_text
            ))
            chunk_id += 1
        
        print(f"✅ Utworzono {len(chunks)} chunków")
        return chunks
    
    def estimate_ram_usage(self, text_length: int) -> int:
        """Oszacuj zużycie RAM - bardzo mało"""
        return text_length * 3  # Bardzo konserwatywne oszacowanie
    
    def _find_start_position(self, text: str, lines: List[str], line_index: int) -> int:
        """Znajdź pozycję początkową chunka w oryginalnym tekście"""
        if line_index == 0:
            return 0
        
        # Zlicz długość poprzednich linii + znaki nowej linii
        position = 0
        for i in range(line_index):
            position += len(lines[i]) + 1  # +1 dla \n
        
        return position
    
    def get_strategy_info(self) -> dict:
        """Zwróć informacje o tej strategii"""
        return {
            "name": "line",
            "description": f"Ultra simple line chunking every {self.lines_per_chunk} lines",
            "memory_efficient": True,
            "streaming_capable": True,
            "lines_per_chunk": self.lines_per_chunk,
            "validation": False,  # Bez walidacji!
            "merging": False,     # Bez łączenia!
            "embedding_model": None,
            "caching": False
        }