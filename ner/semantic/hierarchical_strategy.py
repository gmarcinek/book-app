"""
Generic Hierarchical Chunking Strategy
Uses LLM to find natural document sections like table of contents
"""

import json
from typing import List, Dict, Tuple
from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class HierarchicalChunker(SemanticChunkingStrategy):
    """
    Generic hierarchical chunking using LLM to find natural document sections
    """
    
    def __init__(self, config: SemanticChunkingConfig):
        super().__init__(config)
        self.llm_client = None
    
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        """Chunk text using LLM-guided section detection"""
        
        print(f"🏛️ HIERARCHICAL: Starting analysis for {len(text):,} chars")
        
        if not self.llm_client:
            self._initialize_llm()
        
        # Get sections from LLM
        sections = self._find_sections(text)
        
        if not sections:
            print(f"⚠️ HIERARCHICAL: No sections found, fallback to single chunk")
            return [TextChunk(0, 0, len(text), text)]
        
        # Create chunks from sections
        chunks = self._create_chunks_from_sections(text, sections)
        
        print(f"✅ HIERARCHICAL: Created {len(chunks)} chunks")
        return chunks
    
    def _initialize_llm(self):
        """Initialize LLM client"""
        try:
            from llm import LLMClient, Models
            self.llm_client = LLMClient(Models.GPT_4_1_NANO)
            print(f"🤖 HIERARCHICAL: Initialized LLM {Models.GPT_4_1_NANO}")
        except Exception as e:
            print(f"❌ HIERARCHICAL: Failed to initialize LLM: {e}")
            self.llm_client = None
    
    def _find_sections(self, text: str) -> List[Dict[str, str]]:
        """Find document sections using LLM"""
    
        prompt = f"""Jesteś algorytmem sekwencyjnego dzielenia tekstów na bloki tematyczne.

Twoja rola: Analizujesz dokument od początku do końca i wyznaczasz naturalne punkty podziału na sekcje, jak głowica czytająca taśmę.

Działasz jak parser - idziesz linia po linii i znajdujesz miejsca gdzie jeden temat się kończy a nowy zaczyna.

TEKST DO PODZIELENIA:
{text}

ALGORYTM:
1. Zacznij od początku tekstu
2. Idź sekwencyjnie w dół szukając naturalnych granic tematycznych  
3. Każda granica to początek nowej sekcji
4. Nie wracaj do tyłu, nie pomijaj fragmentów
5. Każda sekcja kończy się tam gdzie zaczyna następna

Myśl jak spis treści - każda pozycja to logiczna część dokumentu w naturalnej kolejności.

JSON (sekcje w kolejności wystąpienia):
{{
  "sections": [
    {{
      "start_text": "fragment początku pierwszej sekcji (unikalny w dokumencie)"
    }},
    {{
      "start_text": "fragment początku drugiej sekcji (dalej niż pierwsza)"
    }}
  ]
}}

Bądź jak parser: sekwencyjnie, bez skoków, bez powtórek."""
        
        try:
            from llm import LLMConfig
            config = LLMConfig(temperature=0.0)
            response = self.llm_client.chat(prompt, config)
            
            # Parse JSON response
            clean_response = response.strip()
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                parts = clean_response.split('```')
                if len(parts) >= 3:
                    clean_response = parts[1]
            
            data = json.loads(clean_response.strip())
            sections = data.get('sections', [])
            
            print(f"🎯 HIERARCHICAL: Found {len(sections)} sections")
            return sections
            
        except Exception as e:
            print(f"⚠️ HIERARCHICAL: Section detection failed: {e}")
            return []
    
    def _create_chunks_from_sections(self, text: str, sections: List[Dict[str, str]]) -> List[TextChunk]:
        """Create chunks from detected sections - sequential, no overlaps"""

        if not sections:
            return [TextChunk(0, 0, len(text), text)]

        # Find all section positions
        boundaries = []
        for section in sections:
            start_text = section.get('start_text', '')
            if not start_text:
                continue
            
            pos = text.find(start_text)
            if pos != -1:
                boundaries.append((pos, section))
                print(f"   🎯 Found section at {pos}: {start_text[:50]}...")

        if not boundaries:
            print(f"   ⚠️ No valid boundaries found")
            return [TextChunk(0, 0, len(text), text)]

        # Sort by position (sequential order)
        boundaries.sort(key=lambda x: x[0])

        # Remove duplicates (same position)
        unique_boundaries = []
        used_positions = set()
        for pos, section in boundaries:
            if pos not in used_positions:
                unique_boundaries.append((pos, section))
                used_positions.add(pos)

        print(f"   📋 Creating {len(unique_boundaries)} sequential chunks")

        # Create sequential chunks
        chunks = []
        for i, (start_pos, section) in enumerate(unique_boundaries):
            # End position is next section's start or document end
            if i + 1 < len(unique_boundaries):
                end_pos = unique_boundaries[i + 1][0]
            else:
                end_pos = len(text)
            
            # Extract chunk text
            chunk_text = text[start_pos:end_pos].strip()
            
            # Create chunk if large enough
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = TextChunk(
                    id=len(chunks),
                    start=start_pos,
                    end=end_pos,
                    text=chunk_text
                )
                chunks.append(chunk)
                print(f"   ✅ Chunk {len(chunks)-1}: {len(chunk_text):,} chars ({start_pos}-{end_pos})")
            else:
                print(f"   ⚠️ Skipped small chunk: {len(chunk_text)} chars < {self.config.min_chunk_size}")

        return chunks if chunks else [TextChunk(0, 0, len(text), text)]
    
    def estimate_ram_usage(self, text_length: int) -> int:
        """Estimate RAM usage"""
        return 50 * 1024 * 1024  # 50MB estimate
    
    def get_strategy_info(self) -> dict:
        """Return strategy information"""
        return {
            "name": "hierarchical",
            "description": "LLM-guided document section detection",
            "features": ["Table of contents style chunking", "Natural document boundaries"]
        }