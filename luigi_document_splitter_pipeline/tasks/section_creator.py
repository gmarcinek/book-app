"""
Section creation helpers
"""

import fitz
from pathlib import Path


class SectionCreator:
    """Helper class for creating PDF sections"""
    
    @staticmethod
    def create_section_builtin(doc, title, start_page, end_page, level, index, output_dir):
        """Create single section from built-in TOC entry with validation"""
        # Validate page range
        if start_page > end_page or start_page < 1 or start_page > len(doc):
            print(f"⚠️ Invalid page range for '{title}': {start_page}-{end_page}")
            return None
        
        # Adjust end_page to document bounds
        end_page = min(end_page, len(doc))
        
        print(f"🔍 Processing '{title}': pages {start_page}-{end_page} (doc has {len(doc)} pages)")
        
        # Create filename
        safe_title = SectionCreator._sanitize_filename(title)
        filename = f"section_{index:02d}_{safe_title}.pdf"
        file_path = output_dir / filename
        
        # Extract pages
        section_doc = fitz.open()
        
        # Copy metadata
        original_metadata = doc.metadata
        section_doc.set_metadata({
            "title": f"{original_metadata.get('title', '')} - {title}",
            "author": original_metadata.get('author', ''),
            "subject": f"Level {level} Section {index + 1}: {title}",
            "creator": original_metadata.get('creator', ''),
            "producer": f"DocumentSplitter (original: {original_metadata.get('producer', '')})"
        })
        
        # Insert pages with validation
        pages_added = 0
        for page_num in range(start_page - 1, min(end_page, len(doc))):
            if page_num >= 0 and page_num < len(doc):
                section_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                pages_added += 1
        
        # Check if we have pages to save
        if pages_added == 0:
            print(f"⚠️ No pages added for '{title}' - skipping")
            section_doc.close()
            return None
        
        section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
        section_doc.close()
        
        section_info = {
            "title": title,
            "filename": filename,
            "file_path": str(file_path),
            "start_page": start_page,
            "end_page": end_page,
            "pages_count": pages_added,
            "level": level,
            "section_index": index
        }
        
        print(f"📄 Created: {filename} (pages {start_page}-{end_page}, {pages_added} pages)")
        return section_info
    
    @staticmethod
    def create_section_detected(doc, entry, index, all_entries, output_dir):
        """Create section from detected TOC entry"""
        entry_title = entry.get("title", f"Section_{index}")
        entry_page = entry.get("page")
        
        if entry_page is None:
            return None
        
        next_page = SectionCreator._find_next_page(index, all_entries)
        end_page = next_page - 1 if next_page else len(doc) - 1
        
        safe_title = SectionCreator._sanitize_filename(entry_title)
        filename = f"section_{index:02d}_{safe_title}.pdf"
        file_path = output_dir / filename
        
        # Extract pages
        section_doc = fitz.open()
        
        # Copy metadata
        original_metadata = doc.metadata
        section_doc.set_metadata({
            "title": f"{original_metadata.get('title', '')} - {entry_title}",
            "author": original_metadata.get('author', ''),
            "subject": f"Section {index + 1}: {entry_title}",
            "creator": original_metadata.get('creator', ''),
            "producer": f"DocumentSplitter (original: {original_metadata.get('producer', '')})"
        })
        
        # Insert pages with validation
        pages_added = 0
        for page_num in range(entry_page - 1, min(end_page + 1, len(doc))):
            if page_num >= 0 and page_num < len(doc):
                section_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                pages_added += 1
        
        if pages_added == 0:
            print(f"⚠️ No pages added for '{entry_title}' - skipping")
            section_doc.close()
            return None
        
        section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
        section_doc.close()
        
        section_info = {
            "title": entry_title,
            "filename": filename,
            "file_path": str(file_path),
            "start_page": entry_page,
            "end_page": end_page,
            "pages_count": pages_added,
            "level": entry.get('level', 1),
            "section_index": index
        }
        
        print(f"📄 Created: {filename} (pages {entry_page}-{end_page}, {pages_added} pages)")
        return section_info
    
    @staticmethod
    def create_section_detected_with_level(doc, title, start_page, end_page, level, index, output_dir):
        """Create section from detected TOC entry with level support"""
        # Validate page range
        if start_page > end_page or start_page < 1 or start_page > len(doc):
            print(f"⚠️ Invalid page range for '{title}': {start_page}-{end_page}")
            return None
        
        # Adjust end_page to document bounds
        end_page = min(end_page, len(doc))
        
        print(f"🔍 Processing detected '{title}': pages {start_page}-{end_page} (doc has {len(doc)} pages)")
        
        # Create filename
        safe_title = SectionCreator._sanitize_filename(title)
        filename = f"section_{index:02d}_{safe_title}.pdf"
        file_path = output_dir / filename
        
        # Extract pages
        section_doc = fitz.open()
        
        # Copy metadata
        original_metadata = doc.metadata
        section_doc.set_metadata({
            "title": f"{original_metadata.get('title', '')} - {title}",
            "author": original_metadata.get('author', ''),
            "subject": f"Level {level} Section {index + 1}: {title}",
            "creator": original_metadata.get('creator', ''),
            "producer": f"DocumentSplitter (original: {original_metadata.get('producer', '')})"
        })
        
        # Insert pages with validation
        pages_added = 0
        for page_num in range(start_page - 1, min(end_page, len(doc))):
            if page_num >= 0 and page_num < len(doc):
                section_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                pages_added += 1
        
        # Check if we have pages to save
        if pages_added == 0:
            print(f"⚠️ No pages added for '{title}' - skipping")
            section_doc.close()
            return None
        
        section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
        section_doc.close()
        
        section_info = {
            "title": title,
            "filename": filename,
            "file_path": str(file_path),
            "start_page": start_page,
            "end_page": end_page,
            "pages_count": pages_added,
            "level": level,
            "section_index": index
        }
        
        print(f"📄 Created: {filename} (pages {start_page}-{end_page}, {pages_added} pages)")
        return section_info
    
    @staticmethod
    def _find_next_page(current_index, all_entries):
        """Find next entry's page number"""
        for i in range(current_index + 1, len(all_entries)):
            next_page = all_entries[i].get("page")
            if next_page is not None:
                return next_page
        return None
    
    @staticmethod
    def _sanitize_filename(title):
        """Sanitize title for filesystem use"""
        import re
        
        # Replace problematic characters with underscores
        safe_title = re.sub(r'[<>:"/\\|?*\s]', '_', title)
        
        # Replace multiple underscores with single underscore
        safe_title = re.sub(r'_+', '_', safe_title)
        
        # Remove leading/trailing underscores and dots
        safe_title = safe_title.strip('._')
        
        # Truncate if too long
        if len(safe_title) > 50:
            safe_title = safe_title[:50].rstrip('_')
        
        return safe_title or "untitled"