import luigi
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .llm_markdown_processor import LLMMarkdownProcessor


class BatchResultCombinerTask(luigi.Task):
    """
    Luigi Task dla kombinowania wyników z batch processing
    
    DRY: All combination logic merged into single Luigi task file
    Replaces: BatchResultCombiner util class + separate task
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    def requires(self):
        return LLMMarkdownProcessor(file_path=self.file_path, preset=self.preset)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/batch_combined_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        print("🔗 Starting batch result combination...")
        
        # Load LLM batch processing results
        with self.input().open('r') as f:
            llm_data = json.load(f)
        
        if llm_data.get("task_name") != "LLMMarkdownProcessor":
            raise ValueError("Expected LLMMarkdownProcessor input data")
        
        # Extract batch results
        batch_results = self._extract_batch_results(llm_data)
        
        if not batch_results:
            raise ValueError("No batch results found in LLM processing output")
        
        # Get metadata
        source_file = llm_data.get("input_file", str(self.file_path))
        model = llm_data.get("model_used", "unknown")
        config = llm_data.get("config", {})
        total_time = llm_data.get("statistics", {}).get("total_processing_time_seconds", 0.0)
        
        print(f"📊 Found {len(batch_results)} batch results to combine")
        
        # Combine batch results (merged logic)
        combined_result = self._combine_batch_results(
            batch_results=batch_results,
            source_file=source_file,
            model=model,
            total_time=total_time,
            config=config
        )
        
        # Create Luigi task output
        output_data = {
            "task_name": "BatchResultCombinerTask",
            "input_file": str(self.file_path),
            "llm_processor_file": self.input().path,
            "model_used": model,
            "status": "success",
            "combined_result": combined_result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Print summary
        stats = combined_result.get("statistics", {})
        print(f"✅ BATCH COMBINATION COMPLETE:")
        print(f"   📊 {stats.get('successful_pages', 0)}/{stats.get('total_pages', 0)} pages combined")
        print(f"   📁 Combined file: {combined_result.get('combined_markdown_file')}")
        print(f"   💾 Task output: {self.output().path}")
    
    def _extract_batch_results(self, llm_data: Dict) -> List[Dict]:
        """Extract batch results from LLMMarkdownProcessor output"""
        batch_results = []
        
        # Try different result structures
        if "success_results" in llm_data:
            batch_results.extend(llm_data["success_results"])
        
        if "failed_results" in llm_data:
            batch_results.extend(llm_data["failed_results"])
        
        # Alternative: look for batch_results directly
        if "batch_results" in llm_data:
            batch_results.extend(llm_data["batch_results"])
        
        return batch_results
    
    def _combine_batch_results(self, batch_results: List[Dict], 
                              source_file: str, model: str, 
                              total_time: float, config: Dict) -> Dict:
        """
        Kombinuje i finalizuje wyniki z batch processing
        
        MERGED: Logic from BatchResultCombiner class
        """
        print(f"🔗 Combining results from {len(batch_results)} processed pages...")
        
        # Separate success/failed results
        success_results = [r for r in batch_results if r.get("status") == "success"]
        failed_results = [r for r in batch_results if r.get("status") == "error"]
        
        print(f"📊 Results: {len(success_results)} success, {len(failed_results)} failed")
        
        # Create combined markdown file
        combined_markdown_file = self._create_combined_markdown(success_results, source_file)
        
        # Generate statistics
        stats = self._generate_statistics(batch_results, total_time)
        
        # Create final output
        final_result = {
            "task_name": "BatchResultCombinerTask",
            "source_file": source_file,
            "model_used": model,
            "processing_mode": "batch_parallel",
            "config": config,
            "status": "success",
            "statistics": stats,
            "combined_markdown_file": str(combined_markdown_file) if combined_markdown_file else None,
            "success_results": success_results,
            "failed_results": failed_results,
            "created_at": datetime.now().isoformat()
        }
        
        return final_result
    
    def _create_combined_markdown(self, success_results: List[Dict], source_file: str) -> Optional[Path]:
        """
        Tworzy combined markdown file z successful results
        
        Returns:
            Path do combined file lub None jeśli brak successful results
        """
        if not success_results:
            print("⚠️ No successful results to combine")
            return None
        
        # Sort by page number
        sorted_results = sorted(success_results, key=lambda x: x.get("page_num", 0))
        
        # Build combined content
        combined_parts = []
        for result in sorted_results:
            page_num = result.get("page_num", "unknown")
            content = result.get("markdown_content", "")
            
            if content.strip():
                combined_parts.append(f"{content.strip()}\n")
        
        if not combined_parts:
            print("⚠️ No content to combine")
            return None
        
        # Create filename
        source_name = Path(source_file).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f"{source_name}_combined_{timestamp}.md"
        
        # Use output directory
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        combined_path = output_dir / combined_filename
        
        # Save combined file
        combined_content = "\n".join(combined_parts)
        combined_path.write_text(combined_content, encoding='utf-8')
        
        print(f"📝 Combined markdown saved: {combined_filename}")
        return combined_path
    
    def _generate_statistics(self, batch_results: List[Dict], total_time: float) -> Dict:
        """
        Generuje statystyki z batch processing
        
        Returns:
            Dict ze statystykami
        """
        total_pages = len(batch_results)
        success_pages = len([r for r in batch_results if r.get("status") == "success"])
        failed_pages = total_pages - success_pages
        
        # Table detection stats
        pages_with_tables = sum(1 for r in batch_results 
                              if r.get("status") == "success" and r.get("has_tables", False))
        
        # Content length stats
        content_lengths = [r.get("content_length", 0) for r in batch_results 
                         if r.get("status") == "success"]
        avg_content_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
        
        # Batch distribution
        batch_distribution = self._analyze_batch_distribution(batch_results)
        
        # Retry stats
        retry_stats = self._analyze_retry_stats(batch_results)
        
        stats = {
            "total_pages": total_pages,
            "successful_pages": success_pages,
            "failed_pages": failed_pages,
            "success_rate": success_pages / total_pages if total_pages > 0 else 0,
            "pages_with_tables": pages_with_tables,
            "total_processing_time_seconds": total_time,
            "average_time_per_page": total_time / total_pages if total_pages > 0 else 0,
            "average_content_length": int(avg_content_length),
            "batch_distribution": batch_distribution,
            "retry_statistics": retry_stats
        }
        
        return stats
    
    def _analyze_batch_distribution(self, batch_results: List[Dict]) -> Dict:
        """Analizuje dystrybucję wyników per batch"""
        batch_stats = {}
        
        for result in batch_results:
            batch_id = result.get("batch_id", "unknown")
            if batch_id not in batch_stats:
                batch_stats[batch_id] = {"success": 0, "failed": 0}
            
            if result.get("status") == "success":
                batch_stats[batch_id]["success"] += 1
            else:
                batch_stats[batch_id]["failed"] += 1
        
        return {
            "total_batches": len(batch_stats),
            "batch_stats": batch_stats,
            "successful_batches": len([b for b in batch_stats.values() if b["failed"] == 0])
        }
    
    def _analyze_retry_stats(self, batch_results: List[Dict]) -> Dict:
        """Analizuje statystyki retry attempts"""
        retry_attempted = len([r for r in batch_results if r.get("retry_attempted", False)])
        retry_successful = len([r for r in batch_results 
                              if r.get("retry_attempted", False) and r.get("status") == "success"])
        
        return {
            "pages_retried": retry_attempted,
            "retry_successful": retry_successful,
            "retry_success_rate": retry_successful / retry_attempted if retry_attempted > 0 else 0
        }