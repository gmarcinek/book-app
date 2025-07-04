import luigi
import json
import fitz
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from .pattern_detector import TOCPatternDetector
from .verification_engine import TOCVerificationEngine
from .debug_utils import TOCDebugUtils


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
        
        max_pages = min(config.get_task_setting("TOCDetector", "max_pages_to_scan", 1000), len(doc))
        
        # Stage 1: Pattern-based detection
        pattern_detector = TOCPatternDetector(doc, max_pages, config)
        toc_candidates = pattern_detector.find_all_toc_candidates()
        
        print(f"🔍 Found {len(toc_candidates['certain'])} certain TOCs")
        print(f"❓ Found {len(toc_candidates['uncertain'])} uncertain TOCs") 
        print(f"❌ Rejected {len(toc_candidates['rejected'])} false positives")
        
        # Stage 2: LLM verification for uncertain TOCs
        if toc_candidates['uncertain']:
            print(f"🤖 Starting LLM verification for {len(toc_candidates['uncertain'])} uncertain TOCs...")
            
            verification_engine = TOCVerificationEngine(self.file_path, config)
            verified_tocs = verification_engine.verify_uncertain_tocs(toc_candidates['uncertain'])
            
            # Check if verification was aborted
            if len(verified_tocs) == 0 and len(toc_candidates['uncertain']) > 0:
                if len(toc_candidates['uncertain']) > 25:
                    reason = "too_many_uncertain_candidates"
                    details = f"{len(toc_candidates['uncertain'])} > 25 limit"
                else:
                    reason = "too_many_rejections"
                    details = "LLM rejected 4+ candidates, likely bad pattern detection"
                
                print(f"🚨 Verification failed: {reason}")
                result = {
                    "status": "verification_failed",
                    "reason": reason,
                    "details": details,
                    "uncertain_count": len(toc_candidates['uncertain']),
                    "toc_found": False
                }
            else:
                # Normal flow - merge verified TOCs with certain ones
                toc_candidates['certain'].extend(verified_tocs)
                print(f"✅ After verification: {len(toc_candidates['certain'])} confirmed TOCs")
                
                result = {
                    "status": "success",
                    "toc_found": len(toc_candidates['certain']) > 0,
                    "certain_count": len(toc_candidates['certain']),
                    "verified_count": len(verified_tocs)
                }
        else:
            # No uncertain TOCs to verify
            result = {
                "status": "success", 
                "toc_found": len(toc_candidates['certain']) > 0,
                "certain_count": len(toc_candidates['certain'])
            }
        
        # Save result
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        doc.close()
    
    def _select_best_toc(self, certain_tocs):
        """Select best TOC from confirmed candidates"""
        if not certain_tocs:
            return {"toc_found": False, "reason": "no_confirmed_tocs"}
        
        # Prioritize: earliest page, most entries, best confidence
        best_toc = min(certain_tocs, key=lambda t: (t['start_page'], -t.get('entry_count', 0)))
        
        return {
            "toc_found": True,
            "start_page": best_toc['start_page'],
            "start_y": best_toc['start_y'],
            "end_page": best_toc['end_page'],
            "end_y": best_toc['end_y'],
            "confidence": best_toc.get('confidence', 'high'),
            "detection_method": best_toc.get('method', 'pattern'),
            "entry_count": best_toc.get('entry_count', 0)
        }