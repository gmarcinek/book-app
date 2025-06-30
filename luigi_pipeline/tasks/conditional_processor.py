# luigi_pipeline/tasks/conditional_processor.py
import luigi
import json
import hashlib
from datetime import datetime

from .preprocessing.file_router import FileRouter
from .preprocessing.text_processing import TextPreprocessing
from .preprocessing.llm_markdown_processor import LLMMarkdownProcessor
from .preprocessing.markdown_combiner import MarkdownCombinerSingle


class ConditionalProcessor(luigi.Task):
    """
    Enhanced conditional orchestrator with automatic markdown combining
    
    Flow:
    - text_processing: TextPreprocessing
    - pdf_processing: PDFProcessing → LLMMarkdownProcessor → MarkdownCombinerSingle
    """
    file_path = luigi.Parameter()
    
    def requires(self):
        return FileRouter(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/conditional_processor_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Read FileRouter decision
        with self.input().open('r') as f:
            strategy = f.read().strip()
        
        # Create appropriate task chain
        if strategy == "text_processing":
            next_task = TextPreprocessing(file_path=self.file_path)
            yield next_task
            
        elif strategy == "pdf_processing":
            # PDF chain: PDFProcessing → LLMMarkdownProcessor → MarkdownCombinerSingle
            llm_task = LLMMarkdownProcessor(file_path=self.file_path)
            yield llm_task  # NAJPIERW LLMMarkdownProcessor
            
            combine_task = MarkdownCombinerSingle(
                llm_markdown_file=llm_task.output().path
            )
            yield combine_task  # POTEM MarkdownCombinerSingle
            
            next_task = combine_task  # Final result
            
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Read the final result
        with next_task.output().open('r') as f:
            result_data = json.load(f)
        
        # Create enhanced aggregated output
        output_data = {
            "task_name": "ConditionalProcessor",
            "input_file": str(self.file_path),
            "strategy_used": strategy,
            "status": "success",
            "final_result": result_data,
            "pipeline_steps": self._get_pipeline_steps(strategy),
            "created_at": datetime.now().isoformat()
        }
        
        # Add strategy-specific metadata
        if strategy == "pdf_processing":
            # Extract useful info from markdown combiner result
            if result_data.get("task_name") == "MarkdownCombinerSingle":
                combine_result = result_data.get("result", {})
                output_data.update({
                    "source_document": combine_result.get("source_document"),
                    "document_name": combine_result.get("document_name"),
                    "combined_markdown_file": combine_result.get("combined_markdown_file"),
                    "pages_count": combine_result.get("pages_count"),
                    "pages_with_tables": combine_result.get("pages_with_tables"),
                    "model_used": combine_result.get("model_used")
                })
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def _get_pipeline_steps(self, strategy):
        """Return list of pipeline steps for given strategy"""
        if strategy == "text_processing":
            return [
                "FileRouter",
                "TextPreprocessing",
                "ConditionalProcessor"
            ]
        elif strategy == "pdf_processing":
            return [
                "FileRouter", 
                "PDFProcessing",
                "LLMMarkdownProcessor",
                "MarkdownCombinerSingle",
                "ConditionalProcessor"
            ]
        return ["FileRouter", "ConditionalProcessor"]