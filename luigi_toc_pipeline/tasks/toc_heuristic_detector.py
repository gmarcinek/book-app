import luigi
import json
import re
import fitz
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from luigi_components.structured_task import StructuredTask

class TOCHeuristicDetector(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_heuristic_detector"
    
    def run(self):
        from luigi_toc_pipeline.config import load_config
        
        config = load_config()
        doc = fitz.open(self.file_path)
        result = {"toc_found": False}
        
        max_pages = min(config.get_task_setting("TOCDetector", "max_pages_to_scan", 20), len(doc))
        
        # Find TOC start and end coordinates using pattern matching
        toc_bounds = self._find_toc_coordinates_with_patterns(doc, max_pages)
        
        if toc_bounds:
            result = {
                "toc_found": True,
                "start_page": toc_bounds["start_page"],
                "start_y": toc_bounds["start_y"],
                "end_page": toc_bounds["end_page"],
                "end_y": toc_bounds["end_y"]
            }
        
        doc.close()
        
        with self.output().open('w') as f:
            json.dump(result, f)
    
    def _find_toc_coordinates_with_patterns(self, doc, max_pages):
        """Find TOC using flexible pattern matching"""
        start_coords = None
        end_coords = None
        
        for page_num in range(max_pages):
            page = doc[page_num]
            text_dict = page.get_text("dict")  # Get text with position info
            
            # Find TOC keyword position using patterns
            if not start_coords:
                start_coords = self._find_toc_start_with_patterns(text_dict, page_num)
            
            # If we found start, look for end on this and subsequent pages
            if start_coords:
                end_coords = self._find_toc_end(text_dict, page_num, start_coords)
                if end_coords:
                    break
        
        if start_coords and end_coords:
            return {
                "start_page": start_coords["page"],
                "start_y": start_coords["y"],
                "end_page": end_coords["page"], 
                "end_y": end_coords["y"]
            }
        
        return None
    
    def _find_toc_start_with_patterns(self, text_dict, page_num):
        """Find Y coordinate where TOC pattern appears - FLEXIBLE MATCHING"""
        
        # TOC patterns - ordered by priority (most specific first)
        toc_patterns = [
            # English patterns
            r'\b(?:table\s+of\s+)?contents?\b',
            r'\bchapter\s+contents?\b',
            r'\bcontents?\s+page\b',
            r'\bindex\b',
            
            # Polish patterns  
            r'\bspis\s+tre[śs]ci\b',
            r'\btre[śs][ćc]\b',
            
            # French patterns
            r'\bsommaire\b',
            r'\btable\s+des?\s+mati[èe]res?\b',
            
            # German patterns
            r'\binhaltsverzeichnis\b',
            r'\binhalt\b',
            
            # Generic patterns (last resort)
            r'\b\w*contents?\w*\b',
        ]
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    line_text_clean = line_text.strip().lower()
                    
                    # Try each pattern
                    for pattern in toc_patterns:
                        if re.search(pattern, line_text_clean, re.IGNORECASE):
                            print(f"🎯 TOC pattern found: '{pattern}' matches '{line_text_clean}'")
                            
                            # Save screenshot of this page for debug
                            self._save_debug_screenshot(page_num, pattern, line_text_clean)
                            
                            return {
                                "page": page_num,
                                "y": line["bbox"][1]  # Top Y coordinate of line
                            }
        
        return None
    
    def _save_debug_screenshot(self, page_num, pattern, matched_text):
        """Save cropped screenshot + extract text + base64 for JSON debug"""
        try:
            import base64
            
            # Create debug directory
            debug_dir = Path("output") / self.pipeline_name / self.task_name / "debug_screenshots"
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            # Open document and get page
            doc = fitz.open(self.file_path)
            page = doc[page_num]
            page_rect = page.rect
            
            # Find Y coordinate of matched text
            text_dict = page.get_text("dict")
            toc_y = None
            
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        
                        if re.search(pattern, line_text.strip().lower(), re.IGNORECASE):
                            toc_y = line["bbox"][1]  # Top Y of TOC line
                            break
                if toc_y:
                    break
            
            # Create crop area around TOC (±300 pixels)
            if toc_y:
                crop_height = 600  # Total height around TOC
                crop_top = max(0, toc_y - 150)  # 150px above TOC
                crop_bottom = min(page_rect.height, toc_y + 450)  # 450px below TOC
                
                # Crop rectangle: full width, limited height around TOC
                crop_rect = fitz.Rect(0, crop_top, page_rect.width, crop_bottom)
            else:
                # Fallback: crop top portion of page
                crop_rect = fitz.Rect(0, 0, page_rect.width, min(600, page_rect.height))
            
            # Extract text from cropped area
            cropped_text = page.get_text(clip=crop_rect).strip()
            
            # Create screenshot with good resolution
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=crop_rect)
            
            # Save PNG screenshot
            screenshot_file = debug_dir / f"toc_found_page_{page_num + 1}_cropped.png"
            pix.save(str(screenshot_file))
            
            # Convert to base64
            img_bytes = pix.tobytes("png")
            image_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Create JSON debug data
            debug_data = {
                "page_num": page_num + 1,
                "pattern_matched": pattern,
                "matched_text": matched_text,
                "crop_coordinates": {
                    "top": crop_top,
                    "bottom": crop_bottom,
                    "width": page_rect.width,
                    "height": crop_bottom - crop_top
                },
                "extracted_text": cropped_text,
                "image_base64": image_base64,
                "screenshot_file": str(screenshot_file),
                "debug_info": {
                    "toc_y_coordinate": toc_y,
                    "page_dimensions": {
                        "width": page_rect.width,
                        "height": page_rect.height
                    }
                }
            }
            
            # Save JSON debug file
            json_file = debug_dir / f"toc_debug_page_{page_num + 1}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            doc.close()
            
            print(f"📸 Debug screenshot saved: {screenshot_file}")
            print(f"📋 Debug JSON saved: {json_file}")
            print(f"    Pattern: {pattern}")
            print(f"    Matched: '{matched_text}'")
            print(f"    Crop area: Y={crop_top:.0f}-{crop_bottom:.0f}")
            print(f"    Text length: {len(cropped_text)} chars")
            
        except Exception as e:
            print(f"⚠️ Failed to save debug screenshot: {e}")
    
    def _find_toc_end(self, text_dict, page_num, start_coords):
        """Find Y coordinate where TOC ends (heuristic)"""
        toc_entries_found = 0
        last_entry_y = start_coords["y"]
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_y = line["bbox"][1]
                    
                    # Only look at lines after TOC start
                    if line_y <= start_coords["y"]:
                        continue
                    
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    # Check if line looks like TOC entry
                    if self._looks_like_toc_entry(line_text):
                        toc_entries_found += 1
                        last_entry_y = line_y
                    elif toc_entries_found >= 3:  # Found enough entries, this might be end
                        # Check if line looks like start of content (not TOC)
                        if self._looks_like_content_start(line_text):
                            return {
                                "page": page_num,
                                "y": line_y
                            }
        
        # If no clear end found but we have entries, end after last entry
        if toc_entries_found >= 3:
            return {
                "page": page_num,
                "y": last_entry_y + 50  # Add some padding
            }
        
        return None
    
    def _looks_like_toc_entry(self, text):
        """Check if text looks like a TOC entry - IMPROVED PATTERNS"""
        text_clean = text.strip()
        
        if len(text_clean) < 3:  # Too short
            return False
        
        # TOC entry patterns
        toc_entry_patterns = [
            # Classic dot leaders: "Chapter 1 ......... 15"
            r'.+\.{3,}\s*\d+\s*$',
            
            # Spaces with page numbers: "Chapter 1        15"
            r'.+\s{3,}\d+\s*$',
            
            # Tab-separated: "Chapter 1	15"
            r'.+\t+\d+\s*$',
            
            # Page number in parentheses: "Chapter 1 (15)"
            r'.+\s*\(\d+\)\s*$',
            
            # Just text followed by number: "Introduction 5"
            r'^[A-Za-z].+\s+\d{1,3}\s*$',
            
            # Numbered sections: "1.1 Introduction 5"
            r'^\d+\.?\d*\.?\s*.+\s+\d+\s*$',
        ]
        
        for pattern in toc_entry_patterns:
            if re.match(pattern, text_clean):
                return True
        
        return False
    
    def _looks_like_content_start(self, text):
        """Check if text looks like start of document content - IMPROVED"""
        text_clean = text.strip().lower()
        
        if len(text_clean) < 3:
            return False
        
        # Content start patterns
        content_patterns = [
            # Polish
            r'^(rozdział|rozdzial)\s+\d+',
            r'^(część|czesc)\s+\d+', 
            r'^(wprowadzenie|wstęp|wstep)',
            r'^§\s*\d+',
            r'^art\.\s*\d+',
            
            # English  
            r'^(chapter|part)\s+\d+',
            r'^(introduction|preface)',
            r'^section\s+\d+',
            
            # Generic patterns
            r'^\d+\.\s+[a-z]',  # "1. introduction"
            r'^[ivx]+\.\s+[a-z]',  # "i. introduction" (roman numerals)
        ]
        
        for pattern in content_patterns:
            if re.match(pattern, text_clean):
                return True
        
        return False