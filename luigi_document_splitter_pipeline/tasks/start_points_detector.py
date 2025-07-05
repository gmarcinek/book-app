"""
Sequential start points detection and cutting
"""

import re
import fitz
from typing import Dict, Optional, Union, List, Tuple
from llm.embeddings_client import OpenAIEmbeddingsClient


class StartPointsDetector:
    """Find start points for all TOC entities, sort by (page, Y), cut sequentially"""
    
    def __init__(self):
        self.embedder = None  # Lazy load
    
    def find_all_start_points(self, doc: fitz.Document, toc_entries: List, entry_format: str = "builtin") -> List[Tuple]:
        """
        Find all start points and return sorted list for sequential cutting
        
        Returns: [(page, start_y, entity_index, title, level), ...]
        """
        start_points = []
        
        for i, entry in enumerate(toc_entries):
            title, page_num = self._extract_title_page(entry, entry_format)
            level = self._extract_level(entry, entry_format)
            
            if page_num is None:
                continue
                
            start_y = self._find_title_y_coordinate(doc, page_num, title)
            
            start_points.append((
                page_num,
                start_y or 0,  # Fallback to page start if no Y found
                i,
                title,
                level
            ))
            
            print(f"🎯 Entity {i}: '{title}' → page {page_num}, Y={start_y}")
        
        # Sort by (page, Y)
        start_points.sort(key=lambda x: (x[0], x[1]))
        
        print(f"📋 Found {len(start_points)} start points, sorted by position")
        return start_points
    
    def _extract_title_page(self, entry: Union[List, Dict], entry_format: str) -> tuple:
        """Extract title and page"""
        if entry_format == "builtin":
            return entry[1], entry[2] if len(entry) >= 3 else (None, None)
        else:
            return entry.get("title"), entry.get("page")
    
    def _extract_level(self, entry: Union[List, Dict], entry_format: str) -> int:
        """Extract hierarchy level"""
        if entry_format == "builtin":
            return entry[0] if len(entry) >= 1 else 1
        else:
            return entry.get("level", 1)
    
    def _find_title_y_coordinate(self, doc: fitz.Document, page_num: int, title: str) -> Optional[float]:
        """Progressive cascade to find Y coordinate"""
        if page_num < 1 or page_num > len(doc):
            return None
            
        page = doc[page_num - 1]
        text_dict = page.get_text("dict")
        
        # 1. Exact phrase
        y_coord = self._try_exact_phrase(text_dict, title)
        if y_coord:
            return y_coord
            
        # 2. Word truncation (max 2 iterations)
        y_coord = self._try_word_truncation(text_dict, title)
        if y_coord:
            return y_coord
            
        # 3. Word-bag matching (80%+)
        y_coord = self._try_word_bag_matching(text_dict, title)
        if y_coord:
            return y_coord
            
        # 4. Embedding fallbacks
        y_coord = self._try_embedding_fallbacks(text_dict, title)
        if y_coord:
            return y_coord
            
        return None  # Page start fallback
    
    def _try_exact_phrase(self, text_dict: Dict, title: str) -> Optional[float]:
        """Exact phrase match"""
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if line_text == title or title in line_text:
                    return line["bbox"][1]
        return None
    
    def _try_word_truncation(self, text_dict: Dict, title: str) -> Optional[float]:
        """Progressive word truncation"""
        words = title.split()
        if len(words) < 3:
            return None
            
        # Try 2 iterations of word removal
        for remove_count in [1, 2]:
            if len(words) >= 3 + 2 * remove_count:
                truncated = " ".join(words[remove_count:-remove_count])
                y_coord = self._search_phrase_in_page(text_dict, truncated)
                if y_coord:
                    return y_coord
        return None
    
    def _try_word_bag_matching(self, text_dict: Dict, title: str) -> Optional[float]:
        """Word-bag matching with 80%+ threshold"""
        title_words = set(self._normalize_text(title).split())
        if len(title_words) < 2:
            return None
            
        best_match = None
        best_ratio = 0.0
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                line_words = set(self._normalize_text(line_text).split())
                
                if line_words:
                    overlap = len(title_words & line_words)
                    ratio = overlap / len(title_words)
                    if ratio >= 0.8 and ratio > best_ratio:
                        best_ratio = ratio
                        best_match = line["bbox"][1]
        
        return best_match
    
    def _try_embedding_fallbacks(self, text_dict: Dict, title: str) -> Optional[float]:
        """Embedding-based fallbacks"""
        # Visual candidates first
        candidates = self._extract_visual_candidates(text_dict)
        if candidates:
            result = self._find_best_semantic_match(candidates, title)
            if result:
                return result
        
        # All sentences fallback
        sentences = self._extract_all_sentences(text_dict)
        if sentences:
            return self._find_semantic_jump(sentences, title)
        
        return None
    
    def _search_phrase_in_page(self, text_dict: Dict, phrase: str) -> Optional[float]:
        """Search phrase in page text"""
        normalized_phrase = self._normalize_text(phrase)
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if normalized_phrase in self._normalize_text(line_text):
                    return line["bbox"][1]
        return None
    
    def _extract_visual_candidates(self, text_dict: Dict) -> List[Dict]:
        """Extract bold/large font candidates"""
        candidates = []
        all_sizes = []
        
        # Calculate average font size
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    all_sizes.append(span.get("size", 10))
        
        avg_font_size = sum(all_sizes) / len(all_sizes) if all_sizes else 10
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if len(line_text) < 3:
                    continue
                    
                is_bold = self._is_line_bold(line)
                avg_size = self._get_line_font_size(line)
                is_large = avg_size > avg_font_size * 1.1
                
                if is_bold or is_large:
                    candidates.append({
                        'text': line_text,
                        'y_coord': line["bbox"][1]
                    })
        
        return candidates
    
    def _extract_all_sentences(self, text_dict: Dict) -> List[Dict]:
        """Extract all sentences"""
        sentences = []
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if len(line_text) > 10:
                    sentences.append({
                        'text': line_text,
                        'y_coord': line["bbox"][1]
                    })
        return sentences
    
    def _find_best_semantic_match(self, candidates: List[Dict], title: str) -> Optional[float]:
        """Find best semantic match using embeddings"""
        if not candidates:
            return None
            
        self._ensure_embedder()
        
        try:
            candidate_texts = [c['text'] for c in candidates]
            title_embedding = self.embedder.embed_batch([title])[0]
            candidate_embeddings = self.embedder.embed_batch(candidate_texts)
            
            best_idx = -1
            best_similarity = 0.0
            
            for i, candidate_emb in enumerate(candidate_embeddings):
                similarity = self.embedder.compute_similarity(title_embedding, candidate_emb)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_idx = i
            
            if best_similarity >= 0.6:
                return candidates[best_idx]['y_coord']
                
        except Exception as e:
            print(f"⚠️ Embedding failed: {e}")
            
        return None
    
    def _find_semantic_jump(self, sentences: List[Dict], title: str) -> Optional[float]:
        """Find semantic jump in similarity"""
        if len(sentences) < 2:
            return None
            
        self._ensure_embedder()
        
        try:
            sentence_texts = [s['text'] for s in sentences]
            title_embedding = self.embedder.embed_batch([title])[0]
            sentence_embeddings = self.embedder.embed_batch(sentence_texts)
            
            similarities = []
            for sent_emb in sentence_embeddings:
                sim = self.embedder.compute_similarity(title_embedding, sent_emb)
                similarities.append(sim)
            
            # Find significant jump
            for i in range(1, len(similarities)):
                jump = similarities[i] - similarities[i-1]
                if jump > 0.3 and similarities[i] > 0.5:
                    return sentences[i]['y_coord']
                    
        except Exception as e:
            print(f"⚠️ Semantic jump detection failed: {e}")
            
        return None
    
    def _ensure_embedder(self):
        """Lazy load embedder"""
        if self.embedder is None:
            self.embedder = OpenAIEmbeddingsClient()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparisons"""
        normalized = re.sub(r'[^\w\s]', ' ', text)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.lower().strip()
    
    def _is_line_bold(self, line: Dict) -> bool:
        """Check if line has bold text"""
        for span in line.get("spans", []):
            flags = span.get("flags", 0)
            if flags & 2**4:  # Bold flag
                return True
        return False
    
    def _get_line_font_size(self, line: Dict) -> float:
        """Get average font size for line"""
        sizes = [span.get("size", 10) for span in line.get("spans", [])]
        return sum(sizes) / len(sizes) if sizes else 10.0