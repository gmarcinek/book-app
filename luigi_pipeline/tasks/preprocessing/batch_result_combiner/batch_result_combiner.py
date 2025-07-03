# PLIK: luigi_pipeline/tasks/preprocessing/batch_result_combiner.py
import luigi
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .markdown_header_cleaner import MarkdownHeaderCleaner  # ← CHANGED from LLMMarkdownProcessor


class BatchResultCombinerTask(luigi.Task):
    """
    Luigi Task dla kombinowania wyników z batch processing
    
    UPDATED INPUT: Now takes cleaned markdown from MarkdownHeaderCleaner
    Pipeline: PDFProcessing → LLMMarkdownProcessor → MarkdownHeaderCleaner → BatchResultCombinerTask
                                                    ↑ NEW INPUT SOURCE
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    def requires(self):
        return MarkdownHeaderCleaner(file_path=self.file_path, preset=self.preset)  # ← CHANGED
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/batch_combined_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        print("🔗 Starting batch result combination...")
        
        # Load MarkdownHeaderCleaner results (not LLMMarkdownProcessor)
        with self.input().open('r') as f:
            header_cleaned_data = json.load(f)
        
        # Validate input - can be either MarkdownHeaderCleaner or LLMMarkdownProcessor (fallback)
        expected_tasks = ["MarkdownHeaderCleaner", "LLMMarkdownProcessor"]
        if header_cleaned_data.get("task_name") not in expected_tasks:
            raise ValueError(f"Expected {expected_tasks} input data, got: {header_cleaned_data.get('task_name')}")
        
        # Extract batch results (works for both input types)
        batch_results = self._extract_batch_results(header_cleaned_data)
        
        if not batch_results:
            raise ValueError("No batch results found in input data")
        
        # Get metadata
        source_file = header_cleaned_data.get("input_file", str(self.file_path))
        model = header_cleaned_data.get("model_used", "unknown")
        config = header_cleaned_data.get("config", {})
        total_time = header_cleaned_data.get("statistics", {}).get("total_processing_time_seconds", 0.0)
        
        # NEW: Extract header cleaning metadata
        header_cleaning_info = self._extract_header_cleaning_info(header_cleaned_data)
        
        print(f"📊 Found {len(batch_results)} batch results to combine")
        if header_cleaning_info["applied"]:
            print(f"🧹 Header cleaning: {header_cleaning_info['patterns_detected']} patterns, {header_cleaning_info['bytes_removed']} bytes removed")
        
        # Combine batch results
        combined_result = self._combine_batch_results(
            batch_results=batch_results,
            source_file=source_file,
            model=model,
            total_time=total_time,
            config=config,
            header_cleaning_info=header_cleaning_info  # ← NEW
        )
        
        # Create Luigi task output
        output_data = {
            "task_name": "BatchResultCombinerTask",
            "input_file": str(self.file_path),
            "input_source": header_cleaned_data.get("task_name"),  # Track what we combined
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
        if header_cleaning_info["applied"]:
            print(f"   🧹 Header cleaning efficiency: {header_cleaning_info['efficiency']:.1%}")
    
    def _extract_batch_results(self, input_data: Dict) -> List[Dict]:
        """Extract batch results from MarkdownHeaderCleaner or LLMMarkdownProcessor output"""
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
            "applied": input_data.get("header_cleaning_applied", False),
            "patterns_detected": input_data.get("cleaning_statistics", {}).get("patterns_detected", 0),
            "bytes_removed": input_data.get("cleaning_statistics", {}).get("total_bytes_removed", 0),
            "pages_cleaned": input_data.get("cleaning_statistics", {}).get("pages_cleaned", 0),
            "efficiency": input_data.get("cleaning_statistics", {}).get("cleaning_efficiency", 0.0),
            "pattern_types": input_data.get("cleaning_statistics", {}).get("detected_pattern_types", [])
        }
    
    def _combine_batch_results(self, batch_results: List[Dict], 
                              source_file: str, model: str, 
                              total_time: float, config: Dict,
                              header_cleaning_info: Dict) -> Dict:  # ← NEW parameter
        """
        Kombinuje i finalizuje wyniki z batch processing + header cleaning info
        """
        print(f"🔗 Combining results from {len(batch_results)} processed pages...")
        
        # Separate success/failed results
        success_results = [r for r in batch_results if r.get("status") == "success"]
        failed_results = [r for r in batch_results if r.get("status") == "error"]
        
        print(f"📊 Results: {len(success_results)} success, {len(failed_results)} failed")
        
        # Create combined markdown file
        combined_markdown_file = self._create_combined_markdown(success_results, source_file)
        
        # Generate enhanced statistics
        stats = self._generate_enhanced_statistics(batch_results, total_time, header_cleaning_info)
        
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
            "header_cleaning": header_cleaning_info,  # ← NEW
            "created_at": datetime.now().isoformat()
        }
        
        return final_result
    
    def _create_combined_markdown(self, success_results: List[Dict], source_file: str) -> Optional[Path]:
        """Create combined markdown file from successful results"""
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
    
    def _generate_enhanced_statistics(self, batch_results: List[Dict], total_time: float, 
                                    header_cleaning_info: Dict) -> Dict:
        """Generate enhanced statistics including header cleaning info"""
        total_pages = len(batch_results)
        success_pages = len([r for r in batch_results if r.get("status") == "success"])
        failed_pages = total_pages - success_pages
        
        # Table detection stats
        pages_with_tables = sum(1 for r in batch_results 
                              if r.get("status") == "success" and r.get("has_tables", False))
        
        # Content length stats
        original_lengths = [r.get("original_content_length", r.get("content_length", 0)) 
                          for r in batch_results if r.get("status") == "success"]
        cleaned_lengths = [r.get("cleaned_content_length", r.get("content_length", 0)) 
                         for r in batch_results if r.get("status") == "success"]
        
        avg_original_length = sum(original_lengths) / len(original_lengths) if original_lengths else 0
        avg_cleaned_length = sum(cleaned_lengths) / len(cleaned_lengths) if cleaned_lengths else 0
        
        # Header cleaning stats
        pages_with_headers_removed = sum(1 for r in batch_results 
                                       if r.get("status") == "success" and r.get("header_cleaned", False))
        
        stats = {
            "total_pages": total_pages,
            "successful_pages": success_pages,
            "failed_pages": failed_pages,
            "success_rate": success_pages / total_pages if total_pages > 0 else 0,
            "pages_with_tables": pages_with_tables,
            "total_processing_time_seconds": total_time,
            "average_time_per_page": total_time / total_pages if total_pages > 0 else 0,
            "average_original_content_length": int(avg_original_length),
            "average_cleaned_content_length": int(avg_cleaned_length),
            # NEW: Header cleaning statistics
            "header_cleaning": {
                "applied": header_cleaning_info["applied"],
                "patterns_detected": header_cleaning_info["patterns_detected"],
                "pages_cleaned": pages_with_headers_removed,
                "total_bytes_removed": header_cleaning_info["bytes_removed"],
                "cleaning_efficiency": header_cleaning_info["efficiency"],
                "pattern_types_found": header_cleaning_info["pattern_types"]
            }
        }
        
        return stats