"""
Semantic TOC validation using embeddings
"""

import random
import logging
import fitz
from pathlib import Path
from llm.embeddings_client import OpenAIEmbeddingsClient
from llm.embeddings_cache import EmbeddingsCache

logger = logging.getLogger(__name__)


class SemanticTOCValidator:
    """Content-based TOC validation using embeddings"""
    
    def __init__(self, similarity_threshold=0.6):
        self.embedder = OpenAIEmbeddingsClient()
        self.cache = EmbeddingsCache()
        self.similarity_threshold = similarity_threshold
    
    def validate_toc_content(self, builtin_toc, file_path):
        """Semantic validation - czy TOC titles pasują do page content"""
        doc = fitz.open(file_path)
        
        try:
            # 1. Filter out intro/generic entries  
            substantive_entries = self._filter_substantive_entries(builtin_toc)
            
            if len(substantive_entries) < 4:
                logger.info("Too few substantive entries for validation")
                return True  # Can't validate properly
            
            # 2. DETERMINISTIC sampling - evenly spaced entries
            sample_entries = self._get_deterministic_sample(substantive_entries)
            
            logger.info(f"Testing {len(sample_entries)} TOC entries...")
            
            # 3. Test each sampled entry
            matches = 0
            skipped = 0
            
            for entry in sample_entries:
                title = entry[1]
                page_num = entry[2]
                
                # Check page exists
                if page_num < 1 or page_num > len(doc):
                    logger.warning(f"'{title}' → page {page_num} (doesn't exist)")
                    skipped += 1
                    continue
                
                # Semantic matching
                match_result = self._test_title_content_match(title, page_num, doc)
                
                if match_result is None:
                    skipped += 1
                    logger.warning(f"'{title}' → page {page_num} (validation skipped)")
                elif match_result:
                    matches += 1
                    logger.info(f"'{title}' → page {page_num} (content match)")
                else:
                    logger.info(f"'{title}' → page {page_num} (no content match)")
            
            # 4. Score: threshold% must match (excluding skipped)
            tested = len(sample_entries) - skipped
            if tested == 0:
                logger.warning("No entries could be tested")
                return True  # Give benefit of doubt
            
            match_ratio = matches / tested
            passed = match_ratio >= 0.75  # Keep 75% threshold for robustness
            
            logger.info(f"Semantic validation: {matches}/{tested} matches ({match_ratio:.1%}), passed: {passed}")
            
            return passed
            
        finally:
            doc.close()
    
    def _get_deterministic_sample(self, substantive_entries):
        """Get evenly spaced sample entries for consistent validation"""
        # Skip first 3, take evenly spaced entries
        available = substantive_entries[3:]
        
        if len(available) <= 4:
            return available
        
        # Take 4 evenly spaced entries
        step = len(available) // 4
        indices = [i * step for i in range(4)]
        
        return [available[i] for i in indices if i < len(available)]
    
    def _filter_substantive_entries(self, builtin_toc):
        """Remove intro/generic entries"""
        skip_patterns = [
            'introduction', 'intro', 'preface', 'foreword', 'abstract',
            'table of contents', 'contents', 'index', 'bibliography',
            'acknowledgments', 'references', 'appendix', 'dedication'
        ]
        
        substantive = []
        for entry in builtin_toc:
            title = entry[1].lower()
            if not any(pattern in title for pattern in skip_patterns):
                substantive.append(entry)
        
        return substantive
    
    def _test_title_content_match(self, title, page_num, doc):
        """Test if TOC title matches page content using embeddings"""
        try:
            # Extract page content
            page = doc[page_num - 1]  # Convert to 0-based
            page_text = page.get_text()
            
            # Split into chunks with overlap
            chunks = self._split_into_chunks_with_overlap(page_text)
            
            if not chunks:
                return None  # Can't test
            
            # Get embeddings WITH CACHE
            title_embedding = self.embedder.embed_batch_with_cache([title], self.cache)[0]
            chunk_embeddings = self.embedder.embed_batch_with_cache(chunks, self.cache)
            
            # Find best similarity
            best_similarity = 0
            for chunk_emb in chunk_embeddings:
                similarity = self.embedder.compute_similarity(title_embedding, chunk_emb)
                best_similarity = max(best_similarity, similarity)
            
            return best_similarity >= self.similarity_threshold
            
        except Exception as e:
            logger.error(f"Validation error for '{title}': {e}")
            return None  # Mark as skipped, don't assume valid
    
    def _split_into_chunks_with_overlap(self, text, max_chunks=10, chunk_size=200, overlap=50):
        """Split text into overlapping chunks for better context preservation"""
        words = text.split()
        chunks = []
        i = 0
        
        while i < len(words) and len(chunks) < max_chunks:
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():  # Only add non-empty chunks
                chunks.append(chunk)
            i += chunk_size - overlap
            
            # Prevent infinite loop
            if i <= len(chunks) * overlap:
                break
        
        return chunks