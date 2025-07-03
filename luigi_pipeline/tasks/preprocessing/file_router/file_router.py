import luigi
import json
from pathlib import Path
from datetime import datetime

from luigi_pipeline.tasks.base.structured_task import StructuredTask


class FileRouter(StructuredTask):
    """Routes files to appropriate processing strategy"""
    
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "file_router"
    
    def run(self):
        file_path = Path(self.file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {self.file_path}")
        
        file_ext = file_path.suffix.lower()
        
        if file_ext in ['.md', '.txt']:
            strategy = 'text_processing'
        elif file_ext == '.pdf':
            strategy = 'pdf_processing'
        else:
            strategy = 'unsupported'
        
        result = {
            "task_name": "FileRouter",
            "file_path": str(self.file_path),
            "strategy": strategy,
            "file_extension": file_ext,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2)