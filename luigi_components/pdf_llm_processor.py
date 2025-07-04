import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable
import fitz
import base64
from pathlib import Path

from llm import LLMClient, LLMConfig


@dataclass
class ProcessingConfig:
    """Config for PDF → LLM processing"""
    model: str = "claude-3.5-haiku"
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    max_concurrent: int = 2
    rate_limit_backoff: float = 30.0
    
    # Image settings
    target_width_px: int = 800
    jpg_quality: int = 65
    
    # Prompt template with {text_content} placeholder
    prompt_template: str = ""


@dataclass
class PageResult:
    """Result from processing single page"""
    page_num: int
    status: str  # "success" or "error"
    result: Dict[str, Any] = None
    error: str = ""
    retry_after_rate_limit: bool = False


class SlidingWindowPageProcessor:
    """Single page processor for sliding window - extracted from luigi_pipeline"""
    
    def __init__(self, page_data: Dict, config: ProcessingConfig, 
                 response_parser: Callable[[str], Dict[str, Any]] = None):
        self.page_data = page_data
        self.config = config
        self.response_parser = response_parser
        self.llm_client = LLMClient(config.model)
        self.llm_config = LLMConfig(
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    
    def process_page(self) -> PageResult:
        """Process single page and return result"""
        page_num = self.page_data["page_num"]
        
        try:
            print(f"📄 Processing page {page_num}...")
            
            # Call LLM with text + image
            result = self._call_llm_vision()
            
            return PageResult(
                page_num=page_num,
                status="success",
                result=result
            )
            
        except Exception as e:
            print(f"❌ Page {page_num} failed: {e}")
            
            # Rate limit handling - copied from luigi_pipeline
            if self._is_rate_limit_error(e):
                print(f"🚨 Rate limit detected! Waiting {self.config.rate_limit_backoff}s...")
                time.sleep(self.config.rate_limit_backoff)
                
                # Try once more after backoff
                try:
                    print(f"🔄 Retry after rate limit for page {page_num}...")
                    result = self._call_llm_vision()
                    
                    return PageResult(
                        page_num=page_num,
                        status="success",
                        result=result,
                        retry_after_rate_limit=True
                    )
                except Exception as retry_e:
                    print(f"❌ Retry also failed for page {page_num}: {retry_e}")
                    return PageResult(
                        page_num=page_num,
                        status="error",
                        error=f"Rate limit retry failed: {retry_e}"
                    )
            
            return PageResult(
                page_num=page_num,
                status="error",
                error=str(e)
            )
    
    def _call_llm_vision(self) -> Dict[str, Any]:
        """Call LLM with vision - core logic"""
        text = self.page_data.get("text", "")
        image_base64 = self.page_data.get("image_base64")
        
        # Build prompt
        prompt = self.config.prompt_template.replace("{text_content}", text)
        
        # Call LLM with image
        response = self.llm_client.chat(prompt, self.llm_config, images=[image_base64])
        
        # Parse response
        if self.response_parser:
            parsed_result = self.response_parser(response)
            if parsed_result is None:
                raise ValueError("Failed to parse LLM response")
            return parsed_result
        else:
            return {"raw_response": response}
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Detect rate limit errors - copied from luigi_pipeline"""
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "rate limit",
            "429",
            "too many requests",
            "rate_limit_exceeded"
        ])


class PDFLLMProcessor:
    """Generic PDF → screenshots + text → LLM processor with sliding window"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
    
    def process_pdf(self, pdf_path: str, 
                   response_parser: Callable[[str], Dict[str, Any]] = None) -> List[PageResult]:
        """
        Process PDF pages through LLM using sliding window
        
        Args:
            pdf_path: Path to PDF file
            response_parser: Function to parse LLM response (optional)
            
        Returns:
            List of PageResult objects
        """
        print(f"🚀 Starting PDF processing: {Path(pdf_path).name}")
        
        # Extract pages with text + images
        pages_data = self._extract_pages_data(pdf_path)
        
        if not pages_data:
            print("❌ No pages extracted")
            return []
        
        print(f"📊 Processing {len(pages_data)} pages with sliding window (max_concurrent={self.config.max_concurrent})")
        
        # Process with sliding window
        results = asyncio.run(self._process_with_sliding_window(pages_data, response_parser))
        
        # Summary
        success_count = sum(1 for r in results if r.status == "success")
        print(f"✅ Completed: {success_count}/{len(results)} pages successful")
        
        return results
    
    def _extract_pages_data(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract text + images from all PDF pages"""
        doc = fitz.open(pdf_path)
        pages_data = []
        
        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                
                # Extract text
                text = page.get_text().strip() or "[No text extracted]"
                
                # Create screenshot
                image_base64 = self._create_screenshot(page)
                
                pages_data.append({
                    "page_num": page_num + 1,
                    "text": text,
                    "image_base64": image_base64
                })
                
                print(f"📸 Page {page_num + 1}: {len(text)} chars text, {len(image_base64)} chars image")
                
            except Exception as e:
                print(f"❌ Failed to extract page {page_num + 1}: {e}")
                continue
        
        doc.close()
        return pages_data
    
    def _create_screenshot(self, page) -> str:
        """Create base64 screenshot of page"""
        page_rect = page.rect
        zoom = self.config.target_width_px / page_rect.width
        zoom = max(0.5, min(3.0, zoom))
        
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("jpeg", jpg_quality=self.config.jpg_quality)
        
        return base64.b64encode(img_bytes).decode('utf-8')
    
    async def _process_with_sliding_window(self, pages_data: List[Dict], 
                                         response_parser: Callable) -> List[PageResult]:
        """Process pages with sliding window - copied from luigi_pipeline"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def process_single_page(page_data: Dict):
            async with semaphore:
                # Create page processor
                page_processor = SlidingWindowPageProcessor(
                    page_data=page_data,
                    config=self.config,
                    response_parser=response_parser
                )
                
                # Run in thread pool (LLM calls are blocking)
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(executor, page_processor.process_page)
                
                status = "✅" if result.status == "success" else "❌"
                retry_info = " (after rate limit retry)" if result.retry_after_rate_limit else ""
                print(f"{status} Page {result.page_num} completed{retry_info}")
                
                return result
        
        # Process all pages concurrently with sliding window
        tasks = [process_single_page(page_data) for page_data in pages_data]
        results = await asyncio.gather(*tasks)
        
        return results