"""
TOC quality validation helpers
"""

from luigi_document_splitter_pipeline.tasks._old_semantic_toc_validator import SemanticTOCValidator


class TOCValidator:
    """Helper class for validating TOC quality"""
    
    @staticmethod
    def validate_section_boundaries(builtin_toc, doc_length):
        """Check if TOC boundaries make sense"""
        if not builtin_toc:
            return False
        
        sections = []
        for i, entry in enumerate(builtin_toc):
            start_page = entry[2]
            end_page = builtin_toc[i+1][2] - 1 if i+1 < len(builtin_toc) else doc_length
            
            sections.append({
                'title': entry[1],
                'start': start_page, 
                'end': end_page,
                'length': end_page - start_page + 1
            })
        
        # Red flags
        micro_sections = sum(1 for s in sections if s['length'] <= 2)  # <=2 pages
        huge_sections = sum(1 for s in sections if s['length'] > doc_length * 0.8)  # >80% doc
        duplicate_starts = len(set(s['start'] for s in sections)) != len(sections)
        
        quality = {
            'micro_ratio': micro_sections / len(sections),      # Should be <50%
            'huge_ratio': huge_sections / len(sections),        # Should be <20% 
            'has_duplicates': duplicate_starts,                 # Should be False
            'avg_length': sum(s['length'] for s in sections) / len(sections)
        }
        
        print(f"   Boundary analysis: micro={quality['micro_ratio']:.1%}, huge={quality['huge_ratio']:.1%}, duplicates={quality['has_duplicates']}")
        
        # Fail if boundaries are garbage
        if quality['micro_ratio'] > 0.5 or quality['huge_ratio'] > 0.2 or quality['has_duplicates']:
            return False
        
        return True
    
    @staticmethod
    def validate_page_bounds(builtin_toc, doc_pages):
        """Check if TOC page numbers exist in document"""
        if not builtin_toc:
            return False
        
        toc_pages = [entry[2] for entry in builtin_toc]
        invalid_count = len([p for p in toc_pages if p > doc_pages or p < 1])
        invalid_ratio = invalid_count / len(builtin_toc)
        
        print(f"   Page bounds: {invalid_count}/{len(builtin_toc)} invalid ({invalid_ratio:.1%})")
        
        # Fail if >20% entries point to non-existent pages
        return invalid_ratio <= 0.2
    
    @staticmethod
    def is_valid_toc(builtin_toc, doc_pages, file_path):  # ← dodaj file_path param
        """Combined validation: bounds + boundaries + semantic fallback"""
        if not builtin_toc:
            return False
        
        # 1. Page bounds (hard requirement)
        page_bounds_ok = TOCValidator.validate_page_bounds(builtin_toc, doc_pages)
        if not page_bounds_ok:
            return False
        
        # 2. Boundary sanity check (relaxed)
        boundaries_ok = TOCValidator.validate_section_boundaries(builtin_toc, doc_pages)
        
        # 3. Semantic validation (if boundaries fail)
        if not boundaries_ok:
            print("   Boundaries failed, trying semantic validation...")
            semantic_validator = SemanticTOCValidator()
            return semantic_validator.validate_toc_content(builtin_toc, file_path)
        
        return True