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
    def create_sections_for_level(doc, entries, level, base_output_dir, doc_name):
        """Create sections for specific TOC level"""
        from .section_creator import SectionCreator
        
        # SYNC: Use same doc_name structure as StructuredTask
        output_dir = base_output_dir / doc_name / "sections" / f"lvl_{level}"  # ← Change path
        output_dir.mkdir(parents=True, exist_ok=True)
        
        sections = []
        
        for i, entry in enumerate(entries):
            toc_level, title, page = entry
            
            # Find end page
            end_page = PDFUtils.find_end_page_builtin(i, entries, len(doc))
            
            # Create section
            section = SectionCreator.create_section_builtin(
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
        """Get output directory for single document"""
        input_path = Path(file_path)
        return PDFUtils.get_base_output_dir() / input_path.stem
    
    @staticmethod
    def get_doc_name(file_path):
        """Get document name from file path"""
        return Path(file_path).stem