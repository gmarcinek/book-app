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
            final_result = self._merge_all_tocs(processed_tocs)
            
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
    
    def _merge_all_tocs(self, confirmed_tocs):
        """Merge all confirmed TOCs into single comprehensive TOC"""
        if not confirmed_tocs:
            return {"toc_found": False, "reason": "no_confirmed_tocs"}
        
        print(f"🔗 Merging {len(confirmed_tocs)} TOC sections...")
        
        # Collect all entries from all TOCs
        all_entries = []
        all_coordinates = []
        
        for toc in confirmed_tocs:
            entries = toc.get('toc_entries', [])
            print(f"   TOC at page {toc['start_page']}: {len(entries)} entries")
            
            all_entries.extend(entries)
            all_coordinates.append({
                'start_page': toc['start_page'],
                'end_page': toc['end_page'],
                'start_y': toc['start_y'],
                'end_y': toc['end_y']
            })
        
        # Remove duplicates based on title + page
        unique_entries = []
        seen = set()
        
        for entry in all_entries:
            key = (entry.get('title', ''), entry.get('page'))
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
        
        # Sort by page number (handle None pages)
        unique_entries.sort(key=lambda e: e.get('page') or 999999)
        
        # Calculate overall coordinates
        first_toc = min(all_coordinates, key=lambda c: c['start_page'])
        last_toc = max(all_coordinates, key=lambda c: c['end_page'])
        
        print(f"📋 Merged result: {len(unique_entries)} unique entries")
        print(f"   Coverage: pages {first_toc['start_page']}-{last_toc['end_page']}")
        
        return {
            "toc_found": True,
            "start_page": first_toc['start_page'],
            "start_y": first_toc['start_y'],
            "end_page": last_toc['end_page'], 
            "end_y": last_toc['end_y'],
            "confidence": "high",
            "detection_method": "llm_processing_merged",
            "entry_count": len(unique_entries),
            "toc_entries": unique_entries,
            "toc_entries_count": len(unique_entries),
            "merged_sections": len(confirmed_tocs),
            "source_coordinates": all_coordinates
        }