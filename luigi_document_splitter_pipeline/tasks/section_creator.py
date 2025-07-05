"""
Section creation helpers - Precise coordinate cutting
"""

import fitz
from pathlib import Path


class SectionCreator:
    """Helper class for creating PDF sections with precise coordinate cutting"""
    
    @staticmethod
    def create_individual_entity_chunk_precise(doc, title, boundaries, level, index, output_dir):
        """
        Create PDF chunk with precise Y coordinate cutting
        
        Args:
            doc: PyMuPDF document
            title: Section title
            boundaries: Dict with precise boundary info from PDFUtils._calculate_precise_boundaries
            level: Hierarchy level
            index: Entity index
            output_dir: Output directory
            
        Returns:
            Section info dict or None if failed
        """
        start_page = boundaries['start_page']
        strategy = boundaries['strategy']
        
        print(f"🔍 Creating precise chunk '{title}': {boundaries['summary']}")
        
        # Create level-specific subdirectory
        level_dir = output_dir / f"lvl_{level}"
        level_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with method suffix for debugging
        safe_title = SectionCreator._sanitize_filename(title)
        method_suffix = boundaries.get('strategy', 'unknown')[:8]  # Direct from boundaries
        filename = f"entity_{index:03d}_lvl{level}_{safe_title}_{method_suffix}.pdf"
        file_path = level_dir / filename
        
        # Create section based on strategy
        if strategy == "sub_page_precise":
            success = SectionCreator._create_sub_page_section(doc, boundaries, file_path)
        elif strategy == "precise_start":
            success = SectionCreator._create_precise_start_section(doc, boundaries, file_path)
        else:  # page_level fallback
            success = SectionCreator._create_page_level_section(doc, boundaries, file_path)
        
        if not success:
            print(f"⚠️ Failed to create section for '{title}'")
            return None
        
        # Set metadata
        SectionCreator._set_section_metadata(file_path, title, index, level, doc)
        
        section_info = {
            "title": title,
            "filename": filename,
            "file_path": str(file_path),
            "start_page": start_page,
            "end_page": boundaries.get('end_page'),
            "start_y": boundaries.get('start_y'),
            "end_y": boundaries.get('end_y'),
            "level": level,
            "entity_index": index,
            "cutting_strategy": strategy,
            "precision": "coordinate_based" if strategy != "page_level" else "page_based"
        }
        
        print(f"📄 Created: lvl_{level}/{filename} ({strategy})")
        return section_info
    
    @staticmethod
    def _create_sub_page_section(doc, boundaries, file_path):
        """Create section with sub-page precision (same page, different Y coords)"""
        start_page = boundaries['start_page']
        start_y = boundaries['start_y']
        end_y = boundaries['end_y']
        
        print(f"🔧 Sub-page debug: start_y={start_y}, end_y={end_y}")
        
        try:
            source_page = doc[start_page - 1]  # Convert to 0-based
            page_rect = source_page.rect
            
            # Apply margin and top threshold logic
            adjusted_start_y = SectionCreator._adjust_start_y_with_margin(start_y, page_rect.height)
            
            # Validate Y coordinates
            if end_y <= adjusted_start_y:
                print(f"⚠️ Invalid Y range: {adjusted_start_y} >= {end_y}, using full page")
                return SectionCreator._create_page_level_section(doc, boundaries, file_path)
            
            # Create crop rectangle from adjusted start_y to end_y
            crop_rect = fitz.Rect(0, adjusted_start_y, page_rect.width, end_y)
            
            # Create new document with cropped content
            section_doc = fitz.open()
            new_page = section_doc.new_page(width=page_rect.width, height=end_y - adjusted_start_y)
            
            # Show cropped area on new page
            new_page.show_pdf_page(new_page.rect, doc, start_page - 1, clip=crop_rect)
            
            section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Sub-page section creation failed: {e}")
            return False
    
    @staticmethod
    def _create_precise_start_section(doc, boundaries, file_path):
        """Create section starting from precise Y coordinate to end page"""
        start_page = boundaries['start_page']
        start_y = boundaries['start_y']
        end_page = boundaries['end_page']
        
        try:
            section_doc = fitz.open()
            
            # First page: crop from adjusted start_y to bottom
            if start_y is not None:
                source_page = doc[start_page - 1]
                page_rect = source_page.rect
                
                # Apply margin and top threshold logic
                adjusted_start_y = SectionCreator._adjust_start_y_with_margin(start_y, page_rect.height)
                
                # Crop from adjusted start_y to page bottom
                crop_rect = fitz.Rect(0, adjusted_start_y, page_rect.width, page_rect.height)
                new_page = section_doc.new_page(width=page_rect.width, height=page_rect.height - adjusted_start_y)
                new_page.show_pdf_page(new_page.rect, doc, start_page - 1, clip=crop_rect)
            else:
                # Fallback: include full first page
                section_doc.insert_pdf(doc, from_page=start_page - 1, to_page=start_page - 1)
            
            # Add remaining full pages (if any)
            if end_page > start_page:
                for page_num in range(start_page, min(end_page, len(doc))):
                    section_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Precise start section creation failed: {e}")
            return False
    
    @staticmethod
    def _create_page_level_section(doc, boundaries, file_path):
        """Fallback: create section with page-level boundaries"""
        start_page = boundaries['start_page']
        end_page = boundaries['end_page']
        
        try:
            section_doc = fitz.open()
            
            # Add pages from start to end
            for page_num in range(start_page - 1, min(end_page, len(doc))):
                if page_num >= 0 and page_num < len(doc):
                    section_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Page level section creation failed: {e}")
            return False
    
    @staticmethod
    def _set_section_metadata(file_path, title, index, level, original_doc):
        """Set PDF metadata for section"""
        try:
            section_doc = fitz.open(str(file_path))
            original_metadata = original_doc.metadata
            
            section_doc.set_metadata({
                "title": f"{original_metadata.get('title', '')} - {title}",
                "author": original_metadata.get('author', ''),
                "subject": f"Entity {index} Level {level}: {title}",
                "creator": original_metadata.get('creator', ''),
                "producer": f"DocumentSplitter Precise Cutting (original: {original_metadata.get('producer', '')})"
            })
            
            section_doc.save(str(file_path))  # Remove incremental=True
            section_doc.close()
            
        except Exception as e:
            print(f"⚠️ Metadata setting failed: {e}")
    
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
        
        return safe_title or "empty_title"
        
    @staticmethod
    def _adjust_start_y_with_margin(start_y, page_height):
        """
        Adjust start Y coordinate with margin and top threshold logic
        
        Args:
            start_y: Original Y coordinate
            page_height: Total page height
            
        Returns:
            Adjusted Y coordinate
        """
        if start_y is None:
            return 0
            
        # If start_y is in top 15% of page, start from page top
        top_threshold = page_height * 0.15
        if start_y <= top_threshold:
            return 0
        
        # Otherwise, add margin (30px) above the detected position
        margin = 30
        adjusted_y = max(0, start_y - margin)
        
        return adjusted_y
    
    @staticmethod
    def create_sequential_section(doc, title, start_boundary, end_boundary, level, entity_index, output_dir):
        """Create section using sequential cutting logic with bbox text extraction"""
        from .pdf_cutting_utils import PDFCuttingUtils
        
        start_page, start_y = start_boundary
        end_page, end_y = end_boundary
        
        # Create level directory
        level_dir = output_dir / f"lvl_{level}"
        level_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        safe_title = SectionCreator._sanitize_filename(title)
        filename = f"entity_{entity_index:03d}_lvl{level}_{safe_title}_sequential.pdf"
        file_path = level_dir / filename
        
        try:
            section_doc = fitz.open()
            
            # Extract text from bbox
            extracted_text = PDFCuttingUtils.extract_bbox_text(doc, start_page, start_y, end_page, end_y)
            
            # Create PDF pages
            if start_page == end_page:
                # Same page cutting
                source_page = doc[start_page - 1]
                crop_rect = PDFCuttingUtils.calculate_crop_rect(source_page.rect, start_y, end_y)
                PDFCuttingUtils.create_cropped_page(section_doc, doc, start_page, crop_rect)
            else:
                # Multi-page cutting
                # First page
                if start_y:
                    source_page = doc[start_page - 1]
                    crop_rect = PDFCuttingUtils.calculate_crop_rect(source_page.rect, start_y, None)
                    PDFCuttingUtils.create_cropped_page(section_doc, doc, start_page, crop_rect)
                else:
                    PDFCuttingUtils.add_full_page(section_doc, doc, start_page)
                
                # Middle pages
                for page_num in range(start_page + 1, min(end_page, len(doc) + 1)):
                    PDFCuttingUtils.add_full_page(section_doc, doc, page_num)
                
                # Last page
                if end_page <= len(doc) and end_y:
                    source_page = doc[end_page - 1]
                    crop_rect = PDFCuttingUtils.calculate_crop_rect(source_page.rect, None, end_y)
                    PDFCuttingUtils.create_cropped_page(section_doc, doc, end_page, crop_rect)
            
            section_doc.save(str(file_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            # Set metadata
            SectionCreator._set_section_metadata(file_path, title, entity_index, level, doc)
            
            return {
                "title": title,
                "filename": filename,
                "file_path": str(file_path),
                "start_page": start_page,
                "end_page": end_page,
                "start_y": start_y,
                "end_y": end_y,
                "level": level,
                "entity_index": entity_index,
                "cutting_strategy": "sequential",
                "extracted_text": extracted_text.strip(),
                "text_length": len(extracted_text.strip())
            }
            
        except Exception as e:
            print(f"❌ Sequential section creation failed: {e}")
            return None