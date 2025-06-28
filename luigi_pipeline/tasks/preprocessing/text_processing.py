import luigi
import json
import hashlib
from pathlib import Path
from datetime import datetime

from ner.semantic.hierarchical_strategy import HierarchicalChunker
from ner.semantic.models import create_semantic_config
from .file_router import FileRouter


class TextPreprocessing(luigi.Task):
    """
    Processes text files (.md, .txt) using hierarchical chunking
    
    Output: JSON with chunks and metadata
    """
    file_path = luigi.Parameter()
    
    def requires(self):
        return FileRouter(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/text_processing_{file_hash}.json")
    
    def run(self):
        # Validate input strategy
        with self.input().open('r') as f:
            strategy = f.read().strip()
        
        if strategy != "text_processing":
            raise ValueError(f"Wrong strategy: {strategy}, expected text_processing")
        
        # Load text
        text = Path(self.file_path).read_text(encoding='utf-8')
        
        # Hierarchical chunking
        config = create_semantic_config("auto")
        chunker = HierarchicalChunker(config)
        chunks = chunker.chunk(text)
        
        # Prepare output
        output_data = {
            "task_name": "TextPreprocessing",
            "input_file": str(self.file_path),
            "status": "success",
            "chunks_count": len(chunks),
            "chunks": [
                {
                    "id": chunk.id,
                    "start": chunk.start,
                    "end": chunk.end,
                    "text": chunk.text,
                    "text_length": len(chunk.text)
                } for chunk in chunks
            ],
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)