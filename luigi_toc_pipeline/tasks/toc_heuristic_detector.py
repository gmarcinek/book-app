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
        
        max_pages = min(config.get_task_setting("TOCDetector", "max_pages_to_scan", 10), len(doc))
        keywords = [kw.lower() for kw in config.get_task_setting("TOCDetector", "toc_keywords", [])]
        
        # Find TOC start and end coordinates
        toc_bounds = self._find_toc_coordinates(doc, max_pages, keywords)
        
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
    
    def _find_toc_coordinates(self, doc, max_pages, keywords):
        """Find precise Y coordinates where TOC starts and ends"""
        start_coords = None
        end_coords = None
        
        for page_num in range(max_pages):
            page = doc[page_num]
            text_dict = page.get_text("dict")  # Get text with position info
            
            # Find TOC keyword position
            if not start_coords:
                start_coords = self._find_toc_start(text_dict, keywords, page_num)
            
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
    
    def _find_toc_start(self, text_dict, keywords, page_num):
        """Find Y coordinate where TOC keyword appears"""
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    for span in line["spans"]:
                        line_text += span["text"]
                    
                    if any(keyword in line_text.lower() for keyword in keywords):
                        return {
                            "page": page_num,
                            "y": line["bbox"][1]  # Top Y coordinate of line
                        }
        return None
    
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
        """Check if text looks like a TOC entry"""
        # Pattern: text with page numbers
        pattern = r'.+\.{3,}\s*\d+|.+\s{3,}\d+\s*$'
        return bool(re.search(pattern, text))
    
    def _looks_like_content_start(self, text):
        """Check if text looks like start of document content"""
        # Heuristics for content start
        content_patterns = [
            r'^(rozdział|chapter)\s+\d+',
            r'^(część|part)\s+\d+',
            r'^(wprowadzenie|wstęp|introduction)',
            r'^§\s*\d+',
            r'^art\.\s*\d+'
        ]
        
        text_lower = text.lower().strip()
        return any(re.match(pattern, text_lower) for pattern in content_patterns)