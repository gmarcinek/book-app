# PLIK: luigi_pipeline/tasks/conditional_processor.py
import luigi
import json
import hashlib
from datetime import datetime

from .preprocessing.file_router import FileRouter
from .preprocessing.text_processing import TextPreprocessing
from .preprocessing.llm_markdown_processor import LLMMarkdownProcessor
from .preprocessing.batch_result_combiner import BatchResultCombinerTask


class ConditionalProcessor(luigi.Task):
    """
    Enhanced conditional orchestrator with new pipeline flow
    
    Flow:
    - text_processing: TextPreprocessing
    - pdf_processing: PDFProcessing → LLMMarkdownProcessor → BatchResultCombinerTask
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
            # NEW PDF chain: PDFProcessing → LLMMarkdownProcessor → BatchResultCombinerTask
            llm_task = LLMMarkdownProcessor(file_path=self.file_path)
            yield llm_task  # First: batch processing
            
            combine_task = BatchResultCombinerTask(file_path=self.file_path)
            yield combine_task  # Then: result combination
            
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
            # Extract useful info from batch combiner result
            if result_data.get("task_name") == "BatchResultCombinerTask":
                combined_result = result_data.get("combined_result", {})
                output_data.update({
                    "source_document": result_data.get("input_file"),
                    "model_used": result_data.get("model_used"),
                    "combined_markdown_file": combined_result.get("combined_markdown_file"),
                    "pages_count": combined_result.get("statistics", {}).get("total_pages"),
                    "pages_successful": combined_result.get("statistics", {}).get("successful_pages"),
                    "pages_with_tables": combined_result.get("statistics", {}).get("pages_with_tables"),
                    "processing_time": combined_result.get("statistics", {}).get("total_processing_time_seconds")
                })
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ CONDITIONAL PROCESSING COMPLETE:")
        print(f"   📋 Strategy: {strategy}")
        print(f"   📁 Final output: {self.output().path}")
        if strategy == "pdf_processing":
            print(f"   📄 Combined markdown: {output_data.get('combined_markdown_file')}")
    
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
                "BatchResultCombinerTask",  # NEW: proper Luigi task
                "ConditionalProcessor"
            ]
        return ["FileRouter", "ConditionalProcessor"]