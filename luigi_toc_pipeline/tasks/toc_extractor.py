import luigi
import json
import fitz
from pathlib import Path
import sys

from luigi_components.structured_task import StructuredTask
sys.path.append(str(Path(__file__).parent.parent.parent))
from .toc_heuristic_detector import TOCHeuristicDetector

class TOCExtractor(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_extractor"
    
    def requires(self):
        return TOCHeuristicDetector(file_path=self.file_path)
    
    def run(self):
        # Load TOC coordinates from heuristic detector
        with self.input().open('r') as f:
            toc_data = json.load(f)
        
        if not toc_data.get("toc_found", False):
            result = {"toc_extracted": False, "reason": "no_toc_found"}
        else:
            # Extract TOC to separate PDF
            toc_pdf_path = self._extract_toc_pdf(toc_data)
            result = {
                "toc_extracted": True,
                "toc_pdf_path": str(toc_pdf_path),
                "coordinates": {
                    "start_page": toc_data["start_page"],
                    "start_y": toc_data["start_y"],
                    "end_page": toc_data["end_page"],
                    "end_y": toc_data["end_y"]
                }
            }
        
        with self.output().open('w') as f:
            json.dump(result, f)
    
    def _extract_toc_pdf(self, toc_data):
        """Extract TOC section to separate PDF using coordinates"""
        source_doc = fitz.open(self.file_path)
        
        # Create new PDF for TOC
        toc_doc = fitz.open()
        
        start_page = toc_data["start_page"]
        end_page = toc_data["end_page"]
        start_y = toc_data["start_y"]
        end_y = toc_data["end_y"]
        
        for page_num in range(start_page, end_page + 1):
            source_page = source_doc[page_num]
            page_rect = source_page.rect
            
            # Determine crop coordinates for this page
            if page_num == start_page and page_num == end_page:
                # Single page TOC
                crop_rect = fitz.Rect(0, start_y, page_rect.width, end_y)
            elif page_num == start_page:
                # First page - crop from start_y to bottom
                crop_rect = fitz.Rect(0, start_y, page_rect.width, page_rect.height)
            elif page_num == end_page:
                # Last page - crop from top to end_y
                crop_rect = fitz.Rect(0, 0, page_rect.width, end_y)
            else:
                # Middle page - full page
                crop_rect = page_rect
            
            # Create new page in TOC document
            new_page = toc_doc.new_page(width=page_rect.width, height=crop_rect.height)
            
            # Copy content from cropped area
            new_page.show_pdf_page(new_page.rect, source_doc, page_num, clip=crop_rect)
        
        # Save TOC PDF
        source_path = Path(self.file_path)
        toc_filename = f"{source_path.stem}_TOC.pdf"
        
        # Create task-specific directory
        task_dir = Path("output") / self.pipeline_name / self.task_name
        task_dir.mkdir(parents=True, exist_ok=True)
        
        toc_pdf_path = task_dir / toc_filename
        toc_doc.save(str(toc_pdf_path))
        
        source_doc.close()
        toc_doc.close()
        
        print(f"✅ TOC extracted to: {toc_pdf_path}")
        return toc_pdf_path