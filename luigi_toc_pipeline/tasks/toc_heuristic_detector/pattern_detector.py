import re
import fitz
from typing import List, Dict, Any


class TOCPatternDetector:
    """Stage 1: Find ALL potential TOCs using patterns - categorize by confidence"""
    
    def __init__(self, doc: fitz.Document, max_pages: int, config):
        self.doc = doc
        self.max_pages = max_pages
        self.config = config
        self.toc_keywords = config.get_task_setting("TOCDetector", "toc_keywords", [])
        self.min_toc_entries = config.get_task_setting("TOCDetector", "min_toc_entries", 3)
    
    def find_all_toc_candidates(self) -> Dict[str, List[Dict]]:
        """Find all TOC candidates and categorize by confidence"""
        all_candidates = []
        
        # Find all potential TOC starts
        for page_num in range(self.max_pages):
            toc_start = self._find_toc_start_on_page(page_num)
            if toc_start:
                # Try to find end for this start
                toc_end = self._find_toc_end_from_start(toc_start)
                
                candidate = {
                    **toc_start,
                    **toc_end,
                    'method': 'pattern',
                    'candidate_id': f"toc_{page_num}_{int(toc_start['start_y'])}"
                }
                all_candidates.append(candidate)
        
        # Categorize by confidence
        return self._categorize_candidates(all_candidates)
    
    def _find_toc_start_on_page(self, page_num: int) -> Dict[str, Any]:
        """Find TOC start patterns on single page"""
        page = self.doc[page_num]
        text_dict = page.get_text("dict")
        
        # Convert YAML keywords to regex patterns
        toc_patterns = self._build_regex_patterns_from_keywords()
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip().lower()
                
                for pattern in toc_patterns:
                    if re.search(pattern, line_text, re.IGNORECASE):
                        return {
                            'start_page': page_num,
                            'start_y': line["bbox"][1],
                            'pattern_matched': pattern,
                            'matched_text': line_text
                        }
        
        return None
    
    def _build_regex_patterns_from_keywords(self) -> List[str]:
        """Convert YAML toc_keywords to regex patterns"""
        patterns = []
        
        for keyword in self.toc_keywords:
            # Escape special regex characters in keyword
            escaped_keyword = re.escape(keyword)
            
            # Create word boundary pattern
            pattern = rf'\b{escaped_keyword}\b'
            patterns.append(pattern)
        
        return patterns
    
    def _find_toc_end_from_start(self, toc_start: Dict) -> Dict[str, Any]:
        """Find end coordinates for given TOC start"""
        start_page = toc_start['start_page']
        start_y = toc_start['start_y']
        
        toc_entries_count = 0
        last_entry_y = start_y
        
        # Search up to 3 pages from start (realistyczny limit)
        for page_offset in range(3):
            page_num = start_page + page_offset
            if page_num >= len(self.doc):
                break
                
            page = self.doc[page_num]
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_y = line["bbox"][1]
                    
                    # Skip lines before TOC start
                    if page_num == start_page and line_y <= start_y:
                        continue
                    
                    line_text = "".join(span["text"] for span in line["spans"]).strip()
                    
                    if self._looks_like_toc_entry(line_text):
                        toc_entries_count += 1
                        last_entry_y = line_y
                    elif toc_entries_count >= self.min_toc_entries and self._looks_like_content_start(line_text):
                        # Found clear end
                        return {
                            'end_page': page_num,
                            'end_y': line_y,
                            'entry_count': toc_entries_count,
                            'end_method': 'content_start'
                        }
        
        # Fallback: end after last entry
        return {
            'end_page': start_page + min(2, len(self.doc) - start_page - 1),
            'end_y': last_entry_y + 50,
            'entry_count': toc_entries_count,
            'end_method': 'fallback'
        }
    
    def _looks_like_toc_entry(self, text: str) -> bool:
        """Check if text looks like TOC entry"""
        text_clean = text.strip()
        if len(text_clean) < 3:
            return False
        
        patterns = [
            r'.+\.{3,}\s*\d+\s*$',  # dots + page number
            r'.+\s{3,}\d+\s*$',     # spaces + page number  
            r'^\d+\.?\d*\.?\s*.+\s+\d+\s*$'  # numbered sections
        ]
        
        return any(re.match(p, text_clean) for p in patterns)
    
    def _looks_like_content_start(self, text: str) -> bool:
        """Check if text looks like document content start"""
        text_clean = text.strip().lower()
        if len(text_clean) < 3:
            return False
            
        patterns = [
            r'^(rozdział|rozdzial)\s+\d+',
            r'^(wprowadzenie|wstęp|wstep)',
            r'^art\.\s*\d+',
            r'^§\s*\d+'
        ]
        
        return any(re.match(p, text_clean) for p in patterns)
    
    def _categorize_candidates(self, candidates: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize TOC candidates by confidence"""
        certain = []
        uncertain = []
        rejected = []
        
        for candidate in candidates:
            start_page = candidate['start_page']
            end_page = candidate['end_page']
            entry_count = candidate.get('entry_count', 0)
            
            page_distance = end_page - start_page
            
            # Proximity validation - TOC should be close to what it describes
            proximity_ok = self._validate_toc_proximity(candidate)
            
            # Categorization rules using YAML min_toc_entries + proximity
            if proximity_ok and page_distance <= 1 and entry_count >= self.min_toc_entries:
                certain.append(candidate)
            elif proximity_ok and page_distance <= 3 and entry_count >= max(2, self.min_toc_entries - 1):
                uncertain.append(candidate)
            else:
                rejected.append(candidate)  # bad proximity OR bad distance/entries
        
        return {
            'certain': certain,
            'uncertain': uncertain, 
            'rejected': rejected
        }
    
    def _validate_toc_proximity(self, candidate: Dict) -> bool:
        """Check if TOC is reasonably close to first entry it references"""
        toc_page = candidate['start_page']
        
        # Extract first entry page number from the candidate
        first_entry_page = self._extract_first_entry_page_number(candidate)
        
        if first_entry_page is None:
            return True  # Can't validate - give benefit of doubt
        
        gap = first_entry_page - toc_page
        
        # TOC should be max 5 pages before first entry
        if gap < 0:      # Entry before TOC = nonsense
            return False
        if gap > 5:      # Gap > 5 pages = suspicious  
            return False
        
        return True      # Gap 0-5 pages = reasonable
    
    def _extract_first_entry_page_number(self, candidate: Dict) -> int:
        """Extract page number from first TOC entry for proximity validation"""
        start_page = candidate['start_page']
        start_y = candidate['start_y']
        
        try:
            page = self.doc[start_page]
            text_dict = page.get_text("dict")
            
            # Look for first TOC entry after the TOC title
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_y = line["bbox"][1]
                    
                    # Skip lines before TOC start
                    if line_y <= start_y:
                        continue
                    
                    line_text = "".join(span["text"] for span in line["spans"]).strip()
                    
                    if self._looks_like_toc_entry(line_text):
                        # Extract page number from this TOC entry
                        page_num = self._extract_page_number_from_entry(line_text)
                        if page_num:
                            return page_num
            
            return None
            
        except Exception:
            return None  # Failed to extract - give benefit of doubt
    
    def _extract_page_number_from_entry(self, toc_entry: str) -> int:
        """Extract page number from TOC entry line"""
        import re
        
        # Try to find number at end of line
        match = re.search(r'\d+\s*', toc_entry.strip())
        if match:
            try:
                return int(match.group().strip())
            except ValueError:
                pass
        
        return None