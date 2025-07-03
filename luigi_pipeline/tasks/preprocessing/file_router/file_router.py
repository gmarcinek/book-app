import luigi
from pathlib import Path

from luigi_pipeline.tasks.base.structured_task import StructuredTask


class FileRouterTask(StructuredTask):
    """Routes files to appropriate processing strategy"""
    
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "file_router"
    
    def output(self):
        file_hash = self.get_file_hash(self.file_path)
        filename = f"file_router_{file_hash}.txt"
        return self.create_output_target(filename)
    
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
        
        with self.output().open('w') as f:
            f.write(f"{strategy}\n")