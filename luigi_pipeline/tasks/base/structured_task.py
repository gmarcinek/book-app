import luigi
import hashlib
from pathlib import Path
from abc import ABC, abstractmethod


class StructuredTask(luigi.Task, ABC):
    """
    Base class dla tasków z ustandaryzowaną strukturą output
    """
    
    @property
    @abstractmethod
    def pipeline_name(self) -> str:
        """Nazwa pipeline (np. 'preprocessing', 'analysis')"""
        pass
    
    @property
    @abstractmethod 
    def task_name(self) -> str:
        """Nazwa taska (np. 'file_router', 'pdf_processing')"""
        pass
    
    @property
    def output_dir(self) -> Path:
        """Standardowy output dir: output/{pipeline}/{task}"""
        return Path("output") / self.pipeline_name / self.task_name
    
    def ensure_output_dir(self) -> Path:
        """Upewnij się że output dir istnieje"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir
    
    def get_file_hash(self, file_path: str) -> str:
        """Wygeneruj hash dla pliku"""
        return hashlib.md5(str(file_path).encode()).hexdigest()[:8]
    
    def create_output_target(self, filename: str) -> luigi.LocalTarget:
        """Stwórz Luigi target w odpowiednim folderze"""
        self.ensure_output_dir()
        output_file = self.output_dir / filename
        return luigi.LocalTarget(str(output_file))