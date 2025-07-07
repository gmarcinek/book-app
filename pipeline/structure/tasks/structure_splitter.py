import luigi
import json
import fitz
import re
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from pipeline.structure.tasks.semantic_structure_detector import SemanticStructureDetector
from pipeline.structure.config import get_splitter_config


class StructureSplitter(StructuredTask):
    """Split document based on detected structure from Surya"""
    
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "structure"
    
    @property
    def task_name(self) -> str:
        return "structure_splitter"
    
    def requires(self):
        return SemanticStructureDetector(file_path=self.file_path)
    
    def run(self):
        print("✂️ Starting structure-based document splitting...")
        
        # Load structure detection results
        with self.input().open('r') as f:
            structure_data = json.load(f)
        
        if structure_data.get("status") != "success":
            raise ValueError("Structure detection failed")
        
        # Load config
        config = get_splitter_config()
        
        # Split document based on detected blocks
        sections = self._split_by_blocks(structure_data, config)
        
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
    
    def _split_by_blocks(self, structure_data, config):
        """Split document based on detected large blocks"""
        large_blocks = structure_data["large_blocks"]
        
        if not large_blocks:
            print("⚠️ No large blocks found for splitting")
            return []
        
        print(f"📊 Found {len(large_blocks)} blocks to process")
        
        # Create output directory
        doc_name = Path(self.file_path).stem
        output_base = Path("output") / doc_name / "structure_sections"
        output_base.mkdir(parents=True, exist_ok=True)
        
        sections = []
        doc = fitz.open(self.file_path)
        
        try:
            # Create sections for each block
            for i, block in enumerate(large_blocks):
                section = self._create_section_from_block(
                    doc, block, i, output_base, config
                )
                if section:
                    sections.append(section)
                    print(f"📄 Created: {section['filename']}")
        
        finally:
            doc.close()
        
        return sections
    
    def _create_section_from_block(self, doc, block, block_index, output_base, config):
        """Create PDF section from single block"""
        page_num = block["page"]  # 1-indexed
        bbox = block["bbox"]
        
        # Calculate boundaries
        start_y = bbox[1]  # Top of block
        end_y = bbox[3]    # Bottom of block
        block_height = end_y - start_y
        
        # Create filename
        title = f"block_{block_index}"
        safe_title = self._sanitize_filename(title, config.get("max_filename_length", 50))
        filename = f"section_{block_index:03d}_{safe_title}.pdf"
        file_path = output_base / filename
        
        # Create section PDF with full width
        success = self._extract_block_pdf(doc, page_num, bbox, file_path)
        
        if success:
            merged_info = {}
            if 'merged_count' in block:
                merged_info = {
                    "merged_count": block['merged_count'],
                    "original_labels": block.get('original_labels', [])
                }
            
            return {
                "title": title,
                "filename": filename,
                "file_path": str(file_path),
                "page": page_num,
                "bbox": bbox,
                "block_index": block_index,
                "block_height": block_height,
                "block_area": block.get("area", 0),
                "splitting_method": "surya_blocks_full_width",
                **merged_info
            }
        
        return None
    
    def _extract_block_pdf(self, source_doc, page_num, bbox, output_path):
        """Extract single block as PDF with FULL WIDTH"""
        try:
            # Convert to 0-indexed for fitz
            page_idx = page_num - 1
            
            if page_idx >= len(source_doc):
                print(f"⚠️ Page {page_num} doesn't exist")
                return False
            
            source_page = source_doc[page_idx]
            page_rect = source_page.rect
            
            # ZAWSZE FULL WIDTH - tylko Y coordinates z bbox
            x1, y1, x2, y2 = bbox
            
            # Force full width
            safe_x1 = 0                    # ZAWSZE od lewej krawędzi
            safe_x2 = page_rect.width      # ZAWSZE do prawej krawędzi
            
            # Y coordinates z bbox (ale z safety)
            safe_y1 = max(0, y1) 
            safe_y2 = min(page_rect.height, y2)
            
            if safe_y2 <= safe_y1:
                print(f"⚠️ Invalid Y range: {y1}-{y2}")
                return False
            
            # Create crop rectangle - FULL WIDTH
            crop_rect = fitz.Rect(safe_x1, safe_y1, safe_x2, safe_y2)
            crop_width = safe_x2 - safe_x1  # = page_rect.width
            crop_height = safe_y2 - safe_y1
            
            print(f"🔪 Cropping: full width x {crop_height:.0f}px (Y: {safe_y1:.0f}-{safe_y2:.0f})")
            
            # Create new PDF with cropped content
            section_doc = fitz.open()
            new_page = section_doc.new_page(width=crop_width, height=crop_height)
            
            # Show cropped area on new page
            new_page.show_pdf_page(new_page.rect, source_doc, page_idx, clip=crop_rect)
            
            # Save section
            section_doc.save(str(output_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create section: {e}")
            return False
    
    def _sanitize_filename(self, title, max_length):
        """Sanitize title for filename"""
        # Replace problematic characters
        safe_title = re.sub(r'[<>:"/\\|?*\s]', '_', title)
        safe_title = re.sub(r'_+', '_', safe_title)
        safe_title = safe_title.strip('._')
        
        # Check for empty or only underscores
        if not safe_title or re.fullmatch(r'_+', safe_title):
            safe_title = "untitled"
        
        # Truncate if too long
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length].rstrip('_')
        
        return safe_title