import luigi
import json

from luigi_components.structured_task import StructuredTask
from luigi_toc_pipeline.tasks.toc_heuristic_detector.toc_heuristic_detector import TOCHeuristicDetector


class TOCFallbackLLMStrategy(StructuredTask):
    """
    TODO: Pipe strategy for TOC detection chain:
    
    1. Check built-in TOC (doc.get_toc()) - if found, pass through
    2. If no built-in TOC, run heuristic detection
    3. If heuristic fails, implement semantic fallback (better than current)
    4. If all fail, return toc_found: false
    
    Current implementation: Pass-through preleotka to TOCHeuristicDetector
    """
    file_path = luigi.Parameter()

    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_fallback_llm_strategy"

    def requires(self):
        return TOCHeuristicDetector(file_path=self.file_path)

    def run(self):
        # TODO: Implement proper chain:
        # 1. Built-in TOC check
        # 2. Heuristic detection (current)  
        # 3. Better semantic fallback
        
        # TEMPORARY: Pass through heuristic result
        with self.input().open('r') as f:
            heuristic_result = json.load(f)
        
        # Pass through as-is (preleotka)
        result = heuristic_result
        result["method"] = result.get("detection_method", "heuristic_passthrough")
        
        print(f"🔄 TOCFallbackLLMStrategy: passing through {result.get('method')} result")
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)