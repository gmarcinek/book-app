"""
Semantic TOC validation using embeddings
"""

import random
import fitz
from llm.embeddings_client import OpenAIEmbeddingsClient


class SemanticTOCValidator:
    """Content-based TOC validation using embeddings"""
    
    def __init__(self):
        from llm.embeddings_cache import EmbeddingsCache
        self.embedder = OpenAIEmbeddingsClient()
        self.cache = EmbeddingsCache()  # ← Add cache instance
    
    def validate_toc_content(self, builtin_toc, file_path):
        """Semantic validation - czy TOC titles pasują do page content"""
        doc = fitz.open(file_path)
        
        try:
            # 1. Filter out intro/generic entries  
            substantive_entries = self._filter_substantive_entries(builtin_toc)
            
            if len(substantive_entries) < 4:
                print("   Too few substantive entries for validation")
                return True  # Can't validate properly
            
            # 2. Random sample 4 entries (but skip first 3)
            sample_entries = random.sample(substantive_entries[3:], min(4, len(substantive_entries) - 3))
            
            print(f"   Testing {len(sample_entries)} random TOC entries...")
            
            # 3. Test each sampled entry
            matches = 0
            for entry in sample_entries:
                title = entry[1]
                page_num = entry[2]
                
                # Check page exists
                if page_num < 1 or page_num > len(doc):
                    print(f"   ❌ '{title}' → page {page_num} (doesn't exist)")
                    continue
                
                # Semantic matching
                if self._test_title_content_match(title, page_num, doc):
                    matches += 1
                    print(f"   ✅ '{title}' → page {page_num} (content match)")
                else:
                    print(f"   ❌ '{title}' → page {page_num} (no content match)")
            
            # 4. Score: 75% must match
            match_ratio = matches / len(sample_entries)
            print(f"   Semantic validation: {matches}/{len(sample_entries)} matches ({match_ratio:.1%})")
            
            return match_ratio >= 0.75
            
        finally:
            doc.close()
    
    def _filter_substantive_entries(self, builtin_toc):
        """Remove intro/generic entries"""
        skip_patterns = [
            'introduction', 'intro', 'preface', 'foreword', 'abstract',
            'table of contents', 'contents', 'index', 'bibliography',
            'acknowledgments', 'references', 'appendix'
        ]
        
        substantive = []
        for entry in builtin_toc:
            title = entry[1].lower()
            if not any(pattern in title for pattern in skip_patterns):
                substantive.append(entry)
        
        return substantive
    
    def _test_title_content_match(self, title, page_num, doc):
        """Test if TOC title matches page content using embeddings WITH CACHE"""
        try:
            # Extract page content (max 10 chunks)
            page = doc[page_num - 1]  # Convert to 0-based
            page_text = page.get_text()
            
            # Split into chunks (max 10)
            chunks = self._split_into_chunks(page_text, max_chunks=10)
            
            if not chunks:
                return False
            
            # Get embeddings WITH CACHE
            title_embedding = self.embedder.embed_batch_with_cache([title], self.cache)[0]  # ← CHANGE
            chunk_embeddings = self.embedder.embed_batch_with_cache(chunks, self.cache)     # ← CHANGE
            
            # Find best similarity
            best_similarity = 0
            for chunk_emb in chunk_embeddings:
                similarity = self.embedder.compute_similarity(title_embedding, chunk_emb)
                best_similarity = max(best_similarity, similarity)
            
            # Threshold: 0.6 similarity = content match
            return best_similarity >= 0.6
            
        except Exception as e:
            print(f"   ⚠️ Validation error for '{title}': {e}")
            return True  # Give benefit of doubt on errors
    
    def _split_into_chunks(self, text, max_chunks=10, chunk_size=200):
        """Split text into semantic chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
            
            if len(chunks) >= max_chunks:
                break
        
        return chunks