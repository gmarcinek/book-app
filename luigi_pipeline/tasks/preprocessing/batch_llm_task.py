# PLIK: luigi_pipeline/tasks/preprocessing/batch_llm_task.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from pathlib import Path

from llm import LLMClient, LLMConfig


class BatchLLMTask:
    """
    Przetwarza batch stron (np. 3 strony) równolegle używając ThreadPoolExecutor
    
    YAGNI: Prosty async wrapper dla LLM calls z rate limit handling
    """
    
    def __init__(self, batch_pages: List[Dict], model: str, llm_config: LLMConfig, 
                 markdown_dir: Path, batch_id: int, rate_limit_backoff: float = 30.0):
        """
        Args:
            batch_pages: Lista stron do przetworzenia (max batch_size)
            model: Model LLM do użycia
            llm_config: Konfiguracja LLM
            markdown_dir: Katalog do zapisywania wyników
            batch_id: ID batcha dla logów
            rate_limit_backoff: Czas oczekiwania po rate limit (seconds)
        """
        self.batch_pages = batch_pages
        self.model = model
        self.llm_config = llm_config
        self.markdown_dir = markdown_dir
        self.batch_id = batch_id
        self.rate_limit_backoff = rate_limit_backoff
        self.llm_client = LLMClient(model)
    
    async def process_batch(self) -> List[Dict]:
        """
        Przetwarza cały batch równolegle
        
        Returns:
            Lista wyników - jeden dict na stronę
        """
        batch_size = len(self.batch_pages)
        print(f"🚀 Batch {self.batch_id}: Processing {batch_size} pages in parallel...")
        
        start_time = time.time()
        
        # ThreadPoolExecutor dla I/O bound LLM calls
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            loop = asyncio.get_event_loop()
            
            # Submit wszystkie strony jednocześnie
            futures = []
            for i, page in enumerate(self.batch_pages):
                future = loop.run_in_executor(
                    executor, 
                    self._process_single_page, 
                    page, 
                    i
                )
                futures.append(future)
            
            # Czekaj na wszystkie wyniki
            results = await asyncio.gather(*futures, return_exceptions=True)
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if isinstance(r, dict) and "error" not in r)
        
        print(f"✅ Batch {self.batch_id}: {success_count}/{batch_size} pages completed in {elapsed:.1f}s")
        
        return self._handle_results(results)
    
    def _process_single_page(self, page: Dict, page_index: int) -> Dict:
        """
        Przetwarza pojedynczą stronę (sync call w ThreadPoolExecutor)
        
        Args:
            page: Page data z PDFProcessing
            page_index: Index w batchu
            
        Returns:
            Dict z rezultatem lub błędem
        """
        page_num = page["page_num"]
        print(f"📄 Batch {self.batch_id}: Processing page {page_num}")
        
        try:
            # Process page to markdown
            markdown_content = self._convert_page_to_markdown(page)
            
            # Save individual page file
            page_file = self._save_page_markdown(page_num, markdown_content)
            
            return {
                "page_num": page_num,
                "batch_id": self.batch_id,
                "status": "success",
                "markdown_content": markdown_content,
                "markdown_file": str(page_file),
                "has_tables": self._detect_tables(markdown_content),
                "content_length": len(markdown_content)
            }
            
        except Exception as e:
            print(f"❌ Batch {self.batch_id}: Page {page_num} failed: {e}")
            return {
                "page_num": page_num,
                "batch_id": self.batch_id,
                "status": "error",
                "error": str(e)
            }
    
    def _convert_page_to_markdown(self, page: Dict) -> str:
        """
        Konwertuje stronę na markdown używając LLM Vision
        
        Medium-length prompt: najważniejsze elementy bez redundancji
        """
        page_num = page["page_num"]
        extracted_text = page.get("text", "")
        image_base64 = page.get("image_base64")
        
        # Medium-length enhanced prompt - key essentials only
        prompt = f"""Convert this PDF page to clean, professional Markdown.

EXTRACTED TEXT:
{extracted_text}

REQUIREMENTS:
1. **ACCURACY** - Use extracted text for content, image for visual structure
2. **PRESERVE ALL DATA** - Include all information, numbers, table rows
3. **NO PAGE METADATA** - Remove page numbers, headers, footers

TABLE FORMATTING:
- Use proper Markdown syntax: | separators and |----| header separators
- Include ALL rows and columns from the image
- Keep numerical values properly aligned

EXAMPLE:
| Nazwa | Ilość | Cena | Wartość |
|-------|-------|------|---------|
| Usługa | 2 | 100,00 | 200,00 |

STRUCTURE:
- ## for main sections
- **Bold** for field labels
- Clean formatting for addresses and contact info

OUTPUT: Clean Markdown only, no explanations or metadata."""
        
        # Prepare images for vision models
        images = [image_base64] if image_base64 else None
        
        # Call LLM with enhanced prompt
        response = self.llm_client.chat(prompt, self.llm_config, images=images)
        
        # Clean response using same logic as original
        markdown_content = self._clean_markdown_response(response)
        
        return markdown_content
    
    def _clean_markdown_response(self, response: str) -> str:
        """
        Clean and validate Markdown response
        
        Copied from original LLMMarkdownProcessor._clean_markdown_response
        """
        # Remove common LLM response artifacts
        markdown = response.strip()
        
        # Remove markdown code blocks if LLM wrapped the response
        if markdown.startswith("```markdown"):
            markdown = markdown[11:]  # Remove ```markdown
        if markdown.startswith("```"):
            markdown = markdown[3:]   # Remove ```
        if markdown.endswith("```"):
            markdown = markdown[:-3]  # Remove trailing ```
        
        # Clean up extra whitespace
        lines = markdown.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_lines.append(line.rstrip())  # Remove trailing whitespace
        
        # Join back and ensure proper ending
        markdown = '\n'.join(cleaned_lines).strip()
        
        # Ensure content exists
        if not markdown or len(markdown) < 10:
            return "[No content could be extracted]"
        
        return markdown
    
    def _save_page_markdown(self, page_num: int, content: str) -> Path:
        """Zapisuje markdown pojedynczej strony"""
        page_file = self.markdown_dir / f"page_{page_num:03d}.md"
        page_file.write_text(content, encoding='utf-8')
        return page_file
    
    def _detect_tables(self, content: str) -> bool:
        """Prosty detektor tabel w markdown"""
        return '|' in content and content.count('|') >= 4
    
    def _handle_results(self, results: List) -> List[Dict]:
        """
        Obsługuje wyniki z asyncio.gather (włącznie z exceptions)
        
        Returns:
            Lista dict'ów z wynikami
        """
        processed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Exception z asyncio.gather
                page_num = self.batch_pages[i]["page_num"]
                processed_results.append({
                    "page_num": page_num,
                    "batch_id": self.batch_id,
                    "status": "error",
                    "error": f"Async error: {result}"
                })
            else:
                # Normalny wynik
                processed_results.append(result)
        
        return processed_results
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Detect OpenAI rate limit errors"""
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "rate limit",
            "429",
            "too many requests",
            "rate_limit_exceeded"
        ])