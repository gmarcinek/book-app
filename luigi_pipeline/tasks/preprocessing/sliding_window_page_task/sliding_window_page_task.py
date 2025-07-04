import time
from pathlib import Path
from typing import Dict

from llm import LLMClient, LLMConfig


class SlidingWindowPageTask:
    """
    Single page processor for sliding window
    
    Helper class (not Luigi task) - processes individual pages for LLMMarkdownProcessor
    """
    
    def __init__(self, page: Dict, model: str, llm_config: LLMConfig, 
                 markdown_dir: Path, rate_limit_backoff: float = 30.0):
        self.page = page
        self.model = model
        self.llm_config = llm_config
        self.markdown_dir = markdown_dir
        self.rate_limit_backoff = rate_limit_backoff
        self.llm_client = LLMClient(model)
    
    def process_page(self) -> Dict:
        """Process single page and save to markdown_dir"""
        page_num = self.page["page_num"]
        
        try:
            print(f"📄 Processing page {page_num}...")
            
            # Convert page to markdown using LLM Vision
            markdown_content = self._convert_page_to_markdown()
            
            # Save individual page file to provided markdown_dir
            page_file = self._save_page_markdown(page_num, markdown_content)
            
            return {
                "page_num": page_num,
                "status": "success",
                "markdown_content": markdown_content,
                "markdown_file": str(page_file),
                "has_tables": self._detect_tables(markdown_content),
                "content_length": len(markdown_content)
            }
            
        except Exception as e:
            print(f"❌ Page {page_num} failed: {e}")
            
            # Rate limit handling
            if self._is_rate_limit_error(e):
                print(f"🚨 Rate limit detected! Waiting {self.rate_limit_backoff}s...")
                time.sleep(self.rate_limit_backoff)
                
                # Try once more after backoff
                try:
                    print(f"🔄 Retry after rate limit for page {page_num}...")
                    markdown_content = self._convert_page_to_markdown()
                    page_file = self._save_page_markdown(page_num, markdown_content)
                    
                    return {
                        "page_num": page_num,
                        "status": "success",
                        "markdown_content": markdown_content,
                        "markdown_file": str(page_file),
                        "has_tables": self._detect_tables(markdown_content),
                        "content_length": len(markdown_content),
                        "retry_after_rate_limit": True
                    }
                except Exception as retry_e:
                    print(f"❌ Retry also failed for page {page_num}: {retry_e}")
                    return {
                        "page_num": page_num,
                        "status": "error",
                        "error": f"Rate limit retry failed: {retry_e}",
                        "original_rate_limit_error": str(e)
                    }
            
            return {
                "page_num": page_num,
                "status": "error",
                "error": str(e)
            }
    
    def _convert_page_to_markdown(self) -> str:
        """Convert page using LLM vision"""
        page_num = self.page["page_num"]
        extracted_text = self.page.get("text", "")
        image_base64 = self.page.get("image_base64")
        
        # Build enhanced prompt
        prompt = f"""Look at the provided image and extracted text. You are converting **a single page** from a multi-page PDF document into clean, structured Markdown.
This page is only one of many (dozens), so **do not assume it starts a new article or section**.

EXTRACTED TEXT (from OCR or PDF text layer):
{extracted_text}

REQUIREMENTS:
0. **LITERARY HEADINGS** - Valid headings always include **words**, not just a number. 
1. **ACCURACY** - Use extracted text for content, image for visual structure
2. **PRESERVE ALL DATA** - Include all information, numbers, table rows
3. **NO PAGE METADATA** - Remove page numbers, headers, footers

HEADER VS POINT LIST
❌ `7.` → likely a numbered item  
✅ `Art. 5 – Zakres` → heading  
❌ `9.` → subpoint  
✅ `Rozdział 3 – Warianty` → heading  
✅ `Chapter 19 – Termination` → heading  

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
- Remove page numbers

OUTPUT: Clean Markdown only, no explanations or metadata."""
        
        # Prepare images for vision models
        images = [image_base64] if image_base64 else None
        
        # Call LLM with enhanced prompt
        response = self.llm_client.chat(prompt, self.llm_config, images=images)
        
        # Clean response
        markdown_content = self._clean_markdown_response(response)
        
        return markdown_content
    
    def _clean_markdown_response(self, response: str) -> str:
        """Clean and validate Markdown response"""
        # Remove common LLM response artifacts
        markdown = response.strip()
        
        # Remove markdown code blocks if LLM wrapped the response
        if markdown.startswith("```markdown"):
            markdown = markdown[11:]
        if markdown.startswith("```"):
            markdown = markdown[3:]
        if markdown.endswith("```"):
            markdown = markdown[:-3]
        
        # Clean up extra whitespace
        lines = markdown.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_lines.append(line.rstrip())
        
        # Join back and ensure proper ending
        markdown = '\n'.join(cleaned_lines).strip()
        
        # Ensure content exists
        if not markdown or len(markdown) < 10:
            return "[No content could be extracted]"
        
        return markdown
    
    def _save_page_markdown(self, page_num: int, content: str) -> Path:
        """Save markdown for single page to provided markdown_dir"""
        page_file = self.markdown_dir / f"page_{page_num:03d}.md"
        page_file.write_text(content, encoding='utf-8')
        return page_file
    
    def _detect_tables(self, content: str) -> bool:
        """Simple table detection in markdown"""
        return '|' in content and content.count('|') >= 4
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Detect OpenAI/Claude rate limit errors"""
        error_str = str(error).lower()
        return any(phrase in error_str for phrase in [
            "rate limit",
            "429",
            "too many requests",
            "rate_limit_exceeded"
        ])