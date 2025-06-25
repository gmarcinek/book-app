import luigi
from pathlib import Path

class HelloTask(luigi.Task):
    """Minimal working Luigi task for testing infrastructure"""
    
    def output(self):
        # Ensure temp directory exists
        Path("luigi_pipeline/temp").mkdir(exist_ok=True)
        return luigi.LocalTarget("luigi_pipeline/temp/hello.txt")
    
    def run(self):
        with self.output().open('w') as f:
            f.write("Hello Luigi Pipeline!\n")
            f.write("Infrastructure is working.\n")
            f.write("Luigi version: 3.6.0\n")