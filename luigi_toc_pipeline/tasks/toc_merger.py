import luigi
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from luigi_pipeline.tasks.base.structured_task import StructuredTask
from .toc_heuristic_detector import TOCHeuristicDetector

class TOCMerger(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_merger"
    
    def requires(self):
        return TOCHeuristicDetector(file_path=self.file_path)
    
    def run(self):
        # Load heuristic result
        with self.input().open('r') as f:
            heuristic_result = json.load(f)
        
        # For now, just pass through heuristic result
        # Later: add fallback logic if heuristic fails
        if heuristic_result.get("toc_found", False):
            final_result = heuristic_result
            final_result["chosen_method"] = "heuristic"
        else:
            final_result = {
                "toc_found": False,
                "chosen_method": "none"
            }
        
        with self.output().open('w') as f:
            json.dump(final_result, f)