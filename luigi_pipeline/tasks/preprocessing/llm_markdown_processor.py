import luigi
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path

from llm import LLMClient, LLMConfig
from ..config import load_config
from .pdf_processing import PDFProcessing


class LLMMarkdownProcessor(luigi.Task):
    """
    Converts PDF pages to Markdown using LLM Vision models
    
    Processes each page (image + text) and generates clean Markdown,
    with special attention to table structure preservation
    Enhanced with progress logging and intermediate saves
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")  # default, fast, quality
    
    def requires(self):
        return PDFProcessing(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/llm_markdown_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Load YAML configuration
        config = load_config()
        
        # Get task-specific settings
        model = config.get_task_setting("LLMMarkdownProcessor", "model", "gpt-4o-mini")
        max_tokens = config.get_max_tokens_for_model(model)  # Auto from llm.models
        temperature = config.get_task_setting("LLMMarkdownProcessor", "temperature", 0.0)
        page_delay = config.get_model_delay(model)
        
        # Load PDF processing results
        with self.input().open('r') as f:
            pdf_data = json.load(f)
        
        if pdf_data.get("task_name") != "PDFProcessing":
            raise ValueError("Expected PDFProcessing input data")
        
        pages = pdf_data.get("pages", [])
        if not pages:
            raise ValueError("No pages found in PDF data")
        
        print(f"🚀 Starting LLM processing: {len(pages)} pages with {model}")
        print(f"📊 Config: max_tokens={max_tokens} (from llm.models), temperature={temperature}, delay={page_delay}s")
        
        # Prepare markdown directory for intermediate saves
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        self.markdown_dir = Path(f"output/markdown_{file_hash}")
        self.markdown_dir.mkdir(exist_ok=True)
        
        # Initialize LLM client
        llm_client = LLMClient(model)
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        # Process each page with progress tracking
        markdown_pages = []
        total_time = 0
        
        for i, page in enumerate(pages):
            page_num = page["page_num"]
            print(f"\n🔄 Processing page {page_num}/{len(pages)} ({i+1}/{len(pages)})...")
            start_time = time.time()
            
            try:
                markdown_content = self._process_page_to_markdown(
                    page, llm_client, llm_config
                )
                
                elapsed = time.time() - start_time
                total_time += elapsed
                avg_time = total_time / (i + 1)
                remaining_pages = len(pages) - (i + 1)
                eta_minutes = (avg_time * remaining_pages) / 60
                
                print(f"✅ Page {page_num} completed in {elapsed:.1f}s (avg: {avg_time:.1f}s, ETA: {eta_minutes:.1f}min)")
                
                # Save individual page immediately (clean content only)
                save_individual = config.get_task_setting("MarkdownCombiner", "save_individual_pages", True)
                if save_individual:
                    self._save_single_page_md(page_num, markdown_content)
                
                markdown_pages.append({
                    "page_num": page_num,
                    "markdown": markdown_content,
                    "original_text_length": page["text_length"],
                    "has_tables": self._detect_tables(markdown_content),
                    "processing_time_seconds": elapsed
                })
                
                # Provider-specific delay between pages
                if page_delay > 0 and i < len(pages) - 1:
                    print(f"😴 Provider delay: {page_delay}s...")
                    time.sleep(page_delay)
                
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"❌ Page {page_num} FAILED after {elapsed:.1f}s: {e}")
                
                error_markdown = f"[Error processing page: {str(e)}]"
                save_individual = config.get_task_setting("MarkdownCombiner", "save_individual_pages", True)
                if save_individual:
                    self._save_single_page_md(page_num, error_markdown, error=True)
                
                markdown_pages.append({
                    "page_num": page_num,
                    "markdown": error_markdown,
                    "original_text_length": page["text_length"],
                    "has_tables": False,
                    "error": str(e),
                    "processing_time_seconds": elapsed
                })
        
        print(f"\n🎉 All pages processed! Total time: {total_time/60:.1f} minutes")
        
        # Save combined markdown file (clean content only)
        markdown_file_path = None
        save_combined = config.get_task_setting("MarkdownCombiner", "save_combined_file", True)
        if save_combined:
            markdown_file_path = self._save_combined_markdown_file(markdown_pages)
        
        # Create output with enhanced stats
        success_pages = len([p for p in markdown_pages if "error" not in p])
        failed_pages = len(markdown_pages) - success_pages
        save_individual = config.get_task_setting("MarkdownCombiner", "save_individual_pages", True)
        
        output_data = {
            "task_name": "LLMMarkdownProcessor",
            "input_file": str(self.file_path),
            "model_used": model,
            "config": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "page_delay": page_delay
            },
            "status": "success",
            "pages_count": len(markdown_pages),
            "pages_successful": success_pages,
            "pages_failed": failed_pages,
            "pages_with_tables": sum(1 for p in markdown_pages if p.get("has_tables", False)),
            "total_processing_time_seconds": total_time,
            "average_time_per_page": total_time / len(pages) if pages else 0,
            "markdown_file": str(markdown_file_path) if markdown_file_path else None,
            "markdown_directory": str(self.markdown_dir),
            "individual_page_files": list(self.markdown_dir.glob("page_*.md")) if save_individual else [],
            "markdown_pages": markdown_pages,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
    
    def _save_single_page_md(self, page_num, markdown_content, error=False):
        """Save individual page as separate .md file immediately - CLEAN CONTENT ONLY"""
        try:
            # Fix escaped newlines
            if '\\n' in markdown_content:
                markdown_content = markdown_content.replace('\\n', '\n')
            
            # Create filename
            status = "ERROR" if error else "OK"
            filename = f"page_{page_num:03d}_{status}.md"
            page_file_path = self.markdown_dir / filename
            
            # Save ONLY the clean content without any headers or metadata
            page_file_path.write_text(markdown_content, encoding='utf-8')
            print(f"💾 Saved: {filename}")
            
        except Exception as e:
            print(f"⚠️ Failed to save page {page_num}: {e}")
    
    def _save_combined_markdown_file(self, markdown_pages):
        """Save combined markdown to single .md file - CLEAN CONTENT ONLY"""
        try:
            source_name = Path(self.file_path).stem
            markdown_file_path = self.markdown_dir / f"{source_name}_COMBINED.md"
            
            # Build combined content - NO METADATA, just clean content
            all_content = []
            for page_data in markdown_pages:
                page_markdown = page_data["markdown"]
                # Fix escaped newlines
                if '\\n' in page_markdown:
                    page_markdown = page_markdown.replace('\\n', '\n')
                
                # Add content without any page headers or metadata
                if page_markdown.strip():
                    all_content.append(page_markdown.strip())
            
            # Join with simple separator
            combined = "\n\n---\n\n".join(all_content)
            markdown_file_path.write_text(combined, encoding='utf-8')
            
            print(f"📝 Saved combined markdown: {markdown_file_path}")
            return markdown_file_path
            
        except Exception as e:
            print(f"⚠️ Failed to save combined markdown: {e}")
            return None
    
    def _process_page_to_markdown(self, page, llm_client, config):
        """Convert single page (image + text) to Markdown using LLM Vision"""
        
        # Prepare prompt for vision model
        prompt = self._build_markdown_conversion_prompt(page)
        
        # Vision call - images jako lista base64
        images = [page["image_base64"]]
        response = llm_client.chat(prompt, config, images=images)
        
        # Clean and validate markdown
        markdown = self._clean_markdown_response(response)
        return markdown
    
    def _build_markdown_conversion_prompt(self, page):
        """Enhanced prompt with better structure and specific table instructions"""
        
        extracted_text = page.get("extracted_text", "")
        
        prompt = f"""You are a document conversion specialist. Convert this PDF page to clean, professional Markdown.

EXTRACTED TEXT FROM PDF:
{extracted_text}

CORE REQUIREMENTS:
1. **ACCURACY FIRST** - Use extracted text for precise content, image for visual structure
2. **PRESERVE ALL DATA** - Don't skip any information, numbers, or table rows
3. **CLEAN FORMATTING** - Remove page numbers, headers, footers, and metadata unless content-relevant
4. **NO PAGE REFERENCES** - Do not include any page numbers or page-related metadata in the output

TABLE FORMATTING (CRITICAL):
- **MANDATORY**: Use proper Markdown table syntax with | separators
- **HEADERS**: Always include header row with column names
- **SEPARATORS**: Add |----| separator row after headers
- **ALIGNMENT**: Keep numerical values properly aligned
- **COMPLETENESS**: Include ALL rows and columns from the image

EXAMPLE TABLE STRUCTURE:
| Lp | Nazwa towaru/usługi | Ilość | Cena netto | Wartość netto | % VAT | Wartość VAT | Wartość brutto |
|----|---------------------|-------|------------|---------------|-------|-------------|----------------|
| 1  | Service description | 1     | 50,00      | 50,00         | 23    | 11,50       | 61,50          |

DOCUMENT STRUCTURE:
- ## for main sections (Sprzedawca, Nabywca, Faktury details)
- **Bold** for field labels (Data wystawienia:, NIP:, etc.)
- Plain text for addresses and contact information
- Preserve exact formatting for numbers, dates, and references

STRICT EXCLUSIONS:
- NO page numbers (Page 1, Page 2, etc.)
- NO metadata (generated by, source file, etc.)
- NO processing timestamps
- NO explanatory text about the conversion

QUALITY CHECKLIST:
✓ All table data included with proper | separators
✓ Headers use ## markdown syntax
✓ Field labels are **bold**
✓ Numbers and dates exactly as in source
✓ No page numbers or metadata included
✓ No explanatory text or meta-commentary

OUTPUT: Clean Markdown content only. No ```markdown blocks, no explanations, no metadata."""

        return prompt
    
    def _clean_markdown_response(self, response):
        """Clean and validate Markdown response"""
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
    
    def _detect_tables(self, markdown_content):
        """Detect if markdown contains tables"""
        return "|" in markdown_content and "---" in markdown_content