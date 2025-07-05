import luigi
import json
from pathlib import Path
from datetime import datetime

from luigi_components.structured_task import StructuredTask
from ner.semantic.hierarchical_strategy import HierarchicalChunker
from ner.semantic.models import create_semantic_config
from luigi_pipeline.tasks.preprocessing.file_router.file_router import FileRouter


class TextProcessing(StructuredTask):
    """
    Processes text files (.md, .txt) using hierarchical chunking
    """
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "text_processing"
    
    def requires(self):
        return FileRouter(file_path=self.file_path)
    
    def run(self):
        # Validate input strategy
        with self.input().open('r') as f:
            input_data = json.load(f)
        
        if input_data.get("strategy") != "text_processing":
            raise ValueError(f"Wrong strategy: {input_data.get('strategy')}, expected text_processing")
        
        # Load text
        text = Path(self.file_path).read_text(encoding='utf-8')
        
        # Create task-specific directory for chunk files
        doc_name = Path(self.file_path).stem
        chunks_dir = Path("output") / doc_name / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # Hierarchical chunking
        config = create_semantic_config("auto")
        chunker = HierarchicalChunker(config)
        chunks = chunker.chunk(text)
        
        # Save individual chunk files
        chunk_files = []
        for chunk in chunks:
            chunk_filename = f"chunk_{chunk.id:03d}.txt"
            chunk_file = chunks_dir / chunk_filename
            chunk_file.write_text(chunk.text, encoding='utf-8')
            chunk_files.append(str(chunk_file))
        
        # Prepare output
        result = {
            "task_name": "TextProcessing",
            "input_file": str(self.file_path),
            "status": "success",
            "chunks_count": len(chunks),
            "chunks_directory": str(chunks_dir),
            "chunk_files": chunk_files,
            "chunks": [
                {
                    "id": chunk.id,
                    "start": chunk.start,
                    "end": chunk.end,
                    "text_length": len(chunk.text),
                    "file": f"chunk_{chunk.id:03d}.txt"
                } for chunk in chunks
            ],
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Text processing complete: {len(chunks)} chunks saved to {chunks_dir}")