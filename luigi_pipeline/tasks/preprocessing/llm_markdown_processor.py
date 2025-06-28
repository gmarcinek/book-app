import luigi
import json
import hashlib
import base64
from datetime import datetime

from llm import LLMClient, LLMConfig, Models
from .pdf_processing import PDFProcessing


class LLMMarkdownProcessor(luigi.Task):
    """
    Converts PDF pages to Markdown using LLM Vision models
    
    Processes each page (image + text) and generates clean Markdown,
    with special attention to table structure preservation
    """
    file_path = luigi.Parameter()
    model = luigi.Parameter(default=Models.QWEN_CODER)  # Ollama LLaVA fallback
    
    def requires(self):
        return PDFProcessing(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/llm_markdown_{file_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Load PDF processing results
        with self.input().open('r') as f:
            pdf_data = json.load(f)
        
        if pdf_data.get("task_name") != "PDFProcessing":
            raise ValueError("Expected PDFProcessing input data")
        
        pages = pdf_data.get("pages", [])
        if not pages:
            raise ValueError("No pages found in PDF data")
        
        # Initialize LLM client
        llm_client = LLMClient(self.model)
        config = LLMConfig(temperature=0.0)
        
        # Process each page
        markdown_pages = []
        for page in pages:
            try:
                markdown_content = self._process_page_to_markdown(
                    page, llm_client, config
                )
                
                markdown_pages.append({
                    "page_num": page["page_num"],
                    "markdown": markdown_content,
                    "original_text_length": page["text_length"],
                    "has_tables": "table" in markdown_content.lower() or "|" in markdown_content
                })
                
            except Exception as e:
                # Log error but continue with other pages
                print(f"⚠️ Failed to process page {page['page_num']}: {e}")
                markdown_pages.append({
                    "page_num": page["page_num"],
                    "markdown": f"# Page {page['page_num']}\n\n[Error processing page: {str(e)}]",
                    "original_text_length": page["text_length"],
                    "has_tables": False,
                    "error": str(e)
                })
        
        # Create output
        output_data = {
            "task_name": "LLMMarkdownProcessor",
            "input_file": str(self.file_path),
            "model_used": self.model,
            "status": "success",
            "pages_count": len(markdown_pages),
            "pages_with_tables": sum(1 for p in markdown_pages if p.get("has_tables", False)),
            "pages_with_errors": sum(1 for p in markdown_pages if "error" in p),
            "markdown_pages": markdown_pages,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def _process_page_to_markdown(self, page, llm_client, config):
        """Convert single page (image + text) to Markdown using LLM"""
        
        # Prepare prompt for vision model
        prompt = self._build_markdown_conversion_prompt(page)
        
        # For vision-capable models, we need to handle image data
        # Note: This is a simplified approach - actual implementation 
        # would depend on the specific model's image input format
        
        if self._is_vision_model(self.model):
            # TODO: Implement vision model call with image
            # For now, fallback to text-only processing
            response = llm_client.chat(prompt, config)
        else:
            # Text-only model fallback
            response = llm_client.chat(prompt, config)
        
        # Clean and validate markdown
        markdown = self._clean_markdown_response(response)
        return markdown
    
    def _build_markdown_conversion_prompt(self, page):
        """Build prompt for Markdown conversion with table preservation focus"""
        
        extracted_text = page.get("extracted_text", "")
        page_num = page.get("page_num", 1)
        
        prompt = f"""Convert this PDF page to clean Markdown format.

PAGE {page_num} CONTENT:
{extracted_text}

INSTRUCTIONS:
- Create clean, well-structured Markdown
- Pay special attention to preserving TABLE STRUCTURE
- Use proper Markdown table syntax: | Column 1 | Column 2 |
- If you see tabular data, format it as proper Markdown tables
- Use appropriate headers (# ## ###) for document structure
- Preserve lists, bullet points, and formatting
- Remove page numbers, headers, footers if not content-relevant
- If the page contains mostly tabular data, ensure tables are properly formatted

IMPORTANT: Focus on accuracy and readability. Tables are critical to preserve correctly.

Return ONLY the Markdown content, no explanations or meta-commentary."""

        return prompt
    
    def _is_vision_model(self, model):
        """Check if model supports vision (simplified check)"""
        vision_models = [
            Models.GPT_4O,
            Models.GPT_4O_MINI,
            Models.GPT_4_1_MINI,
            Models.GPT_4_1_NANO,
            # Add Ollama LLaVA models when implemented
        ]
        return model in vision_models
    
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
            return "# Page Content\n\n[No content could be extracted]"
        
        return markdown