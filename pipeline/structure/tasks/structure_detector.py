import luigi
import json
import sys
import fitz
from pathlib import Path
from datetime import datetime
from PIL import Image
import io

# Add parent directories for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from ocr import SuryaClient


class StructureDetector(StructuredTask):
    """
    Detect document structure using Surya layout analysis
    """
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "structure"
    
    @property
    def task_name(self) -> str:
        return "structure_detector"
    
    def run(self):
        print("🔍 Starting Surya structure detection...")
        
        # Load config
        config = self._load_config()
        
        # Initialize Surya OCR client
        languages = config.get("languages", ["en", "pl"])
        surya_client = SuryaClient(languages)
        
        # Extract PDF pages and analyze structure
        structure_data = self._analyze_document_structure(surya_client, config)
        
        # Create output
        result = {
            "task_name": "StructureDetector",
            "input_file": str(self.file_path),
            "status": "success",
            "structure_data": structure_data,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Structure detection complete: {len(structure_data.get('headers', []))} headers found")
    
    def _load_config(self):
        """Load structure detection config"""
        return {
            "languages": ["en", "pl"],
            "min_header_confidence": 0.7,
            "detect_levels": 3,
            "max_pages": 1000
        }
    
    def _analyze_document_structure(self, surya_client, config):
        """Analyze document structure using Surya"""
        print(f"📊 Analyzing structure of: {Path(self.file_path).name}")
        
        doc = fitz.open(self.file_path)
        max_pages = min(len(doc), config.get("max_pages", 1000))
        
        all_headers = []
        all_tables = []
        page_images = []
        
        # Extract pages as images
        print(f"🖼️ Extracting {max_pages} pages as images...")
        for page_num in range(max_pages):
            page = doc[page_num]
            # Convert to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x zoom
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            page_images.append(img)
        
        # Run Surya analysis on all pages
        print(f"🤖 Running Surya layout analysis...")
        ocr_results = surya_client.process_pages(page_images)
        
        # Extract structure from Surya results
        for page_idx, result in enumerate(ocr_results):
            page_num = page_idx + 1
            
            # Extract headers based on layout
            page_headers = self._extract_headers_from_page(result, page_num, config)
            all_headers.extend(page_headers)
            
            # Extract tables
            page_tables = self._extract_tables_from_page(result, page_num)
            all_tables.extend(page_tables)
        
        doc.close()
        
        # Sort headers by page and position
        all_headers.sort(key=lambda h: (h['page'], h.get('y_position', 0)))
        
        print(f"📋 Found {len(all_headers)} headers, {len(all_tables)} tables")
        
        return {
            "headers": all_headers,
            "tables": all_tables,
            "total_pages": max_pages,
            "structure_summary": f"{len(all_headers)} headers across {max_pages} pages"
        }
    
    def _extract_headers_from_page(self, surya_result, page_num, config):
        """Extract headers from Surya layout analysis using real semantic labels"""
        headers = []
        
        # Get layout info from Surya
        layout = surya_result.get('layout', [])
        text_lines = surya_result.get('text_lines', [])
        min_confidence = config.get('min_header_confidence', 0.7)
        
        print(f"🔍 Page {page_num} debug:")
        print(f"   Layout elements: {len(layout)}")
        print(f"   Text lines: {len(text_lines)}")
        
        # Debug: Show all layout labels found
        labels_found = [elem.get('label', 'unknown') for elem in layout]
        label_counts = {}
        for label in labels_found:
            label_counts[label] = label_counts.get(label, 0) + 1
        print(f"   Layout labels: {label_counts}")
        
        # Use REAL Surya layout detection
        for layout_element in layout:
            label = layout_element.get('label', '')
            confidence = layout_element.get('confidence', 0.0)
            bbox = layout_element.get('bbox', [])
            
            # Filter by semantic labels and confidence
            if label in ['Section-header'] and confidence >= min_confidence:
                # Find corresponding text for this layout element
                header_text = self._find_text_for_layout_element(layout_element, text_lines)
                
                if header_text and len(header_text.strip()) > 3:
                    level = self._estimate_level_from_layout(layout_element, text_lines)
                    
                    headers.append({
                        "text": header_text.strip(),
                        "page": page_num,
                        "bbox": bbox,
                        "y_position": bbox[1] if len(bbox) >= 2 else 0,
                        "level": level,
                        "type": "header",
                        "surya_label": label,
                        "confidence": confidence
                    })
                    
                    print(f"   ✅ Header found: '{header_text[:50]}...' (level {level}, conf: {confidence:.2f})")
        
        print(f"   📋 Total headers on page {page_num}: {len(headers)}")
        return headers
    
    def _extract_tables_from_page(self, surya_result, page_num):
        """Extract tables from Surya result using semantic labels"""
        tables = []
        
        layout = surya_result.get('layout', [])
        
        # Look for table elements with proper labels
        for layout_element in layout:
            label = layout_element.get('label', '')
            confidence = layout_element.get('confidence', 0.0)
            bbox = layout_element.get('bbox', [])
            
            if label == 'Table' and confidence >= 0.5:
                tables.append({
                    "page": page_num,
                    "bbox": bbox,
                    "type": "table",
                    "confidence": confidence,
                    "surya_label": label
                })
        
        return tables
    
    def _find_text_for_layout_element(self, layout_element, text_lines):
        """Find text that overlaps with layout element"""
        layout_bbox = layout_element.get('bbox', [])
        if len(layout_bbox) < 4:
            return ""
        
        # Find overlapping text lines
        overlapping_texts = []
        for text_line in text_lines:
            text_bbox = text_line.get('bbox', [])
            text_content = text_line.get('text', '')
            
            if len(text_bbox) >= 4 and self._bboxes_overlap(layout_bbox, text_bbox):
                overlapping_texts.append(text_content)
        
        return " ".join(overlapping_texts)
    
    def _bboxes_overlap(self, bbox1, bbox2):
        """Check if two bboxes overlap"""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)
    
    def _estimate_level_from_layout(self, layout_element, text_lines):
        """Estimate hierarchy level from layout properties"""
        bbox = layout_element.get('bbox', [])
        if len(bbox) < 4:
            return 2
        
        # Use bbox height as fallback heuristic
        height = bbox[3] - bbox[1]
        y_position = bbox[1]
        
        # Larger text or higher on page = higher level
        if height > 25 or y_position < 100:
            return 1
        elif height > 18:
            return 2
        else:
            return 3