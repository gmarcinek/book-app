import luigi
import hashlib
from pathlib import Path
from abc import ABC, abstractmethod


class StructuredTask(luigi.Task, ABC):
    """
    Base class for Luigi tasks with standardized output structure
    
    Output: output/{pipeline_name}/{task_name}/{task_name}.json
    """
    
    @property
    @abstractmethod
    def pipeline_name(self) -> str:
        """Pipeline name (e.g. 'preprocessing', 'postprocessing')"""
        pass
    
    @property
    @abstractmethod 
    def task_name(self) -> str:
        """Task name (e.g. 'file_router', 'pdf_processing')"""
        pass
    
    def output(self):
        """Standardized output path with UTF-8 encoding"""
        output_dir = Path("output") / self.pipeline_name / self.task_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{self.task_name}.json"
        return luigi.LocalTarget(str(output_dir / filename), format=luigi.format.UTF8)
    
    @abstractmethod
    def run(self):
        """Task implementation"""
        pass