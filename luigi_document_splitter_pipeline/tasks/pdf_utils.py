"""
PDF processing utilities - Individual entity chunking
"""

import fitz
from pathlib import Path


class PDFUtils:
    """Helper class for PDF operations with individual entity chunking"""
    
    @staticmethod
    def split_by_individual_entities(entries, doc, base_output_dir, doc_name, entry_format="detected"):
        """
        NEW: Split each TOC entity into its own PDF chunk
        Every entity gets its own file regardless of level or page overlaps
        """
        from .section_creator import SectionCreator
        
        print(f"🔪 Individual entity chunking:")
        print(f"   Total entries: {len(entries)}")
        print(f"   Entry format: {entry_format}")
        
        # Create single output directory for all chunks
        output_dir = base_output_dir / doc_name / "sections"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_sections = []
        
        # Process each entity individually
        for i, entry in enumerate(entries):
            try:
                # Calculate boundaries for this specific entity
                start_page, end_page = PDFUtils._calculate_entity_boundaries(
                    i, entries, len(doc), entry_format
                )
                
                if start_page is None:
                    print(f"   ⚠️ Entity {i}: No page number - skipping")
                    continue
                
                # Extract entity info based on format
                if entry_format == "builtin":
                    level, title, page = entry
                else:  # detected
                    title = entry.get("title", f"Section_{i}")
                    level = entry.get("level", 1)
                    page = entry.get("page")
                
                print(f"   📄 Entity {i}: '{title}' pages {start_page}-{end_page} (level {level})")
                
                # Create individual PDF chunk
                section = SectionCreator.create_individual_entity_chunk(
                    doc, title, start_page, end_page, level, i, output_dir
                )
                
                if section:
                    all_sections.append(section)
                    
            except Exception as e:
                print(f"   ❌ Entity {i} failed: {e}")
                continue
        
        print(f"✅ Created {len(all_sections)} individual entity chunks")
        return all_sections
    
    @staticmethod
    def _calculate_entity_boundaries(current_index, all_entries, doc_length, entry_format):
        """
        Calculate start/end pages for single entity using hierarchical logic
        Returns: (start_page, end_page) or (None, None) if invalid
        """
        current_entry = all_entries[current_index]
        
        # Get current entity's page and level
        if entry_format == "builtin":
            current_level = current_entry[0]  # [level, title, page]
            current_page = current_entry[2]
        else:  # detected
            current_level = current_entry.get("level", 1)
            current_page = current_entry.get("page")
        
        if current_page is None:
            return None, None
        
        # Find next entity with level <= current_level (hierarchical cut)
        next_page = None
        for j in range(current_index + 1, len(all_entries)):
            next_entry = all_entries[j]
            
            # Get next entity's level and page
            if entry_format == "builtin":
                next_level = next_entry[0]
                candidate_page = next_entry[2]
            else:
                next_level = next_entry.get("level", 1)
                candidate_page = next_entry.get("page")
            
            # Skip entries without page numbers
            if candidate_page is None:
                continue
            
            # Hierarchical logic: cut on same or higher level (lower number)
            if next_level <= current_level:
                next_page = candidate_page
                break
        
        # Calculate boundaries
        start_page = current_page
        if next_page is not None:
            end_page = next_page  # Include full page where next entity starts
        else:
            end_page = doc_length  # Last entity goes to document end
        
        # Validation: ensure at least current page is included
        if end_page < start_page:
            end_page = start_page  # Single page entity
        
        return start_page, end_page
    
    # LEGACY METHODS - keep for backward compatibility but mark as deprecated
    
    @staticmethod
    def split_by_levels(entries, doc, base_output_dir, doc_name, entry_format="detected"):
        """
        LEGACY: Use split_by_individual_entities instead
        Kept for backward compatibility
        """
        print("⚠️ DEPRECATED: split_by_levels - using split_by_individual_entities")
        return PDFUtils.split_by_individual_entities(entries, doc, base_output_dir, doc_name, entry_format)
    
    @staticmethod
    def find_end_page_builtin(current_index, entries, doc_length):
        """LEGACY: Use _calculate_entity_boundaries instead"""
        _, end_page = PDFUtils._calculate_entity_boundaries(current_index, entries, doc_length, "builtin")
        return end_page or doc_length
    
    @staticmethod
    def find_end_page_detected(current_index, entries, doc_length):
        """LEGACY: Use _calculate_entity_boundaries instead"""
        _, end_page = PDFUtils._calculate_entity_boundaries(current_index, entries, doc_length, "detected")
        return end_page or doc_length
    
    @staticmethod
    def create_sections_for_level(doc, entries, level, base_output_dir, doc_name, entry_format="builtin"):
        """LEGACY: Use split_by_individual_entities instead"""
        print(f"⚠️ DEPRECATED: create_sections_for_level - redirecting to individual chunking")
        return PDFUtils.split_by_individual_entities(entries, doc, base_output_dir, doc_name, entry_format)
    
    # UTILITY METHODS - keep unchanged
    
    @staticmethod
    def get_base_output_dir():
        """Get base output directory for sections - SYNC with StructuredTask"""
        return Path("output")
    
    @staticmethod
    def get_output_dir(file_path):
        """Get output directory for single document (legacy)"""
        input_path = Path(file_path)
        return PDFUtils.get_base_output_dir() / input_path.stem / "sections"
    
    @staticmethod
    def get_doc_name(file_path):
        """Get document name from file path"""
        return Path(file_path).stem