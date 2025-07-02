"""
Line-based Chunking Strategy
"""

import numpy as np
from typing import List

from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class LineChunker(SemanticChunkingStrategy):
    """
    Line-based chunking strategy that splits text every N lines
    
    Simple, fast strategy that cuts text at line boundaries.
    Useful for structured documents, logs, or when semantic analysis
    is not needed.
    """
    
    def __init__(self, config: SemanticChunkingConfig, lines_per_chunk: int = 10):
        super().__init__(config)
        self.lines_per_chunk = lines_per_chunk
        
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        """Chunk text by splitting every N lines"""
        
        # Dostosuj liczbę linii na podstawie domeny
        lines_per_chunk = self._get_domain_lines_per_chunk(domains)
        
        # Podziel tekst na linie
        lines = text.split('\n')
        
        if len(lines) <= lines_per_chunk:
            # Za mało linii, zwróć jako jeden chunk
            return [TextChunk(
                id=0,
                start=0,
                end=len(text),
                text=text
            )]
        
        print(f"📄 Dzielę tekst na chunki po {lines_per_chunk} linii ({len(lines)} linii total)")
        
        # Utwórz chunki
        chunks = []
        chunk_id = 0
        
        for i in range(0, len(lines), lines_per_chunk):
            # Pobierz linie dla tego chunka
            chunk_lines = lines[i:i + lines_per_chunk]
            chunk_text = '\n'.join(chunk_lines)
            
            # Znajdź pozycję początkową w oryginalnym tekście
            start_pos = self._find_start_position(text, lines, i)
            end_pos = start_pos + len(chunk_text)
            
            # Sprawdź czy chunk spełnia wymagania rozmiaru
            if self._validate_chunk_size(chunk_text):
                chunks.append(TextChunk(
                    id=chunk_id,
                    start=start_pos,
                    end=end_pos,
                    text=chunk_text
                ))
                chunk_id += 1
            else:
                # Chunk za mały - dołącz do poprzedniego lub utwórz minimalny
                if chunks:
                    # Dołącz do ostatniego chunka
                    last_chunk = chunks[-1]
                    combined_text = last_chunk.text + '\n' + chunk_text
                    chunks[-1] = TextChunk(
                        id=last_chunk.id,
                        start=last_chunk.start,
                        end=start_pos + len(chunk_text),
                        text=combined_text
                    )
                else:
                    # Pierwszy chunk - zachowaj mimo że mały
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
        """Oszacuj zużycie RAM dla line chunking"""
        # Bardzo mało RAM - tylko podzielenie na linie
        line_count = max(text_length // 50, 1)  # Założenie ~50 znaków na linię
        
        # RAM dla przechowania linii
        lines_ram = text_length * 2  # Duplikacja dla split()
        
        # RAM dla chunków
        chunks_ram = text_length  # Referencje do części tekstu
        
        # Overhead przetwarzania
        processing_overhead = 10 * 1024 * 1024  # 10MB
        
        return lines_ram + chunks_ram + processing_overhead
    
    def _get_domain_lines_per_chunk(self, domains: List[BaseNER] = None) -> int:
        """Dostosuj liczbę linii na chunk w zależności od domeny"""
        if domains and len(domains) > 0:
            domain_name = domains[0].config.name
            
            # Dostosowania dla różnych domen
            domain_line_settings = {
                "literary": 15,      # Więcej linii dla literatury
                "simple": 8,         # Mniej linii dla prostych tekstów
                "financial": 12,     # Średnio dla dokumentów finansowych
                "code": 20,          # Więcej linii dla kodu
                "log": 50,           # Dużo więcej dla logów
                "auto": 10           # Domyślnie
            }
            
            return domain_line_settings.get(domain_name, self.lines_per_chunk)
        
        return self.lines_per_chunk
    
    def _find_start_position(self, text: str, lines: List[str], line_index: int) -> int:
        """Znajdź pozycję początkową chunka w oryginalnym tekście"""
        if line_index == 0:
            return 0
        
        # Zlicz długość poprzednich linii + znaki nowej linii
        position = 0
        for i in range(line_index):
            position += len(lines[i]) + 1  # +1 dla \n
        
        return position
    
    def _validate_chunk_size(self, chunk_text: str) -> bool:
        """Sprawdź czy chunk spełnia wymagania rozmiaru"""
        chunk_size = len(chunk_text.strip())
        
        # Sprawdź minimalny rozmiar
        if chunk_size < self.config.min_chunk_size:
            return False
        
        # Sprawdź maksymalny rozmiar (jeśli skonfigurowany)
        if hasattr(self.config, 'max_chunk_size') and self.config.max_chunk_size:
            if chunk_size > self.config.max_chunk_size:
                return False
        
        return True
    
    def get_strategy_info(self) -> dict:
        """Zwróć informacje o tej strategii"""
        return {
            "name": "line",
            "description": f"Line-based chunking splitting every {self.lines_per_chunk} lines",
            "memory_efficient": True,   # Bardzo mało RAM
            "streaming_capable": True,  # Można streamować
            "domain_tunable": True,     # Dostosowywalne do domeny
            "lines_per_chunk": self.lines_per_chunk,
            "adaptive": True,           # Dostosowuje się do domeny
            "embedding_model": None,    # Nie używa embeddings
            "caching": False           # Nie potrzebuje cache
        }