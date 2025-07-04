import luigi
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from .toc_extractor import TOCExtractor

class TOCOrchestrator(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_orchestrator"
    
    def requires(self):
        return TOCExtractor(file_path=self.file_path)
    
    def run(self):
        # Load extractor results
        with self.input().open('r') as f:
            extractor_data = json.load(f)
        
        # Create final orchestration result
        if extractor_data.get("toc_extracted", False):
            result = {
                "task_name": "TOCOrchestrator",
                "input_file": str(self.file_path),
                "toc_found": True,
                "toc_pdf_path": extractor_data.get("toc_pdf_path"),
                "coordinates": extractor_data.get("coordinates", {}),
                "ready_for_splitting": True
            }
            
            print(f"✅ TOC orchestration complete: {extractor_data.get('toc_pdf_path')}")
            
        else:
            result = {
                "task_name": "TOCOrchestrator", 
                "input_file": str(self.file_path),
                "toc_found": False,
                "reason": extractor_data.get("reason", "unknown"),
                "ready_for_splitting": False
            }
            
            print("❌ No TOC found or extracted")
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2)