import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import fitz


class TOCDebugUtils:
    """Debug utilities for TOC detection - screenshots and summaries"""
    
    def __init__(self, pipeline_name: str, task_name: str, document_name: str):
        """Initialize debug utils with document-specific directory"""
        self.pipeline_name = pipeline_name
        self.task_name = task_name  
        self.document_name = document_name
        
        # Create document-specific debug directory (not task-specific)
        self.debug_dir = Path("output") / document_name / "debug"
        self.debug_dir.mkdir(parents=True, exist_ok=True)
    
    def save_detection_summary(self, toc_candidates: Dict[str, List[Dict]], pdf_path: str):
        """Save comprehensive summary of all TOC detection results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create summary data
        summary = {
            "timestamp": timestamp,
            "pdf_file": str(pdf_path),
            "detection_summary": {
                "certain_tocs": len(toc_candidates['certain']),
                "uncertain_tocs": len(toc_candidates['uncertain']),
                "rejected_tocs": len(toc_candidates['rejected']),
                "total_candidates": len(toc_candidates['certain']) + len(toc_candidates['uncertain']) + len(toc_candidates['rejected'])
            },
            "candidates": toc_candidates
        }
        
        # Save JSON summary
        summary_file = self.debug_dir / f"toc_detection_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Debug summary saved: {summary_file}")
        
        # Save screenshots for all candidates
        self._save_candidate_screenshots(toc_candidates, pdf_path, timestamp)
        
        return summary_file
    
    def _save_candidate_screenshots(self, toc_candidates: Dict[str, List[Dict]], 
                                  pdf_path: str, timestamp: str):
        """Save debug screenshots for all TOC candidates"""
        doc = fitz.open(pdf_path)
        screenshots_saved = 0
        
        for category, candidates in toc_candidates.items():
            for i, candidate in enumerate(candidates):
                try:
                    screenshot_data = self._create_candidate_screenshot(doc, candidate, category, i, timestamp)
                    if screenshot_data:
                        screenshots_saved += 1
                        
                except Exception as e:
                    print(f"⚠️ Failed to save screenshot for {category} candidate {i}: {e}")
        
        doc.close()
        print(f"📸 Saved {screenshots_saved} debug screenshots")
    
    def _create_candidate_screenshot(self, doc: fitz.Document, candidate: Dict, 
                                   category: str, index: int, timestamp: str) -> Dict[str, Any]:
        """Create debug screenshot for single TOC candidate"""
        start_page = candidate['start_page']
        start_y = candidate['start_y']
        
        try:
            page = doc[start_page]
            page_rect = page.rect
            
            # Create crop area around TOC (±200 pixels)
            crop_height = 600  # Total height around TOC
            crop_top = max(0, start_y - 100)  # 100px above TOC
            crop_bottom = min(page_rect.height, start_y + 500)  # 500px below TOC
            
            # Crop rectangle
            crop_rect = fitz.Rect(0, crop_top, page_rect.width, crop_bottom)
            
            # Extract text from cropped area
            cropped_text = page.get_text(clip=crop_rect).strip()
            
            # Create high-quality screenshot
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=crop_rect)
            
            # Save PNG screenshot
            screenshot_filename = f"toc_{category}_{index}_page_{start_page + 1}_{timestamp}.png"
            screenshot_file = self.debug_dir / screenshot_filename
            pix.save(str(screenshot_file))
            
            # Convert to base64 for JSON
            img_bytes = pix.tobytes("png")
            image_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Create debug data
            debug_data = {
                "candidate_info": {
                    "category": category,
                    "index": index,
                    "candidate_id": candidate.get('candidate_id', f"{category}_{index}"),
                    "page_num": start_page + 1,
                    "pattern_matched": candidate.get('pattern_matched', ''),
                    "matched_text": candidate.get('matched_text', ''),
                    "entry_count": candidate.get('entry_count', 0),
                    "confidence": candidate.get('confidence', ''),
                    "method": candidate.get('method', 'pattern')
                },
                "crop_info": {
                    "crop_coordinates": {
                        "top": crop_top,
                        "bottom": crop_bottom,
                        "width": page_rect.width,
                        "height": crop_bottom - crop_top
                    },
                    "page_dimensions": {
                        "width": page_rect.width,
                        "height": page_rect.height
                    }
                },
                "extracted_text": cropped_text,
                "image_base64": image_base64,
                "screenshot_file": str(screenshot_file),
                "timestamp": timestamp
            }
            
            # Save individual JSON debug file
            json_filename = f"toc_{category}_{index}_debug_{timestamp}.json"
            json_file = self.debug_dir / json_filename
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            print(f"📸 Saved {category} TOC #{index}: {screenshot_filename}")
            return debug_data
            
        except Exception as e:
            print(f"❌ Screenshot failed for {category} candidate {index}: {e}")
            return None
    
    def save_verification_debug(self, candidate: Dict, verification_result: bool, 
                              llm_response: str, timestamp: str = None):
        """Save debug info for LLM verification"""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        debug_data = {
            "verification_result": verification_result,
            "candidate": candidate,
            "llm_response": llm_response,
            "timestamp": timestamp,
            "verification_model": "from_config"  # Could be enhanced
        }
        
        candidate_id = candidate.get('candidate_id', 'unknown')
        verification_file = self.debug_dir / f"verification_{candidate_id}_{timestamp}.json"
        
        with open(verification_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        
        result_emoji = "✅" if verification_result else "❌"
        print(f"🤖 {result_emoji} Verification debug saved: {verification_file.name}")
        
        return verification_file
    
    def get_debug_stats(self) -> Dict[str, Any]:
        """Get statistics about debug files created"""
        debug_files = list(self.debug_dir.glob("*"))
        
        return {
            "debug_directory": str(self.debug_dir),
            "total_debug_files": len(debug_files),
            "screenshots": len(list(self.debug_dir.glob("*.png"))),
            "json_files": len(list(self.debug_dir.glob("*.json"))),
            "summaries": len(list(self.debug_dir.glob("toc_detection_summary_*.json"))),
            "verifications": len(list(self.debug_dir.glob("verification_*.json")))
        }