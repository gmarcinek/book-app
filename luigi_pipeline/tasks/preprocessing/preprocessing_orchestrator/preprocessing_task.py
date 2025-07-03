import luigi
import json
from datetime import datetime

from luigi_pipeline.tasks.base.structured_task import StructuredTask
from luigi_pipeline.tasks.preprocessing.batch_result_combiner.batch_result_combiner import BatchResultCombiner


class PreprocessingOrchestrator(StructuredTask):
    """
    Preprocessing pipeline orchestrator - coordinates entire Phase 1
    """
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "preprocessing_orchestrator"
    
    def requires(self):
        return BatchResultCombiner(file_path=self.file_path)
    
    def run(self):
        # Pass through BatchResultCombiner output with orchestrator wrapper
        with self.input().open('r') as f:
            result = json.load(f)
        
        output = {
            "task_name": "PreprocessingOrchestrator",
            "ready_for_ner": True,
            "phase_1_complete": True,
            "combined_result": result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print("✅ Preprocessing orchestration complete - ready for NER")