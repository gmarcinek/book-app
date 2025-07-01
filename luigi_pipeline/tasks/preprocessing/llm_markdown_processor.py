# PLIK: luigi_pipeline/tasks/preprocessing/llm_markdown_processor.py
import luigi
import json
import hashlib
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from asyncio import Semaphore

from llm import LLMClient, LLMConfig
from luigi_pipeline.config import load_config
from .pdf_processing import PDFProcessing
from .sliding_window_page_task import SlidingWindowPageTask


class LLMMarkdownProcessor(luigi.Task):
    """
    Sliding Window Coordinator dla parallel processing stron
    
    IMPROVED: Sliding window instead of batches
    - Max N concurrent pages at any time
    - Continuous flow as pages complete
    - Better throughput, handles slow pages
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    def requires(self):
        return PDFProcessing(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/llm_markdown_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Load configuration
        config = load_config()
        
        # Get sliding window settings
        model = config.get_task_setting("LLMMarkdownProcessor", "model", "gpt-4o-mini")
        max_tokens = config.get_max_tokens_for_model(model)
        temperature = config.get_task_setting("LLMMarkdownProcessor", "temperature", 0.0)
        max_concurrent = config.get_task_setting("LLMMarkdownProcessor", "max_concurrent", 5)  # NEW: sliding window size
        retry_failed = config.get_task_setting("LLMMarkdownProcessor", "retry_failed_pages", True)
        rate_limit_backoff = config.get_task_setting("LLMMarkdownProcessor", "rate_limit_backoff", 30.0)
        
        # Load PDF processing results
        with self.input().open('r') as f:
            pdf_data = json.load(f)
        
        if pdf_data.get("task_name") != "PDFProcessing":
            raise ValueError("Expected PDFProcessing input data")
        
        pages = pdf_data.get("pages", [])
        if not pages:
            raise ValueError("No pages found in PDF data")
        
        print(f"🚀 SLIDING WINDOW MODE: {len(pages)} pages, max_concurrent={max_concurrent}")
        print(f"📊 Model: {model}, max_tokens={max_tokens}, temperature={temperature}")
        print(f"⏱️ Rate limit backoff: {rate_limit_backoff}s")
        
        # Setup markdown directory
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        self.markdown_dir = Path(f"output/markdown_{file_hash}")
        self.markdown_dir.mkdir(exist_ok=True)
        
        # Setup LLM config
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        # Process all pages with sliding window
        start_time = time.time()
        all_results = asyncio.run(self._process_pages_sliding_window(
            pages, model, llm_config, max_concurrent, rate_limit_backoff
        ))
        total_time = time.time() - start_time
        
        # Retry failed pages if enabled
        if retry_failed:
            all_results = self._retry_failed_pages(all_results, model, llm_config)
        
        # Create raw results output
        success_results = [r for r in all_results if r.get("status") == "success"]
        failed_results = [r for r in all_results if r.get("status") == "error"]
        
        output_data = {
            "task_name": "LLMMarkdownProcessor",
            "input_file": str(self.file_path),
            "model_used": model,
            "processing_mode": "sliding_window",
            "config": {
                "max_concurrent": max_concurrent,
                "retry_failed_pages": retry_failed,
                "rate_limit_backoff": rate_limit_backoff,
                "max_tokens": max_tokens,
                "temperature": temperature
            },
            "status": "success",
            "batch_results": all_results,
            "statistics": {
                "total_pages": len(all_results),
                "successful_pages": len(success_results),
                "failed_pages": len(failed_results),
                "success_rate": len(success_results) / len(all_results) if all_results else 0,
                "pages_with_tables": sum(1 for r in success_results if r.get("has_tables", False)),
                "total_processing_time_seconds": total_time,
                "average_time_per_page": total_time / len(all_results) if all_results else 0
            },
            "markdown_directory": str(self.markdown_dir),
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"✅ SLIDING WINDOW PROCESSING COMPLETE:")
        print(f"   📊 {len(success_results)}/{len(all_results)} pages successful")
        print(f"   ⏱️  Total time: {total_time:.1f}s (avg: {total_time/len(all_results):.1f}s/page)")
        print(f"   📁 Raw results: {self.output().path}")
        print(f"   ➡️  Next: Run BatchResultCombinerTask to create combined markdown")
    
    async def _process_pages_sliding_window(self, pages: List[Dict], model: str, 
                                           llm_config: LLMConfig, max_concurrent: int,
                                           rate_limit_backoff: float) -> List[Dict]:
        """
        Sliding window processing - max N concurrent pages at any time
        
        Continuous flow: jak jedna strona się kończy, startuje następna
        """
        print(f"🌊 Starting sliding window processing with max {max_concurrent} concurrent pages...")
        
        # Create semaphore for bounded parallelism
        semaphore = Semaphore(max_concurrent)
        
        # Process page with semaphore limit
        async def process_page_with_limit(page: Dict, page_index: int):
            async with semaphore:
                return await self._process_single_page_async(
                    page, page_index, model, llm_config, rate_limit_backoff
                )
        
        # Start all pages with sliding window constraint
        print(f"🚀 Launching {len(pages)} pages into sliding window...")
        
        tasks = [
            process_page_with_limit(page, i) 
            for i, page in enumerate(pages)
        ]
        
        # Wait for all to complete with continuous progress updates
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            page_num = result.get("page_num", "?")
            status = "✅" if result.get("status") == "success" else "❌"
            print(f"{status} Page {page_num} completed ({completed}/{len(pages)})")
        
        # Sort results by page number for consistent output
        results.sort(key=lambda x: x.get("page_num", 0))
        
        return results
    
    async def _process_single_page_async(self, page: Dict, page_index: int, 
                                        model: str, llm_config: LLMConfig,
                                        rate_limit_backoff: float) -> Dict:
        """
        Async wrapper for single page processing using SlidingWindowPageTask
        """
        import asyncio
        import concurrent.futures
        
        def sync_process_page():
            # Use SlidingWindowPageTask for actual processing
            page_task = SlidingWindowPageTask(
                page=page,
                model=model,
                llm_config=llm_config,
                markdown_dir=self.markdown_dir,
                rate_limit_backoff=rate_limit_backoff
            )
            return page_task.process_page()
        
        # Run in thread executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, sync_process_page)
        
        return result
    
    def _retry_failed_pages(self, results: List[Dict], model: str, llm_config: LLMConfig) -> List[Dict]:
        """Simple retry logic for failed pages"""
        failed_results = [r for r in results if r.get("status") == "error"]
        
        if not failed_results:
            print("✅ No failed pages to retry")
            return results
        
        print(f"🔄 Retrying {len(failed_results)} failed pages...")
        
        for failed_result in failed_results:
            page_num = failed_result["page_num"]
            print(f"🔁 Retrying page {page_num}...")
            
            try:
                failed_result["retry_attempted"] = True
                failed_result["retry_timestamp"] = datetime.now().isoformat()
                
            except Exception as e:
                print(f"❌ Retry failed for page {page_num}: {e}")
                failed_result["retry_error"] = str(e)
        
        return results