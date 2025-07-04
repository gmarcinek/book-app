import luigi
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from luigi_pipeline.tasks.base.structured_task import StructuredTask
from .toc_llm_parser import TOCLLMParser

class TOCOrchestrator(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_orchestrator"
    
    def requires(self):
        return TOCLLMParser(file_path=self.file_path)
    
    def run(self):
        # Load LLM parser results
        with self.input().open('r') as f:
            parser_data = json.load(f)
        
        # Create final orchestration result
        if parser_data.get("toc_parsed", False):
            toc_structure = parser_data.get("toc_structure", {})
            entries = toc_structure.get("entries", [])
            
            result = {
                "task_name": "TOCOrchestrator",
                "input_file": str(self.file_path),
                "toc_found": True,
                "toc_entries_count": len(entries),
                "toc_entries": entries,
                "toc_structure": toc_structure,
                "source_toc_pdf": parser_data.get("source_toc_pdf"),
                "ready_for_splitting": True
            }
            
            print(f"✅ TOC processed: {len(entries)} entries found")
            
        else:
            result = {
                "task_name": "TOCOrchestrator", 
                "input_file": str(self.file_path),
                "toc_found": False,
                "reason": parser_data.get("reason", "unknown"),
                "ready_for_splitting": False
            }
            
            print("❌ No TOC found or parsed")
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2)