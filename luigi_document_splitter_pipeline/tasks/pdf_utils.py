"""
PDF processing utilities
"""

import fitz
from pathlib import Path


class PDFUtils:
    """Helper class for PDF operations"""
    
    @staticmethod
    def find_end_page_builtin(current_index, entries, doc_length):
        """Find end page for built-in TOC entry with better validation"""
        if current_index + 1 < len(entries):
            next_entry = entries[current_index + 1]
            next_page = next_entry[2]  # page number from TOC
            return max(1, next_page - 1)  # Ensure positive page number
        else:
            return doc_length  # Last entry goes to document end
    
    @staticmethod
    def find_end_page_detected(current_index, entries, doc_length):
        """Find end page for detected TOC entry"""
        if current_index + 1 < len(entries):
            next_entry = entries[current_index + 1]
            next_page = next_entry.get('page')
            if next_page:
                return max(1, next_page - 1)
        return doc_length  # Last entry goes to document end
    
    @staticmethod
    def split_by_levels(entries, doc, base_output_dir, doc_name, entry_format="detected"):
        """Universal level-based splitting for both built-in and detected TOC"""
        
        def get_entry_level(entry):
            """Get level from entry based on format"""
            if entry_format == "builtin":
                return entry[0]  # [level, title, page]
            else:  # detected format
                return entry.get('level', 1)  # {"level": 1, "title": "...", "page": ...}
        
        # Group by level
        level_1_entries = [entry for entry in entries if get_entry_level(entry) == 1]
        level_2_entries = [entry for entry in entries if get_entry_level(entry) == 2]
        
        all_sections = []
        
        # Split by level 1
        if level_1_entries:
            lvl1_sections = PDFUtils.create_sections_for_level(
                doc, level_1_entries, 1, base_output_dir, doc_name, entry_format
            )
            all_sections.extend(lvl1_sections)
        
        # Split by level 2  
        if level_2_entries:
            lvl2_sections = PDFUtils.create_sections_for_level(
                doc, level_2_entries, 2, base_output_dir, doc_name, entry_format
            )
            all_sections.extend(lvl2_sections)
        
        return all_sections
    
    @staticmethod
    def create_sections_for_level(doc, entries, level, base_output_dir, doc_name, entry_format="builtin"):
        """Create sections for specific TOC level - supports both formats"""
        from .section_creator import SectionCreator
        
        # Create level-specific output directory
        output_dir = base_output_dir / doc_name / "sections" / f"lvl_{level}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        sections = []
        
        for i, entry in enumerate(entries):
            if entry_format == "builtin":
                # Built-in format: [level, title, page]
                toc_level, title, page = entry
                end_page = PDFUtils.find_end_page_builtin(i, entries, len(doc))
                
                section = SectionCreator.create_section_builtin(
                    doc, title, page, end_page, level, i, output_dir
                )
            else:
                # Detected format: {"level": 1, "title": "...", "page": ...}
                title = entry.get("title", f"Section_{i}")
                page = entry.get("page")
                
                if page is None:
                    continue  # Skip entries without page numbers
                
                end_page = PDFUtils.find_end_page_detected(i, entries, len(doc))
                
                section = SectionCreator.create_section_detected_with_level(
                    doc, title, page, end_page, level, i, output_dir
                )
            
            if section:
                sections.append(section)
        
        print(f"📁 Created {len(sections)} level {level} sections in: {output_dir.name}")
        return sections
    
    @staticmethod
    def get_base_output_dir():
        """Get base output directory for sections - SYNC with StructuredTask"""
        return Path("output")
    
    @staticmethod
    def get_output_dir(file_path):
        """Get output directory for single document (legacy - use split_by_levels instead)"""
        input_path = Path(file_path)
        return PDFUtils.get_base_output_dir() / input_path.stem / "sections"
    
    @staticmethod
    def get_doc_name(file_path):
        """Get document name from file path"""
        return Path(file_path).stem