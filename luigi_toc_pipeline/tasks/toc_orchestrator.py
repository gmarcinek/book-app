import luigi
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from luigi_pipeline.tasks.base.structured_task import StructuredTask
from .toc_merger import TOCMerger

class TOCOrchestrator(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_orchestrator"
    
    def requires(self):
        return TOCMerger(file_path=self.file_path)
    
    def run(self):
        # Load merger results
        with self.input().open('r') as f:
            toc_data = json.load(f)
        
        # Create final orchestration result
        result = {
            "task_name": "TOCOrchestrator",
            "input_file": str(self.file_path),
            "toc_detection_result": toc_data,
            "ready_for_splitting": toc_data.get("toc_found", False)
        }
        
        with self.output().open('w') as f:
            json.dump(result, f)
        
        # Status
        if result["ready_for_splitting"]:
            entries_count = len(toc_data.get("toc_entries", []))
            method = toc_data.get("chosen_method", "unknown")
            print(f"✅ TOC found via {method}: {entries_count} entries")
        else:
            print("❌ No TOC found")