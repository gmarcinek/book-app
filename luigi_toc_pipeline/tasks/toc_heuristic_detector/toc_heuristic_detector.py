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
        
        # Initialize debug utils
        debug_utils = TOCDebugUtils(self.pipeline_name, self.task_name)
        
        max_pages = min(config.get_task_setting("TOCDetector", "max_pages_to_scan", 1000), len(doc))
        
        # Stage 1: Pattern-based detection
        pattern_detector = TOCPatternDetector(doc, max_pages, config)
        toc_candidates = pattern_detector.find_all_toc_candidates()
        
        print(f"🔍 Found {len(toc_candidates['certain'])} certain TOCs")
        print(f"🔍 Found {len(toc_candidates['uncertain'])} uncertain TOCs") 
        print(f"🔍 Rejected {len(toc_candidates['rejected'])} false positives")
        
        # Save debug info for all candidates
        debug_utils.save_detection_summary(toc_candidates, self.file_path)
        
        # Stage 2: LLM processing for ALL candidates (certain + uncertain)
        all_candidates = toc_candidates['certain'] + toc_candidates['uncertain']
        processed_tocs = []
        
        if all_candidates:
            print(f"🤖 Starting LLM processing for {len(all_candidates)} TOC candidates...")
            
            verification_engine = TOCVerificationEngine(self.file_path, config)
            processed_tocs = verification_engine.process_all_candidates(all_candidates)
            
            # Check if processing was aborted
            if len(processed_tocs) == 0 and len(all_candidates) > 0:
                if len(all_candidates) > 25:
                    reason = "too_many_candidates"
                    details = f"{len(all_candidates)} > 25 limit"
                else:
                    reason = "too_many_rejections_or_failures"
                    details = "LLM rejected/failed too many candidates"
                
                print(f"🚨 LLM processing failed: {reason}")
                result = {
                    "status": "processing_failed",
                    "reason": reason,
                    "details": details,
                    "candidates_count": len(all_candidates),
                    "toc_found": False
                }
                
                with self.output().open('w') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                doc.close()
                return
        
        # Select best TOC and create final result
        if processed_tocs:
            final_result = self._select_best_toc(processed_tocs)
            
            # Add debug and statistics info
            final_result.update({
                "status": "success",
                "certain_count": len(toc_candidates['certain']),
                "uncertain_count": len(toc_candidates['uncertain']),
                "processed_count": len(processed_tocs),
                "rejected_count": len(toc_candidates['rejected']),
                "debug_stats": debug_utils.get_debug_stats()
            })
            
            print(f"🎯 Selected best TOC: page {final_result['start_page']}-{final_result['end_page']}")
            
        else:
            final_result = {
                "status": "success",
                "toc_found": False,
                "reason": "no_confirmed_tocs_after_processing",
                "certain_count": len(toc_candidates['certain']),
                "uncertain_count": len(toc_candidates['uncertain']),
                "processed_count": len(processed_tocs),
                "rejected_count": len(toc_candidates['rejected']),
                "debug_stats": debug_utils.get_debug_stats()
            }
            
            print("❌ No confirmed TOCs found")
        
        # Save final result
        with self.output().open('w') as f:
            json.dump(final_result, f, indent=2, ensure_ascii=False)
        
        doc.close()
    
    def _select_best_toc(self, confirmed_tocs):
        """Select best TOC from confirmed candidates"""
        if not confirmed_tocs:
            return {"toc_found": False, "reason": "no_confirmed_tocs"}
        
        # Prioritize: earliest page, most entries, best confidence
        best_toc = min(confirmed_tocs, key=lambda t: (
            t['start_page'], 
            -t.get('entry_count', 0),
            -t.get('toc_ratio', 0.0)
        ))
        
        print(f"📋 Best TOC candidate:")
        print(f"   Page: {best_toc['start_page']}-{best_toc['end_page']}")
        print(f"   Entries: {best_toc.get('entry_count', 0)}")
        print(f"   Ratio: {best_toc.get('toc_ratio', 0.0):.2f}")
        print(f"   Method: {best_toc.get('method', 'unknown')}")
        
        return {
            "toc_found": True,
            "start_page": best_toc['start_page'],
            "start_y": best_toc['start_y'],
            "end_page": best_toc['end_page'],
            "end_y": best_toc['end_y'],
            "confidence": best_toc.get('confidence', 'high'),
            "detection_method": best_toc.get('method', 'pattern'),
            "entry_count": best_toc.get('entry_count', 0),
            "toc_ratio": best_toc.get('toc_ratio', 0.0),
            "candidate_id": best_toc.get('candidate_id', 'unknown'),
            "pattern_matched": best_toc.get('pattern_matched', ''),
            "matched_text": best_toc.get('matched_text', ''),
            "toc_entries": best_toc.get('toc_entries', []),
            "toc_entries_count": best_toc.get('toc_entries_count', 0)
        }