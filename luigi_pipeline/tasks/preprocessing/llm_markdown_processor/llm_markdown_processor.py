import luigi
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from asyncio import Semaphore

from llm import LLMConfig
from luigi_components.structured_task import StructuredTask
from luigi_pipeline.config import load_config
from luigi_pipeline.tasks.preprocessing.pdf_processing.pdf_processing import PDFProcessing
from luigi_pipeline.tasks.preprocessing.sliding_window_page_task.sliding_window_page_task import SlidingWindowPageTask


class LLMMarkdownProcessor(StructuredTask):
    """
    Sliding Window with page persistence - resume from last success
    Saves markdown files to task-specific directory
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "llm_markdown_processor"
    
    def requires(self):
        return PDFProcessing(file_path=self.file_path)
    
    def run(self):
        # Load config
        config = load_config()
        model = config.get_task_setting("LLMMarkdownProcessor", "model", "gpt-4o-mini")
        max_tokens = config.get_max_tokens_for_model(model)
        temperature = config.get_task_setting("LLMMarkdownProcessor", "temperature", 0.0)
        max_concurrent = config.get_task_setting("LLMMarkdownProcessor", "max_concurrent", 5)
        rate_limit_backoff = config.get_task_setting("LLMMarkdownProcessor", "rate_limit_backoff", 30.0)
        
        # Load PDF data
        with self.input().open('r') as f:
            pdf_data = json.load(f)
        
        pages = pdf_data.get("pages", [])
        if not pages:
            raise ValueError("No pages found")
        
        # Create task-specific directories
        task_dir = Path("output") / self.pipeline_name / self.task_name
        markdown_dir = task_dir / "markdown"
        page_results_dir = task_dir / "page_results"
        markdown_dir.mkdir(parents=True, exist_ok=True)
        page_results_dir.mkdir(parents=True, exist_ok=True)
        
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        # Resume logic: skip existing successful pages
        pages_to_process = []
        for page in pages:
            page_num = page["page_num"]
            result_file = page_results_dir / f"page_{page_num:03d}.json"
            
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
            asyncio.run(self._process_with_save(pages_to_process, model, llm_config, max_concurrent, 
                                              markdown_dir, page_results_dir, rate_limit_backoff))
        
        # Load all results and sort by page number
        all_results = []
        for page in pages:
            page_num = page["page_num"]
            result_file = page_results_dir / f"page_{page_num:03d}.json"
            
            if result_file.exists():
                with open(result_file, 'r') as f:
                    all_results.append(json.load(f))
            else:
                all_results.append({"page_num": page_num, "status": "error", "error": "Missing result"})
        
        # Sort by page number
        all_results.sort(key=lambda x: x.get("page_num", 0))
        
        # Final output
        success_count = sum(1 for r in all_results if r.get("status") == "success")
        
        result = {
            "task_name": "LLMMarkdownProcessor",
            "input_file": str(self.file_path),
            "model_used": model,
            "batch_results": all_results,
            "statistics": {
                "total_pages": len(all_results),
                "successful_pages": success_count,
                "failed_pages": len(all_results) - success_count
            },
            "markdown_directory": str(markdown_dir),
            "page_results_directory": str(page_results_dir),
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {success_count}/{len(all_results)} pages successful")
    
    async def _process_with_save(self, pages: List[Dict], model: str, llm_config: LLMConfig, 
                                max_concurrent: int, markdown_dir: Path, page_results_dir: Path,
                                rate_limit_backoff: float):
        """Process pages with immediate save to task directories"""
        semaphore = Semaphore(max_concurrent)
        
        async def process_and_save(page: Dict):
            async with semaphore:
                # Process page
                page_task = SlidingWindowPageTask(
                    page=page,
                    model=model,
                    llm_config=llm_config,
                    markdown_dir=markdown_dir,
                    rate_limit_backoff=rate_limit_backoff
                )
                
                import concurrent.futures
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, page_task.process_page)
                
                # Save result to task directory
                page_num = result.get("page_num", 0)
                result_file = page_results_dir / f"page_{page_num:03d}.json"
                
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                status = "✅" if result.get("status") == "success" else "❌"
                print(f"{status} Page {page_num} saved")
                
                return result
        
        # Process all pages
        tasks = [process_and_save(page) for page in pages]
        await asyncio.gather(*tasks)