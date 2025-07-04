import luigi
import json
import base64
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF
import PyPDF2

from luigi_components.structured_task import StructuredTask
from luigi_pipeline.tasks.preprocessing.file_router.file_router import FileRouter


class PDFProcessing(StructuredTask):
    """
    Hybrid PDF processing: PyMuPDF screenshots + PyPDF2 clean text extraction
    Saves screenshots to task-specific directory
    """
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "pdf_processing"
    
    def requires(self):
        return FileRouter(file_path=self.file_path)
    
    def run(self):
        # Validate strategy  
        with self.input().open('r') as f:
            input_data = json.load(f)
        
        if input_data.get("strategy") != "pdf_processing":
            raise ValueError(f"Wrong strategy: {input_data.get('strategy')}")
        
        # Create task-specific screenshot directory
        task_dir = Path("output") / self.pipeline_name / self.task_name
        screenshot_dir = task_dir / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Process PDF
        pages_data = self._process_pdf(screenshot_dir)
        
        # Output
        result = {
            "task_name": "PDFProcessing", 
            "input_file": str(self.file_path),
            "status": "success",
            "pages_count": len(pages_data),
            "pages_with_text": sum(1 for p in pages_data if p["has_text"]),
            "pages_with_images": sum(1 for p in pages_data if "image_base64" in p),
            "pages_with_screenshot_files": sum(1 for p in pages_data if "screenshot_file" in p),
            "screenshot_directory": str(screenshot_dir),
            "screenshot_format": "jpeg_adaptive_zoom_quality_70",
            "text_extraction_method": "hybrid_pypdf2_pymupdf",
            "pages": pages_data,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
    def _process_pdf(self, screenshot_dir):
        """Process PDF with hybrid approach"""
        fitz_doc = fitz.open(self.file_path)
        pages_data = []
        
        # Try PyPDF2
        pypdf_reader = None
        pdf_file_handle = None
        
        try:
            pdf_file_handle = open(self.file_path, 'rb')
            pypdf_reader = PyPDF2.PdfReader(pdf_file_handle)
            if pypdf_reader.is_encrypted:
                pypdf_reader = None
        except Exception as e:
            print(f"PyPDF2 failed: {e}, using PyMuPDF fallback")
            pypdf_reader = None
        
        # Process pages
        for page_num in range(len(fitz_doc)):
            page_data = self._process_single_page(page_num, fitz_doc, pypdf_reader, screenshot_dir)
            pages_data.append(page_data)
        
        # Cleanup
        fitz_doc.close()
        if pdf_file_handle:
            pdf_file_handle.close()
        
        return pages_data
    
    def _process_single_page(self, page_num, fitz_doc, pypdf_reader, screenshot_dir):
        """Process single page with adaptive zoom and file save"""
        page_data = {
            "page_num": page_num + 1,
            "text_length": 0,
            "has_text": False
        }
        
        # Screenshot with adaptive zoom
        try:
            fitz_page = fitz_doc[page_num]
            page_rect = fitz_page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Adaptive zoom - target 1200px width
            target_width = 1200
            adaptive_zoom = target_width / page_width
            adaptive_zoom = max(0.5, min(3.0, adaptive_zoom))
            
            mat = fitz.Matrix(adaptive_zoom, adaptive_zoom)
            pix = fitz_page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("jpeg", jpg_quality=70)
            
            # Save as base64 in JSON
            page_data["image_base64"] = base64.b64encode(img_bytes).decode('utf-8')
            
            # Save as JPEG file in task directory
            screenshot_filename = f"page_{page_num + 1:03d}.jpg"
            screenshot_path = screenshot_dir / screenshot_filename
            
            with open(screenshot_path, 'wb') as f:
                f.write(img_bytes)
            
            page_data["screenshot_file"] = str(screenshot_path)
            page_data["screenshot_filename"] = screenshot_filename
            page_data["screenshot_format"] = f"jpeg_quality_70_adaptive_zoom_{adaptive_zoom:.2f}"
            page_data["page_dimensions"] = {"width": page_width, "height": page_height}
            
        except Exception as e:
            print(f"Screenshot failed for page {page_num + 1}: {e}")
        
        # Text extraction - PyPDF2 first, PyMuPDF fallback
        extracted_text = ""
        
        if pypdf_reader:
            try:
                pypdf_page = pypdf_reader.pages[page_num]
                extracted_text = pypdf_page.extract_text()
                page_data["text_source"] = "pypdf2"
            except Exception as e:
                print(f"PyPDF2 text extraction failed for page {page_num + 1}: {e}")
        
        # Fallback to PyMuPDF
        if not extracted_text.strip():
            try:
                fitz_page = fitz_doc[page_num]
                extracted_text = fitz_page.get_text()
                page_data["text_source"] = "pymupdf_fallback"
            except Exception as e:
                print(f"PyMuPDF fallback failed for page {page_num + 1}: {e}")
                page_data["text_source"] = "failed"
        
        extracted_text = extracted_text.strip()
        page_data["text"] = extracted_text
        page_data["text_length"] = len(extracted_text)
        page_data["has_text"] = len(extracted_text) > 0
        
        return page_data