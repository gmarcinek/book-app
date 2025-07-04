import luigi
import json
from pathlib import Path
import sys

from luigi_toc_pipeline.tasks.toc_fallback_llm_strategy.toc_fallback_llm_strategy import TOCFallbackLLMStrategy
sys.path.append(str(Path(__file__).parent.parent.parent))

from luigi_components.structured_task import StructuredTask


class TOCOrchestrator(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_orchestrator"
    
    def requires(self):
        return TOCFallbackLLMStrategy(file_path=self.file_path)  # skip extractor
    
    def run(self):
        # Load fallback strategy results (instead of extractor)
        with self.input().open('r') as f:
            strategy_data = json.load(f)
        
        # Create final orchestration result
        if strategy_data.get("toc_found", False):
            # Extract structured TOC data
            toc_entries = strategy_data.get("toc_entries", [])
            coordinates = {
                "start_page": strategy_data.get("start_page"),
                "end_page": strategy_data.get("end_page"), 
                "start_y": strategy_data.get("start_y"),
                "end_y": strategy_data.get("end_y")
            }
            
            result = {
                "task_name": "TOCOrchestrator",
                "input_file": str(self.file_path),
                "toc_found": True,
                "detection_method": strategy_data.get("method", "unknown"),
                "coordinates": coordinates,
                "toc_entries": toc_entries,
                "toc_entries_count": len(toc_entries),
                "ready_for_splitting": len(toc_entries) > 0,
                "processing_stats": {
                    "certain_count": strategy_data.get("certain_count", 0),
                    "uncertain_count": strategy_data.get("uncertain_count", 0),
                    "processed_count": strategy_data.get("processed_count", 0),
                    "rejected_count": strategy_data.get("rejected_count", 0)
                }
            }
            
            print(f"✅ TOC orchestration complete: {len(toc_entries)} entries found")
            print(f"   Method: {strategy_data.get('method', 'unknown')}")
            print(f"   Coverage: pages {coordinates['start_page']}-{coordinates['end_page']}")
            
        else:
            result = {
                "task_name": "TOCOrchestrator", 
                "input_file": str(self.file_path),
                "toc_found": False,
                "reason": strategy_data.get("reason", "unknown"),
                "ready_for_splitting": False,
                "processing_stats": {
                    "certain_count": strategy_data.get("certain_count", 0),
                    "uncertain_count": strategy_data.get("uncertain_count", 0),
                    "processed_count": strategy_data.get("processed_count", 0),
                    "rejected_count": strategy_data.get("rejected_count", 0)
                }
            }
            
            print("❌ No TOC found")
            print(f"   Reason: {strategy_data.get('reason', 'unknown')}")
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)