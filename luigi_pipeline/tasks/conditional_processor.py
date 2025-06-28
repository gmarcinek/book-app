import luigi
import json
import hashlib
from datetime import datetime

from .preprocessing.file_router import FileRouter
from .preprocessing.text_processing import TextPreprocessing
from .preprocessing.pdf_processing import PDFProcessing


class ConditionalProcessor(luigi.Task):
    """
    Conditional orchestrator that dynamically chooses processing strategy
    
    Reads FileRouter decision and runs appropriate processing task
    """
    file_path = luigi.Parameter()
    
    def requires(self):
        return FileRouter(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/conditional_processor_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Read FileRouter decision
        with self.input().open('r') as f:
            strategy = f.read().strip()
        
        # Create appropriate task
        if strategy == "text_processing":
            next_task = TextPreprocessing(file_path=self.file_path)
        elif strategy == "pdf_processing":
            next_task = PDFProcessing(file_path=self.file_path)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Run the chosen task
        yield next_task
        
        # Read the result and create our output
        with next_task.output().open('r') as f:
            result_data = json.load(f)
        
        # Create aggregated output
        output_data = {
            "task_name": "ConditionalProcessor",
            "input_file": str(self.file_path),
            "strategy_used": strategy,
            "status": "success",
            "processing_result": result_data,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)