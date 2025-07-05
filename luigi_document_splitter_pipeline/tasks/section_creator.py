"""
Section creation helpers - Individual Entity Chunking
"""

import fitz
from pathlib import Path


class SectionCreator:
    """Helper class for creating PDF sections with individual entity chunking"""
    
    @staticmethod
    def create_individual_entity_chunk(doc, title, start_page, end_page, level, index, output_dir):
        """
        NEW: Create PDF chunk for individual TOC entity
        Each entity gets its own file regardless of overlaps or level
        """
        # Validate page range
        if start_page > end_page or start_page < 1 or start_page > len(doc):
            print(f"⚠️ Invalid page range for '{title}': {start_page}-{end_page}")
            return None
        
        # Adjust end_page to document bounds
        end_page = min(end_page, len(doc))
        
        print(f"🔍 Creating chunk '{title}': pages {start_page}-{end_page} (level {level})")
        
        # Create level-specific subdirectory for file organization
        level_dir = output_dir / f"lvl_{level}"
        level_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with entity index
        safe_title = SectionCreator._sanitize_filename(title)
        filename = f"entity_{index:03d}_lvl{level}_{safe_title}.pdf"
        file_path = level_dir / filename
        
        # Extract pages
        section_doc = fitz.open()
        
        # Copy metadata
        original_metadata = doc.metadata
        section_doc.set_metadata({
            "title": f"{original_metadata.get('title', '')} - {title}",
            "author": original_metadata.get('author', ''),
            "subject": f"Entity {index} Level {level}: {title}",
            "creator": original_metadata.get('creator', ''),
            "producer": f"DocumentSplitter Individual Chunking (original: {original_metadata.get('producer', '')})"
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
            "entity_index": index,
            "chunk_type": "individual_entity"
        }
        
        print(f"📄 Created: lvl_{level}/{filename} (pages {start_page}-{end_page}, {pages_added} pages)")
        return section_info
    
    # UTILITY METHODS
    
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