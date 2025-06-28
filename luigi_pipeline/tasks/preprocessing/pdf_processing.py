import luigi
import json
import hashlib
import base64
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

from .file_router import FileRouter


class PDFProcessing(luigi.Task):
    """
    Processes PDF files by extracting pages as images and text
    
    Output: JSON with base64 images and extracted text for each page
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
        
        # Process PDF
        doc = fitz.open(self.file_path)
        pages_data = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Screenshot to PNG bytes with higher resolution
            # Default matrix is 72 DPI, scale up for better quality
            zoom = 2.0  # 144 DPI (2x zoom)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Extract text (no OCR - direct from PDF)
            text = page.get_text()
            
            pages_data.append({
                "page_num": page_num + 1,
                "image_base64": img_base64,
                "extracted_text": text,
                "text_length": len(text),
                "has_text": len(text.strip()) > 0
            })
        
        doc.close()
        
        # Output JSON
        output_data = {
            "task_name": "PDFProcessing", 
            "input_file": str(self.file_path),
            "status": "success",
            "pages_count": len(pages_data),
            "pages": pages_data,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)