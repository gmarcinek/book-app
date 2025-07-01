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
    Sliding Window with page persistence - resume from last success
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    def requires(self):
        return PDFProcessing(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/llm_markdown_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Load config
        config = load_config()
        model = config.get_task_setting("LLMMarkdownProcessor", "model", "gpt-4o-mini")
        max_tokens = config.get_max_tokens_for_model(model)
        temperature = config.get_task_setting("LLMMarkdownProcessor", "temperature", 0.0)
        max_concurrent = config.get_task_setting("LLMMarkdownProcessor", "max_concurrent", 5)
        
        # Load PDF data
        with self.input().open('r') as f:
            pdf_data = json.load(f)
        
        pages = pdf_data.get("pages", [])
        if not pages:
            raise ValueError("No pages found")
        
        # Setup directories
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        self.markdown_dir = Path(f"output/markdown_{file_hash}")
        self.page_results_dir = Path(f"output/page_results_{file_hash}")
        self.markdown_dir.mkdir(exist_ok=True)
        self.page_results_dir.mkdir(exist_ok=True)
        
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        # Resume logic: skip existing successful pages
        pages_to_process = []
        for page in pages:
            page_num = page["page_num"]
            result_file = self.page_results_dir / f"page_{page_num:03d}.json"
            
            if result_file.exists():
                try:
                    with open(result_file, 'r') as f:
                        result = json.load(f)
                    if result.get("status") == "success":
                        print(f"⏭️ Page {page_num} already done")
                        continue
                except:
                    pass
            
            pages_to_process.append(page)
        
        print(f"🔄 Processing {len(pages_to_process)}/{len(pages)} pages")
        
        # Process remaining pages
        if pages_to_process:
            asyncio.run(self._process_with_save(pages_to_process, model, llm_config, max_concurrent))
        
        # Load all results and sort by page number
        all_results = []
        for page in pages:
            page_num = page["page_num"]
            result_file = self.page_results_dir / f"page_{page_num:03d}.json"
            
            if result_file.exists():
                with open(result_file, 'r') as f:
                    all_results.append(json.load(f))
            else:
                all_results.append({"page_num": page_num, "status": "error", "error": "Missing result"})
        
        # Sort by page number - CRITICAL for correct order
        all_results.sort(key=lambda x: x.get("page_num", 0))
        
        # Final output
        success_count = sum(1 for r in all_results if r.get("status") == "success")
        
        output_data = {
            "task_name": "LLMMarkdownProcessor",
            "input_file": str(self.file_path),
            "model_used": model,
            "batch_results": all_results,
            "statistics": {
                "total_pages": len(all_results),
                "successful_pages": success_count,
                "failed_pages": len(all_results) - success_count
            },
            "markdown_directory": str(self.markdown_dir),
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {success_count}/{len(all_results)} pages successful")
    
    async def _process_with_save(self, pages: List[Dict], model: str, llm_config: LLMConfig, max_concurrent: int):
        """Process pages with immediate save"""
        semaphore = Semaphore(max_concurrent)
        
        async def process_and_save(page: Dict):
            async with semaphore:
                # Process page
                page_task = SlidingWindowPageTask(
                    page=page,
                    model=model,
                    llm_config=llm_config,
                    markdown_dir=self.markdown_dir,
                    rate_limit_backoff=30.0
                )
                
                import concurrent.futures
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, page_task.process_page)
                
                # Save immediately
                page_num = result.get("page_num", 0)
                result_file = self.page_results_dir / f"page_{page_num:03d}.json"
                
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                status = "✅" if result.get("status") == "success" else "❌"
                print(f"{status} Page {page_num} saved")
                
                return result
        
        # Process all pages
        tasks = [process_and_save(page) for page in pages]
        await asyncio.gather(*tasks)