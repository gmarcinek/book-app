import luigi
import hashlib
from pathlib import Path


class FileRouter(luigi.Task):
    """
    Routes files to appropriate processing strategy based on file extension
    
    Output: text file with strategy name (text_processing, pdf_processing, unsupported)
    """
    file_path = luigi.Parameter()
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/file_router_{file_hash}.txt")
    
    def run(self):
        file_path = Path(self.file_path)
        
        # Validate file exists and is actually a file
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