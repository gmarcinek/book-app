import luigi
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from luigi_components.structured_task import StructuredTask
from luigi_pipeline.tasks.preprocessing.markdown_header_cleaner.markdown_header_cleaner import MarkdownHeaderCleaner


class BatchResultCombiner(StructuredTask):
    """
    Combines results from batch processing and creates final markdown file
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "batch_result_combiner"
    
    def requires(self):
        return MarkdownHeaderCleaner(file_path=self.file_path, preset=self.preset)
    
    def run(self):
        print("🔗 Starting batch result combination...")
        
        # Load header cleaned results
        with self.input().open('r') as f:
            header_cleaned_data = json.load(f)
        
        # Validate input
        expected_tasks = ["MarkdownHeaderCleaner", "LLMMarkdownProcessor"]
        if header_cleaned_data.get("task_name") not in expected_tasks:
            raise ValueError(f"Expected {expected_tasks} input data, got: {header_cleaned_data.get('task_name')}")
        
        # Extract batch results
        batch_results = self._extract_batch_results(header_cleaned_data)
        
        if not batch_results:
            raise ValueError("No batch results found in input data")
        
        # Create task-specific directory
        task_dir = Path("output") / self.pipeline_name / self.task_name
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract metadata
        source_file = header_cleaned_data.get("input_file", str(self.file_path))
        model = header_cleaned_data.get("model_used", "unknown")
        header_cleaning_info = self._extract_header_cleaning_info(header_cleaned_data)
        
        print(f"📊 Found {len(batch_results)} batch results to combine")
        if header_cleaning_info["applied"]:
            print(f"🧹 Header cleaning: {header_cleaning_info['patterns_detected']} patterns, {header_cleaning_info['bytes_removed']} bytes removed")
        
        # Combine batch results
        combined_result = self._combine_batch_results(
            batch_results=batch_results,
            source_file=source_file,
            model=model,
            header_cleaning_info=header_cleaning_info,
            task_dir=task_dir
        )
        
        # Create output
        result = {
            "task_name": "BatchResultCombiner",
            "input_file": str(self.file_path),
            "input_source": header_cleaned_data.get("task_name"),
            "model_used": model,
            "status": "success",
            "combined_result": combined_result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Print summary
        stats = combined_result.get("statistics", {})
        print(f"✅ BATCH COMBINATION COMPLETE:")
        print(f"   📊 {stats.get('successful_pages', 0)}/{stats.get('total_pages', 0)} pages combined")
        print(f"   📁 Combined file: {combined_result.get('combined_markdown_file')}")
        if header_cleaning_info["applied"]:
            print(f"   🧹 Header cleaning efficiency: {header_cleaning_info['efficiency']:.1%}")
    
    def _extract_batch_results(self, input_data: Dict) -> List[Dict]:
        """Extract batch results from input data"""
        batch_results = []
        
        # Try different result structures
        if "batch_results" in input_data:
            batch_results.extend(input_data["batch_results"])
        
        # Fallback: look for success/failed results separately  
        if "success_results" in input_data:
            batch_results.extend(input_data["success_results"])
        
        if "failed_results" in input_data:
            batch_results.extend(input_data["failed_results"])
        
        return batch_results
    
    def _extract_header_cleaning_info(self, input_data: Dict) -> Dict:
        """Extract header cleaning metadata"""
        return {
            "applied": input_data.get("ai_cleaning_applied", False),
            "patterns_detected": input_data.get("ai_statistics", {}).get("headers_detected", 0),
            "bytes_removed": input_data.get("ai_statistics", {}).get("total_bytes_removed", 0),
            "pages_cleaned": input_data.get("ai_statistics", {}).get("pages_cleaned", 0),
            "efficiency": input_data.get("ai_statistics", {}).get("cleaning_efficiency", 0.0),
            "pattern_types": input_data.get("detected_headers", [])
        }
    
    def _combine_batch_results(self, batch_results: List[Dict], source_file: str, 
                              model: str, header_cleaning_info: Dict, task_dir: Path) -> Dict:
        """Combine batch results and create final markdown file"""
        print(f"🔗 Combining results from {len(batch_results)} processed pages...")
        
        # Separate success/failed results
        success_results = [r for r in batch_results if r.get("status") == "success"]
        failed_results = [r for r in batch_results if r.get("status") == "error"]
        
        print(f"📊 Results: {len(success_results)} success, {len(failed_results)} failed")
        
        # Create combined markdown file
        combined_markdown_file = self._create_combined_markdown(success_results, source_file, task_dir)
        
        # Generate statistics
        stats = self._generate_statistics(batch_results, header_cleaning_info)
        
        # Create final result
        return {
            "task_name": "BatchResultCombiner",
            "source_file": source_file,
            "model_used": model,
            "processing_mode": "batch_parallel",
            "status": "success",
            "statistics": stats,
            "combined_markdown_file": str(combined_markdown_file) if combined_markdown_file else None,
            "success_results": success_results,
            "failed_results": failed_results,
            "header_cleaning": header_cleaning_info,
            "created_at": datetime.now().isoformat()
        }
    
    def _create_combined_markdown(self, success_results: List[Dict], source_file: str, task_dir: Path) -> Optional[Path]:
        """Create combined markdown file in task directory"""
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
        
        # Create filename in task directory
        source_name = Path(source_file).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_filename = f"{source_name}_combined_{timestamp}.md"
        combined_path = task_dir / combined_filename
        
        # Save combined file
        combined_content = "\n".join(combined_parts)
        combined_path.write_text(combined_content, encoding='utf-8')
        
        print(f"📝 Combined markdown saved: {combined_filename}")
        return combined_path
    
    def _generate_statistics(self, batch_results: List[Dict], header_cleaning_info: Dict) -> Dict:
        """Generate comprehensive statistics"""
        total_pages = len(batch_results)
        success_pages = len([r for r in batch_results if r.get("status") == "success"])
        failed_pages = total_pages - success_pages
        
        # Table detection stats
        pages_with_tables = sum(1 for r in batch_results 
                              if r.get("status") == "success" and r.get("has_tables", False))
        
        # Content length stats
        success_results = [r for r in batch_results if r.get("status") == "success"]
        original_lengths = [r.get("original_length", r.get("content_length", 0)) for r in success_results]
        cleaned_lengths = [r.get("cleaned_length", r.get("content_length", 0)) for r in success_results]
        
        avg_original_length = sum(original_lengths) / len(original_lengths) if original_lengths else 0
        avg_cleaned_length = sum(cleaned_lengths) / len(cleaned_lengths) if cleaned_lengths else 0
        
        # Header cleaning stats
        pages_with_headers_removed = sum(1 for r in batch_results 
                                       if r.get("status") == "success" and r.get("ai_cleaned", False))
        
        return {
            "total_pages": total_pages,
            "successful_pages": success_pages,
            "failed_pages": failed_pages,
            "success_rate": success_pages / total_pages if total_pages > 0 else 0,
            "pages_with_tables": pages_with_tables,
            "average_original_content_length": int(avg_original_length),
            "average_cleaned_content_length": int(avg_cleaned_length),
            "header_cleaning": {
                "applied": header_cleaning_info["applied"],
                "patterns_detected": header_cleaning_info["patterns_detected"],
                "pages_cleaned": pages_with_headers_removed,
                "total_bytes_removed": header_cleaning_info["bytes_removed"],
                "cleaning_efficiency": header_cleaning_info["efficiency"],
                "pattern_types_found": header_cleaning_info["pattern_types"]
            }
        }