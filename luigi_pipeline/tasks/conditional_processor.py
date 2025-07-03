import luigi
import json
from datetime import datetime

from luigi_pipeline.tasks.base.structured_task import StructuredTask
from luigi_pipeline.tasks.preprocessing.file_router.file_router import FileRouter
from luigi_pipeline.tasks.preprocessing.text_processing.text_processing import TextProcessing
from luigi_pipeline.tasks.postprocessing.postprocess_task.postprocess_task import PostprocessTask


class ConditionalProcessor(StructuredTask):
    """
    Main orchestrator task that routes to appropriate processing pipeline
    """
    file_path = luigi.Parameter()

    @property
    def pipeline_name(self) -> str:
        return "orchestration"
    
    @property
    def task_name(self) -> str:
        return "conditional_processor"

    def requires(self):
        return FileRouter(file_path=self.file_path)

    def run(self):
        # Read file router decision
        with self.input().open('r') as f:
            router_data = json.load(f)

        strategy = router_data.get("strategy")
        
        if strategy == "text_processing":
            next_task = TextProcessing(file_path=self.file_path)
            yield next_task
            
            # Load text processing result
            with next_task.output().open('r') as f:
                result = json.load(f)
                
        elif strategy == "pdf_processing":
            print("🚀 Starting PDF processing with NER pipeline...")
            next_task = PostprocessTask(file_path=self.file_path)
            yield next_task
            
            # Load postprocessing result
            with next_task.output().open('r') as f:
                result = json.load(f)
                
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Create final orchestration result
        output = {
            "task_name": "ConditionalProcessor",
            "strategy": strategy,
            "file_path": str(self.file_path),
            "status": "success",
            "result": result,
            "created_at": datetime.now().isoformat()
        }

        with self.output().open('w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"✅ Strategy {strategy} complete")