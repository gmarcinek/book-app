import luigi
import json
import hashlib
from datetime import datetime

from .preprocessing.file_router import FileRouter
from .preprocessing.text_processing import TextPreprocessing
from .preprocessing_task import PreprocessingTask
from .postprocess_task import PostprocessTask  # ← NEW IMPORT


class ConditionalProcessor(luigi.Task):
    """
    EXTENDED conditional orchestrator with postprocessing
    """
    file_path = luigi.Parameter()

    def requires(self):
        return FileRouter(file_path=self.file_path)

    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/conditional_processor_{file_hash}.json")

    def run(self):
        with self.input().open('r') as f:
            strategy = f.read().strip()

        if strategy == "text_processing":
            next_task = TextPreprocessing(file_path=self.file_path)
            yield next_task
        elif strategy == "pdf_processing":
            print("🚀 Starting PDF processing with NER pipeline...")
            next_task = PostprocessTask(file_path=self.file_path)  # Remove preset
            yield next_task
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        with next_task.output().open('r') as f:
            result = json.load(f)

        output = {
            "task_name": "ConditionalProcessor",
            "strategy": strategy,
            "result": result,
            "created_at": datetime.now().isoformat()
        }

        with self.output().open('w') as f:
            json.dump(output, f, indent=2)

        print(f"✅ Strategy {strategy} complete")