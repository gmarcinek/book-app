import luigi
import json
import hashlib
from datetime import datetime

from .preprocessing.batch_result_combiner import BatchResultCombinerTask


class PreprocessingTask(luigi.Task):
    """
    Phase 1 wrapper - clean interface for entire preprocessing pipeline
    """
    file_path = luigi.Parameter()
    
    def requires(self):
        return BatchResultCombinerTask(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/preprocessing_{file_hash}.json")
    
    def run(self):
        # Pass through BatchResultCombiner output with minimal wrapper
        with self.input().open('r') as f:
            result = json.load(f)
        
        output = {
            "task_name": "PreprocessingTask",
            "ready_for_ner": True,
            "phase_1_complete": True,
            "combined_result": result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output, f, indent=2)
        
        print("✅ Phase 1 complete - ready for NER")