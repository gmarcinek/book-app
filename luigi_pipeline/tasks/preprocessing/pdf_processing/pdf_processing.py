import luigi
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF - screenshots
import PyPDF2  # Clean text extraction

from ..file_router import FileRouter


class PDFProcessing(luigi.Task):
    """
    Hybrid PDF processing: PyMuPDF screenshots + PyPDF2 clean text extraction
    
    Output: JSON with base64 images and clean extracted text for each page
    Also saves individual JPEG screenshots to output directory
    """
    file_path = luigi.Parameter()
    
    def requires(self):
        return FileRouter(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/pdf_processing_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Validate strategy  
        with self.input().open('r') as f:
            strategy = f.read().strip()
        
        if strategy != "pdf_processing":
            raise ValueError(f"Wrong strategy: {strategy}")
        
        # Prepare screenshot directory
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        screenshot_dir = Path(f"output/screenshots_{file_hash}")
        screenshot_dir.mkdir(exist_ok=True)
        
        # Initialize PyMuPDF
        fitz_doc = fitz.open(self.file_path)
        
        # Initialize PyPDF2 with proper file handling
        pypdf_reader = None
        pdf_file_handle = None
        
        try:
            pdf_file_handle = open(self.file_path, 'rb')  # KEEP HANDLE OPEN
            pypdf_reader = PyPDF2.PdfReader(pdf_file_handle)
            
            # Check if PDF is encrypted
            if pypdf_reader.is_encrypted:
                print(f"⚠️ PDF is encrypted, using PyMuPDF text fallback")
                pypdf_reader = None
                
        except Exception as e:
            print(f"⚠️ PyPDF2 failed to open PDF: {e}, using PyMuPDF text fallback")
            pypdf_reader = None
        
        pages_data = []
        page_count = len(fitz_doc)
        
        for page_num in range(page_count):
            page_data = self._process_single_page(
                page_num, fitz_doc, pypdf_reader, screenshot_dir
            )
            pages_data.append(page_data)
        
        # Clean up resources
        fitz_doc.close()
        if pdf_file_handle:
            pdf_file_handle.close()  # CLOSE HANDLE PROPERLY
        
        # Output JSON with enhanced metadata
        output_data = {
            "task_name": "PDFProcessing", 
            "input_file": str(self.file_path),
            "status": "success",
            "pages_count": len(pages_data),
            "pages_with_text": sum(1 for p in pages_data if p["has_text"]),
            "pages_with_images": sum(1 for p in pages_data if "image_base64" in p),
            "pages_with_screenshot_files": sum(1 for p in pages_data if "screenshot_file" in p),
            "screenshot_directory": str(screenshot_dir),
            "screenshot_format": "jpeg_quality_60_zoom_0.5",
            "text_extraction_method": "hybrid_pypdf2_pymupdf",
            "pages": pages_data,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def _process_single_page(self, page_num, fitz_doc, pypdf_reader, screenshot_dir):
        """Process single page with hybrid approach + graceful error handling + small JPEG screenshot"""
        page_data = {
            "page_num": page_num + 1,
            "text_length": 0,
            "has_text": False
        }
        
        # 1. PyMuPDF Screenshot (SMALL size + JPEG compression for minimal tokens)
        try:
            fitz_page = fitz_doc[page_num]
            
            # Get page dimensions
            page_rect = fitz_page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Adaptive zoom based on page size
            # Target: ~1200px width for consistent readability
            target_width = 1200
            adaptive_zoom = target_width / page_width
            
            # Clamp zoom between reasonable bounds
            adaptive_zoom = max(0.5, min(3.0, adaptive_zoom))
            
            print(f"📐 Page {page_num + 1}: {page_width}x{page_height} → zoom {adaptive_zoom:.2f}")
            
            mat = fitz.Matrix(adaptive_zoom, adaptive_zoom)
            pix = fitz_page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("jpeg", jpg_quality=70)
            
            # Save as base64 in JSON
            page_data["image_base64"] = base64.b64encode(img_bytes).decode('utf-8')
            
            # Save as JPEG file
            screenshot_filename = f"page_{page_num + 1:03d}.jpg"
            screenshot_path = screenshot_dir / screenshot_filename
            
            with open(screenshot_path, 'wb') as f:
                f.write(img_bytes)
            
            page_data["screenshot_file"] = str(screenshot_path)
            page_data["screenshot_filename"] = screenshot_filename
            page_data["screenshot_format"] = f"jpeg_quality_70_adaptive_zoom_{adaptive_zoom:.2f}"
            page_data["page_dimensions"] = {"width": page_width, "height": page_height}
            page_data["target_width"] = target_width
            
        except Exception as e:
            print(f"⚠️ Screenshot failed for page {page_num + 1}: {e}")
            # Continue without screenshot
        
        # 2. PyPDF2 Clean Text Extraction (with PyMuPDF fallback)
        extracted_text = ""
        
        if pypdf_reader:
            try:
                pypdf_page = pypdf_reader.pages[page_num]
                extracted_text = pypdf_page.extract_text()
                page_data["text_source"] = "pypdf2"
            except Exception as e:
                print(f"⚠️ PyPDF2 text extraction failed for page {page_num + 1}: {e}")
                extracted_text = ""
        
        # Fallback to PyMuPDF if PyPDF2 failed or unavailable
        if not extracted_text.strip():
            try:
                fitz_page = fitz_doc[page_num]
                extracted_text = fitz_page.get_text()
                page_data["text_source"] = "pymupdf_fallback"
            except Exception as e:
                print(f"⚠️ PyMuPDF fallback text extraction failed for page {page_num + 1}: {e}")
                extracted_text = ""
                page_data["text_source"] = "failed"
        
        # Clean and set text data
        extracted_text = extracted_text.strip()
        page_data["extracted_text"] = extracted_text
        page_data["text_length"] = len(extracted_text)
        page_data["has_text"] = len(extracted_text) > 0
        
        return page_data