"""
Simplified Hierarchical Chunking Strategy for Legal Documents (OWU)
Uses LLM for smart detection of sections, tables, and attachments
Enhanced with context-aware boundary detection

FILE: ner/semantic/hierarchical_strategy.py
"""

import re
import json
from typing import List, Dict, Tuple, Any, Optional
from .base import SemanticChunkingStrategy, SemanticChunkingConfig, TextChunk
from ..domains import BaseNER


class HierarchicalChunker(SemanticChunkingStrategy):
    """
    Simplified Hierarchical chunking strategy for Polish legal documents
    
    1. LLM analyzes entire document structure
    2. Finds boundaries for sections, tables, attachments
    3. Uses context-aware search to resolve ambiguous positions
    4. Intelligently preserves table/attachment integrity
    5. Creates chunks respecting document logic
    """
    
    def __init__(self, config: SemanticChunkingConfig):
        super().__init__(config)
        self.llm_client = None
        self._last_llm_response = ""
        
    def _get_llm_client(self):
        """Get LLM client, initialize if needed"""
        if not self.llm_client:
            try:
                from llm import LLMClient, Models
                self.llm_client = LLMClient(Models.GPT_4_1_NANO)
                print(f"🤖 HIERARCHICAL: Initialized LLM client with {Models.GPT_4_1_NANO}")
            except Exception as e:
                print(f"💥 HIERARCHICAL: Failed to initialize LLM: {e}")
                raise
        return self.llm_client
    
    def chunk(self, text: str, domains: List[BaseNER] = None) -> List[TextChunk]:
        """Chunk text using simplified hierarchical approach"""
        
        print(f"🏛️ HIERARCHICAL: Starting analysis for {len(text):,} chars")
        
        try:
            llm_client = self._get_llm_client()
        except Exception as e:
            print(f"⚠️ HIERARCHICAL: LLM initialization failed, falling back to semantic chunking")
            return self._fallback_semantic_chunk(text)
        
        # Phase 1: Analyze document structure with LLM
        structure = self._analyze_document_structure(text)
        
        # Phase 2: Extract boundaries using context-aware search
        boundaries = self._extract_boundaries(text, structure)
        
        if not boundaries:
            print(f"⚠️ HIERARCHICAL: No boundaries found, falling back to semantic chunking")
            return self._fallback_semantic_chunk(text)
        
        print(f"📋 HIERARCHICAL: Found {len(boundaries)} boundaries")
        
        # Phase 3: Create chunks
        chunks = self._create_chunks(text, boundaries)
        
        # Phase 4: Handle oversized chunks
        final_chunks = self._handle_oversized_chunks(chunks)
        
        print(f"✅ HIERARCHICAL: Created {len(final_chunks)} chunks")
        return final_chunks
    
    def set_llm_client(self, llm_client):
        """Inject LLM client"""
        self.llm_client = llm_client
    
    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure using LLM"""
        
        print(f"🔍 HIERARCHICAL: Analyzing document structure...")
        
        prompt = f"""Przeanalizuj strukturę polskiego dokumentu prawnego/OWU i znajdź DWA POZIOMY podziału:

DOKUMENT:
{text}

ZADANIE:
0. Sklasyfikuj zawartość tak żeby wyodrębnić bloki tematyczne. Masz za zadanie odnaleźć rozdziały, sekcje i załączniki oraz sklasyfikować je jako odrębne całosci. 
1. POZIOM GŁÓWNY: Znajdź podstawową strukturę hierarchiczną (Artykuły, Rozdziały, Paragrafy)
2. POZIOM RÓWNOLEGŁY: Znajdź rzeczy "obok" hierarchii (Załączniki, Tabele, Schematy)
3. Poziomów równoległych szukaj od końca a struktury rozdziałowej od początku.

POZIOM GŁÓWNY (normalna struktura dokumentu):
- Art. 1, Art. 2, Art. 3, Artykuł X...
- Rozdział I, Rozdział II, Rozdział 3, Rozdz. 4...  
- § 1, § 2, § 3...
- Wszystkie elementy podstawowej hierarchii
- UWAGA - nie odcinaj rozdziału jeśli w hierarchi znajdujesz tylko odniesienie do równoległej struktury

POZIOM RÓWNOLEGŁY (rzeczy obok głównej struktury):
- Załączniki z tabelami (A. Uszkodzenia głowy, B. Uszkodzenia twarzy...)
- Wykazy z procentami, kwotami
- Schematy, formularze, procedury
- Struktury z numeracją ale NIE będące częścią artykułów

UWAGA:
- NIE pomijaj artykułów/rozdziałów bo skupiasz się na załącznikach!
- Znajdź WSZYSTKIE Art./Rozdz. PLUS wszystkie załączniki
- Definicje pojęć (24. uszkodzenie ciała...) to NIE tabela!
- Użyj PRECYZYJNYCH tekstów startowych - nie ogólnych nazw!

ZWRÓĆ JSON:
{{
  "boundaries": [
    {{
      "start_text": "DOKŁADNY tekst od którego zaczyna się sekcja - nie skracaj!",
      "type": "article" | "chapter" | "attachment" | "table" | "section",
      "description": "krótki opis co to za sekcja",
      "keep_intact": true | false
    }}
  ]
}}

TYLKO JSON:"""
        
        try:
            llm_client = self._get_llm_client()
            response = llm_client.chat(prompt)
            
            # Parse response
            clean_response = response.strip()
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                parts = clean_response.split('```')
                if len(parts) >= 3:
                    clean_response = parts[1]
            
            data = json.loads(clean_response.strip())
            
            if not isinstance(data, dict) or 'boundaries' not in data:
                raise ValueError("Invalid JSON structure")
            
            print(f"🎯 HIERARCHICAL: Found {len(data['boundaries'])} boundary markers")
            return data
            
        except Exception as e:
            print(f"⚠️ HIERARCHICAL: LLM analysis failed: {e}")
            return {"boundaries": []}
    
    def _extract_boundaries(self, text: str, structure: Dict[str, Any]) -> List[Tuple[int, str, str, bool]]:
        """
        Extract actual boundaries from LLM analysis using context-aware search
        Returns: (position, type, description, keep_intact)
        """
        
        boundaries = []
        used_positions = set()  # Track used positions to avoid duplicates
        
        for boundary_info in structure.get("boundaries", []):
            start_text = boundary_info.get("start_text", "")
            boundary_type = boundary_info.get("type", "section")
            description = boundary_info.get("description", "")
            keep_intact = boundary_info.get("keep_intact", False)
            
            if start_text:
                # Find ALL occurrences of this text
                positions = self._find_all_occurrences(text, start_text)
                
                # Choose the best position based on context
                best_pos = self._choose_best_position(
                    text, start_text, positions, boundary_type, used_positions
                )
                
                if best_pos != -1:
                    boundaries.append((best_pos, boundary_type, description, keep_intact))
                    used_positions.add(best_pos)
                    print(f"   ✅ Found {boundary_type}: {description} at position {best_pos}")
                else:
                    print(f"   ⚠️ Could not find good position for: {start_text[:50]}...")
        
        # Sort by position and deduplicate
        boundaries.sort(key=lambda x: x[0])
        boundaries = self._deduplicate_boundaries(boundaries)
        
        return boundaries
    
    def _find_all_occurrences(self, text: str, search_text: str) -> List[int]:
        """Find all occurrences of search_text in text"""
        positions = []
        start = 0
        
        while True:
            pos = text.find(search_text, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        return positions
    
    def _choose_best_position(self, text: str, search_text: str, positions: List[int], 
                         boundary_type: str, used_positions: set) -> int:
        """
        Choose the best position for boundary based on context analysis
        """
        
        if not positions:
            return -1
        
        if len(positions) == 1:
            return positions[0] if positions[0] not in used_positions else -1
        
        print(f"   🔍 Multiple matches for '{search_text[:30]}...': {len(positions)} found")
        
        best_pos = -1
        best_score = -1
        
        for pos in positions:
            if pos in used_positions:
                continue
                
            score = self._score_position_context(text, pos, search_text, boundary_type)
            print(f"      Position {pos}: score {score:.2f}")
            
            if score > best_score:
                best_score = score
                best_pos = pos
        
        return best_pos
    
    def _score_position_context(self, text: str, pos: int, search_text: str, 
                           boundary_type: str) -> float:
        """
        Score a position based on its context - higher score = better match
        """
        
        score = 0.0
        
        # Context window around the position
        context_start = max(0, pos - 500)
        context_end = min(len(text), pos + len(search_text) + 500)
        context = text[context_start:context_end]
        
        # Line context - text around the exact line
        line_start = text.rfind('\n', context_start, pos) + 1
        line_end = text.find('\n', pos + len(search_text))
        if line_end == -1:
            line_end = len(text)
        line_context = text[line_start:line_end]
        
        # SCORING RULES based on boundary type
        
        if boundary_type == "article":
            # Articles should start at beginning of line
            if pos == line_start or text[pos-1] in '\n\r':
                score += 10.0
            
            # Articles should have "Artykuł" pattern
            if re.match(r'^\s*Artykuł\s+\d+', line_context.strip()):
                score += 15.0
            
            # Avoid articles inside definitions or references
            if any(ref_word in context.lower() for ref_word in [
                'definicje', 'oznacza', 'wskazane w', 'zgodnie z', 'określone w'
            ]):
                score -= 20.0
                
        elif boundary_type == "table":
            # Tables should NOT be inside article definitions
            if any(def_word in context.lower() for def_word in [
                'definicje', 'oznacza', 'wskazane w', 'stanowi załącznik'
            ]):
                score -= 30.0  # Heavy penalty for references
                
            # Tables should be standalone sections
            if pos == line_start or text[pos-1] in '\n\r':
                score += 10.0
                
            # Look for actual table content AFTER the boundary (not before!)
            table_pattern = re.compile(r'[A-Z]\.\s+[A-ZĄĆĘŁŃÓŚŹŻ]', re.MULTILINE)
            boundary_pos_in_context = pos - context_start
            
            # Only search AFTER the boundary position
            context_after = context[boundary_pos_in_context:]
            table_matches = list(table_pattern.finditer(context_after))
            
            if table_matches:
                content_score = 0
                
                for match in table_matches:
                    distance_to_content = match.start()  # Distance from boundary
                    
                    # Content should be CLOSE AFTER boundary, not far
                    if distance_to_content <= 50:
                        content_score += 30.0  # Very close after
                    elif distance_to_content <= 200:
                        content_score += 15.0  # Close after
                    elif distance_to_content <= 500:
                        content_score += 5.0   # Nearby after
                    # No score for content far away
                    
                # Bonus for multiple table entries (richer content)
                if len(table_matches) >= 5:
                    content_score += 15.0
                elif len(table_matches) >= 3:
                    content_score += 8.0
                    
                score += content_score
                
            # Tables should be after articles (high position in document)
            doc_position_ratio = pos / len(text)
            if doc_position_ratio > 0.5:  # In second half of document
                score += 15.0
            else:
                score -= 10.0  # Penalty for early position
                
        elif boundary_type == "attachment":
            # Attachments usually at the end
            doc_position_ratio = pos / len(text)
            if doc_position_ratio > 0.8:  # In last 20% of document
                score += 25.0  # Strong bonus for end position
            elif doc_position_ratio > 0.6:  # In last 40% of document  
                score += 10.0
            else:
                score -= 15.0  # Penalty for early position
        
        # GENERAL RULES
        
        # Prefer positions that start new sections (after double newline)
        if '\n\n' in text[max(0, pos-10):pos]:
            score += 5.0
        
        # Avoid positions inside parentheses or quotes
        paren_count = context[:pos-context_start].count('(') - context[:pos-context_start].count(')')
        if paren_count > 0:
            score -= 10.0
        
        # Prefer positions with proper capitalization
        if search_text and search_text[0].isupper():
            score += 2.0
        
        # Avoid positions that are clearly in the middle of sentences
        before_char = text[pos-1] if pos > 0 else '\n'
        if before_char.islower():
            score -= 15.0
        
        return score
    
    def _deduplicate_boundaries(self, boundaries: List[Tuple[int, str, str, bool]]) -> List[Tuple[int, str, str, bool]]:
        """
        Remove boundaries that are too close to each other
        Enhanced with type-aware logic and better debugging
        """
        
        if not boundaries:
            return boundaries
        
        print(f"🔧 DEDUPLICATION: Processing {len(boundaries)} boundaries...")
        
        # Debug: show all boundaries first
        for i, (pos, btype, desc, keep_intact) in enumerate(boundaries):
            print(f"   {i+1:2d}. pos={pos:6d} type={btype:10s} desc={desc[:40]}...")
        
        deduplicated = [boundaries[0]]
        print(f"   ✅ Keeping boundary 1: pos={boundaries[0][0]} type={boundaries[0][1]}")
        
        for i, boundary in enumerate(boundaries[1:], 2):
            pos, btype, desc, keep_intact = boundary
            last_pos, last_type, last_desc, last_keep_intact = deduplicated[-1]
            
            distance = pos - last_pos
            
            # SMART DEDUPLICATION RULES
            should_keep = False
            reason = ""
            
            # Rule 1: Always keep if far enough apart
            if distance >= 100:
                should_keep = True
                reason = f"far enough ({distance} chars)"
                
            # Rule 2: Keep if different types, even if close
            elif btype != last_type:
                # Special case: table + attachment are related, use smaller threshold
                if {btype, last_type} == {"table", "attachment"}:
                    if distance >= 20:  # Very small threshold for table sections
                        should_keep = True
                        reason = f"different types table/attachment ({distance} chars)"
                    else:
                        reason = f"too close even for table/attachment ({distance} chars)"
                else:
                    # Other type combinations - medium threshold
                    if distance >= 50:
                        should_keep = True
                        reason = f"different types {last_type}->{btype} ({distance} chars)"
                    else:
                        reason = f"different types but too close ({distance} chars)"
                        
            # Rule 3: Keep if one is marked as keep_intact
            elif keep_intact or last_keep_intact:
                if distance >= 30:
                    should_keep = True
                    reason = f"keep_intact flag ({distance} chars)"
                else:
                    reason = f"keep_intact but too close ({distance} chars)"
                    
            # Rule 4: Skip if same type and close
            else:
                reason = f"same type {btype} and close ({distance} chars)"
            
            # Apply decision
            if should_keep:
                deduplicated.append(boundary)
                print(f"   ✅ Keeping boundary {i}: pos={pos} type={btype} - {reason}")
            else:
                print(f"   ❌ Skipping boundary {i}: pos={pos} type={btype} - {reason}")
        
        print(f"🔧 DEDUPLICATION: Kept {len(deduplicated)} out of {len(boundaries)} boundaries")
        
        # Final summary
        print(f"📋 FINAL BOUNDARIES:")
        for i, (pos, btype, desc, keep_intact) in enumerate(deduplicated):
            print(f"   {i+1}. pos={pos:6d} type={btype:10s} desc={desc[:40]}...")
        
        return deduplicated
    
    def _create_chunks(self, text: str, boundaries: List[Tuple[int, str, str, bool]]) -> List[TextChunk]:
        """Create chunks from boundaries"""
        
        if not boundaries:
            return [TextChunk(0, 0, len(text), text)]
        
        chunks = []
        text_length = len(text)
        
        for i, (start_pos, boundary_type, description, keep_intact) in enumerate(boundaries):
            # Determine end position
            if i + 1 < len(boundaries):
                end_pos = boundaries[i + 1][0]
            else:
                end_pos = text_length
            
            # Extract chunk text
            chunk_text = text[start_pos:end_pos].strip()
            
            # Create chunk if large enough
            if len(chunk_text) >= self.config.min_chunk_size:
                chunk = TextChunk(
                    id=i,
                    start=start_pos,
                    end=end_pos,
                    text=chunk_text
                )
                
                # Add comprehensive metadata
                chunk.metadata = {
                    "type": boundary_type,
                    "description": description,
                    "keep_intact": keep_intact,
                    "boundary_text": chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text
                }
                
                chunks.append(chunk)
        
        return chunks if chunks else [TextChunk(0, 0, len(text), text)]
    
    def _handle_oversized_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Handle chunks that are too large"""
        
        final_chunks = []
        
        for chunk in chunks:
            if len(chunk.text) > self.config.max_chunk_size:
                metadata = getattr(chunk, 'metadata', {})
                chunk_type = metadata.get('type', 'unknown')
                
                if chunk_type == 'table_section':
                    # SPECJALNA OBSŁUGA: Tabela uszkodzeń - zawsze zachowaj jako jeden duży chunk
                    print(f"📊 HIERARCHICAL: Keeping entire table section intact ({len(chunk.text):,} chars) - will be parsed separately")
                    final_chunks.append(chunk)
                    
                elif metadata.get('keep_intact'):
                    # Keep intact even if large
                    print(f"📎 HIERARCHICAL: Keeping large {chunk_type} intact ({len(chunk.text):,} chars)")
                    final_chunks.append(chunk)
                    
                elif chunk_type in ['table', 'attachment']:
                    # Try to split table by subsections
                    print(f"📊 HIERARCHICAL: Splitting large {chunk_type} by subsections ({len(chunk.text):,} chars)")
                    sub_chunks = self._split_table_by_subsections(chunk)
                    final_chunks.extend(sub_chunks)
                    
                else:
                    # Use semantic splitting
                    print(f"📏 HIERARCHICAL: Semantic splitting of large section ({len(chunk.text):,} chars)")
                    sub_chunks = self._semantic_split(chunk.text, len(final_chunks))
                    final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _split_table_by_subsections(self, chunk: TextChunk) -> List[TextChunk]:
        """Split table/attachment by subsections like A., B., C."""
        
        # Look for subsection patterns
        subsection_pattern = re.compile(r'^([A-Z]\.|\d+\.)\s+[A-ZĄĆĘŁŃÓŚŹŻ]', re.MULTILINE)
        matches = list(subsection_pattern.finditer(chunk.text))
        
        if len(matches) > 1:
            sub_chunks = []
            for i, match in enumerate(matches):
                start_pos = match.start()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(chunk.text)
                
                sub_text = chunk.text[start_pos:end_pos].strip()
                if len(sub_text) >= self.config.min_chunk_size:
                    sub_chunk = TextChunk(
                        id=f"{chunk.id}_{i}",
                        start=chunk.start + start_pos,
                        end=chunk.start + end_pos,
                        text=sub_text
                    )
                    
                    # Copy metadata
                    if hasattr(chunk, 'metadata'):
                        sub_chunk.metadata = chunk.metadata.copy()
                        sub_chunk.metadata["subsection"] = match.group(1)
                    
                    sub_chunks.append(sub_chunk)
            
            return sub_chunks if sub_chunks else [chunk]
        
        return [chunk]
    
    def _semantic_split(self, text: str, base_chunk_id: int) -> List[TextChunk]:
        """Split using semantic chunking"""
        from .percentile_strategy import PercentileChunker
        
        semantic_config = SemanticChunkingConfig(
            strategy=self.config.strategy,
            model_name=self.config.model_name,
            percentile=self.config.percentile,
            min_chunk_size=self.config.min_chunk_size,
            max_chunk_size=self.config.max_chunk_size
        )
        
        semantic_chunker = PercentileChunker(semantic_config)
        semantic_chunks = semantic_chunker.chunk(text)
        
        # Update chunk IDs
        for i, chunk in enumerate(semantic_chunks):
            chunk.id = f"{base_chunk_id}_{i}"
        
        return semantic_chunks
    
    def _fallback_semantic_chunk(self, text: str) -> List[TextChunk]:
        """Fallback to pure semantic chunking"""
        from .percentile_strategy import PercentileChunker
        
        semantic_chunker = PercentileChunker(self.config)
        return semantic_chunker.chunk(text)
    
    def estimate_ram_usage(self, text_length: int) -> int:
        """Estimate RAM usage for hierarchical chunking"""
        return 100 * 1024 * 1024  # 100MB estimate
    
    def get_strategy_info(self) -> dict:
        """Return strategy information"""
        return {
            "name": "simplified_hierarchical",
            "description": "LLM-guided document structure chunking with context-aware boundary detection",
            "features": [
                "Full document LLM analysis",
                "Context-aware boundary resolution", 
                "Attachment/table detection", 
                "Intelligent size handling",
                "Subsection splitting"
            ]
        }