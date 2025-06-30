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
            
        elif strategy == "pdf_processing":
            # PDF chain: PDFProcessing → LLMMarkdownProcessor → MarkdownCombinerSingle
            llm_task = LLMMarkdownProcessor(file_path=self.file_path)
            combine_task = MarkdownCombinerSingle(
                llm_markdown_file=llm_task.output().path  # Auto-generated path
            )
            next_task = combine_task
            
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        # Run the chosen task chain (Luigi will auto-run dependencies)
        yield next_task
        
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


class BatchProcessor(luigi.Task):
    """
    NEW: Batch processor for multiple files with final combining
    
    Processes all files in directory, then combines ALL markdown outputs
    """
    input_directory = luigi.Parameter()
    file_pattern = luigi.Parameter(default="*.pdf")
    
    def output(self):
        dir_hash = hashlib.md5(str(self.input_directory).encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return luigi.LocalTarget(f"output/batch_processor_{dir_hash}_{timestamp}.json", format=luigi.format.UTF8)
    
    def run(self):
        from pathlib import Path
        import glob
        from .preprocessing.markdown_combiner import MarkdownCombiner
        
        # Find all matching files
        search_pattern = str(Path(self.input_directory) / self.file_pattern)
        files = glob.glob(search_pattern)
        
        if not files:
            raise ValueError(f"No files found: {search_pattern}")
        
        print(f"📁 Found {len(files)} files to process")
        
        # Process each file through ConditionalProcessor
        processed_files = []
        for file_path in files:
            try:
                conditional_task = ConditionalProcessor(file_path=file_path)
                yield conditional_task
                
                with conditional_task.output().open('r') as f:
                    result = json.load(f)
                
                processed_files.append({
                    "file_path": file_path,
                    "status": "success",
                    "result": result
                })
                
            except Exception as e:
                print(f"❌ Failed to process {file_path}: {e}")
                processed_files.append({
                    "file_path": file_path,
                    "status": "error", 
                    "error": str(e)
                })
        
        # Run final MarkdownCombiner to combine all documents
        combiner_task = MarkdownCombiner()
        yield combiner_task
        
        with combiner_task.output().open('r') as f:
            combiner_result = json.load(f)
        
        # Create batch output
        successful = len([f for f in processed_files if f["status"] == "success"])
        
        output_data = {
            "task_name": "BatchProcessor",
            "input_directory": str(self.input_directory),
            "file_pattern": self.file_pattern,
            "files_found": len(files),
            "files_successful": successful,
            "files_failed": len(files) - successful,
            "processed_files": processed_files,
            "final_combiner_result": combiner_result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"🎉 Batch complete: {successful}/{len(files)} files processed")