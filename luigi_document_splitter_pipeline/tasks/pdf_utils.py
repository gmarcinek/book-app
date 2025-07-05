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
        """Universal level-based splitting - creates folder for each level found"""
        
        def get_entry_level(entry):
            """Get level from entry based on format"""
            if entry_format == "builtin":
                return entry[0]  # [level, title, page]
            else:  # detected format
                return entry.get('level')  # NO DEFAULT - should be filtered upstream
        
        # DEBUG: Analyze entry distribution
        print(f"🔍 DEBUG split_by_levels:")
        print(f"   Total entries: {len(entries)}")
        print(f"   Entry format: {entry_format}")
        
        # Show level distribution
        level_counts = {}
        null_levels = 0
        for i, entry in enumerate(entries):
            level = entry.get('level') if entry_format == "detected" else entry[0]
            title = entry.get('title', '') if entry_format == "detected" else entry[1]
            page = entry.get('page') if entry_format == "detected" else entry[2]
            
            if level is None:
                null_levels += 1
                print(f"   Entry {i}: '{title}' page {page} → level=NULL (will use level 1)")
            else:
                level_counts[level] = level_counts.get(level, 0) + 1
                print(f"   Entry {i}: '{title}' page {page} → level={level}")
        
        print(f"   Level distribution: {level_counts}")
        print(f"   Null levels (defaulted to 1): {null_levels}")
        
        # Group by level dynamically
        levels_found = {}
        for entry in entries:
            level = get_entry_level(entry)
            if level not in levels_found:
                levels_found[level] = []
            levels_found[level].append(entry)
        
        print(f"   Grouped levels: {dict((k, len(v)) for k, v in levels_found.items())}")
        
        all_sections = []
        
        # Create sections for each level found
        for level in sorted(levels_found.keys()):
            level_entries = levels_found[level]
            print(f"📁 Processing level {level}: {len(level_entries)} entries")
            
            level_sections = PDFUtils.create_sections_for_level(
                doc, level_entries, level, base_output_dir, doc_name, entry_format
            )
            all_sections.extend(level_sections)
            print(f"   Created {len(level_sections)} PDF files for level {level}")
        
        print(f"✅ Total PDF files created: {len(all_sections)}")
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