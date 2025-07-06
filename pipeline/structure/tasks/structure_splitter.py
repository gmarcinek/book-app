import luigi
import json
import fitz
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from .structure_detector import StructureDetector


class StructureSplitter(StructuredTask):
    """
    Split document based on detected structure from Surya
    """
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "structure"
    
    @property
    def task_name(self) -> str:
        return "structure_splitter"
    
    def requires(self):
        return StructureDetector(file_path=self.file_path)
    
    def run(self):
        print("✂️ Starting structure-based document splitting...")
        
        # Load structure detection results
        with self.input().open('r') as f:
            structure_data = json.load(f)
        
        if structure_data.get("status") != "success":
            raise ValueError("Structure detection failed")
        
        # Load config
        config = self._load_config()
        
        # Split document based on detected headers
        sections = self._split_by_headers(structure_data, config)
        
        # Create output
        result = {
            "task_name": "StructureSplitter",
            "input_file": str(self.file_path),
            "status": "success",
            "sections_created": len(sections),
            "sections": sections,
            "splitting_method": "surya_structure_based",
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Document split into {len(sections)} sections")
    
    def _load_config(self):
        """Load splitter config"""
        # TODO: Load from config.yaml
        return {
            "split_on_levels": [1, 2],
            "min_section_pages": 1,
            "output_format": "pdf",
            "create_level_folders": True,
            "max_filename_length": 50
        }
    
    def _split_by_headers(self, structure_data, config):
        """Split document based on detected headers"""
        headers = structure_data["structure_data"]["headers"]
        split_levels = config.get("split_on_levels", [1, 2])
        
        # Filter headers by levels we want to split on
        split_headers = [h for h in headers if h.get("level") in split_levels]
        split_headers.sort(key=lambda h: (h['page'], h.get('y_position', 0)))
        
        if not split_headers:
            print("⚠️ No headers found for splitting")
            return []
        
        # Create output directory
        doc_name = Path(self.file_path).stem
        output_base = Path("output") / doc_name / "structure_sections"
        
        sections = []
        doc = fitz.open(self.file_path)
        
        try:
            # Create sections between headers
            for i, header in enumerate(split_headers):
                section = self._create_section(
                    doc, header, split_headers, i, output_base, config
                )
                if section:
                    sections.append(section)
        
        finally:
            doc.close()
        
        return sections
    
    def _create_section(self, doc, current_header, all_headers, header_index, output_base, config):
        """Create single section PDF"""
        start_page = current_header["page"]
        start_y = current_header.get("y_position", 0)
        level = current_header.get("level", 1)
        title = current_header["text"]
        
        # Find end boundary
        end_page = len(doc)  # Default to document end
        end_y = None
        
        # Look for next header of same or higher level
        for next_header in all_headers[header_index + 1:]:
            next_level = next_header.get("level", 1)
            if next_level <= level:  # Same or higher level ends current section
                end_page = next_header["page"]
                end_y = next_header.get("y_position")
                break
        
        # Create level-specific directory
        if config.get("create_level_folders", True):
            level_dir = output_base / f"level_{level}"
        else:
            level_dir = output_base
        
        level_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        safe_title = self._sanitize_filename(title, config.get("max_filename_length", 50))
        filename = f"section_{header_index:03d}_lvl{level}_{safe_title}.pdf"
        file_path = level_dir / filename
        
        # Create section PDF
        success = self._extract_section_pdf(
            doc, start_page, start_y, end_page, end_y, file_path
        )
        
        if success:
            return {
                "title": title,
                "filename": filename,
                "file_path": str(file_path),
                "start_page": start_page,
                "end_page": end_page,
                "level": level,
                "section_index": header_index,
                "splitting_method": "surya_coordinates"
            }
        
        return None
    
    def _extract_section_pdf(self, source_doc, start_page, start_y, end_page, end_y, output_path):
        """Extract section as PDF using coordinates"""
        try:
            section_doc = fitz.open()
            
            # Validate coordinates
            if start_page < 1 or start_page > len(source_doc):
                print(f"⚠️ Invalid start_page: {start_page}")
                return False
                
            if end_page < 1 or end_page > len(source_doc):
                end_page = len(source_doc)
                print(f"⚠️ Clamped end_page to: {end_page}")
            
            if start_page == end_page:
                # Same page section
                page = source_doc[start_page - 1]
                page_rect = page.rect
                
                # Validate Y coordinates
                safe_start_y = max(0, start_y or 0)
                safe_end_y = min(page_rect.height, end_y or page_rect.height)
                
                if safe_end_y <= safe_start_y:
                    # Invalid crop, use full page
                    section_doc.insert_pdf(source_doc, from_page=start_page - 1, to_page=start_page - 1)
                else:
                    # Create valid crop rectangle
                    crop_rect = fitz.Rect(0, safe_start_y, page_rect.width, safe_end_y)
                    
                    new_page = section_doc.new_page(
                        width=page_rect.width,
                        height=safe_end_y - safe_start_y
                    )
                    new_page.show_pdf_page(new_page.rect, source_doc, start_page - 1, clip=crop_rect)
            
            else:
                # Multi-page section
                # First page
                page = source_doc[start_page - 1]
                page_rect = page.rect
                
                if start_y and start_y < page_rect.height:
                    safe_start_y = max(0, start_y)
                    crop_rect = fitz.Rect(0, safe_start_y, page_rect.width, page_rect.height)
                    
                    new_page = section_doc.new_page(
                        width=page_rect.width,
                        height=page_rect.height - safe_start_y
                    )
                    new_page.show_pdf_page(new_page.rect, source_doc, start_page - 1, clip=crop_rect)
                else:
                    # Full first page
                    section_doc.insert_pdf(source_doc, from_page=start_page - 1, to_page=start_page - 1)
                
                # Middle pages (full pages)
                for page_num in range(start_page, min(end_page - 1, len(source_doc))):
                    section_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
                
                # Last page (cropped if end_y specified)
                if end_page <= len(source_doc):
                    last_page = source_doc[end_page - 1]
                    last_rect = last_page.rect
                    
                    if end_y and end_y > 0 and end_y < last_rect.height:
                        crop_rect = fitz.Rect(0, 0, last_rect.width, min(end_y, last_rect.height))
                        
                        new_page = section_doc.new_page(width=last_rect.width, height=min(end_y, last_rect.height))
                        new_page.show_pdf_page(new_page.rect, source_doc, end_page - 1, clip=crop_rect)
                    else:
                        # Full last page
                        section_doc.insert_pdf(source_doc, from_page=end_page - 1, to_page=end_page - 1)
            
            # Save section
            section_doc.save(str(output_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create section: {e}")
            return False
    
    def _sanitize_filename(self, title, max_length):
        """Sanitize title for filename"""
        import re
        
        # Replace problematic characters
        safe_title = re.sub(r'[<>:"/\\|?*\s]', '_', title)
        safe_title = re.sub(r'_+', '_', safe_title)
        safe_title = safe_title.strip('._')
        
        # Truncate if too long
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length].rstrip('_')
        
        return safe_title or "untitled"