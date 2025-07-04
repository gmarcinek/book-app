import luigi
import json
import fitz
import base64
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from luigi_pipeline.tasks.base.structured_task import StructuredTask
from luigi_pipeline.config import load_config
from llm import LLMClient, LLMConfig
from ner.utils import parse_llm_json_response
from .toc_extractor import TOCExtractor

class TOCLLMParser(StructuredTask):
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_llm_parser"
    
    def requires(self):
        return TOCExtractor(file_path=self.file_path)
    
    def run(self):
        # Load TOC extraction result
        with self.input().open('r') as f:
            extractor_data = json.load(f)
        
        if not extractor_data.get("toc_extracted", False):
            result = {"toc_parsed": False, "reason": "no_toc_extracted"}
        else:
            # Parse TOC PDF with vision + text
            toc_structure = self._parse_toc_with_vision(extractor_data["toc_pdf_path"])
            result = {
                "toc_parsed": True,
                "toc_structure": toc_structure,
                "source_toc_pdf": extractor_data["toc_pdf_path"]
            }
        
        with self.output().open('w') as f:
            json.dump(result, f)
    
    def _parse_toc_with_vision(self, toc_pdf_path):
        """Parse TOC PDF using LLM vision + text (based on SlidingWindowPageTask pattern)"""
        config = load_config()
        model = config.get_task_setting("TOCLLMParser", "model", "claude-4-sonnet")
        max_tokens = config.get_max_tokens_for_model(model)
        temperature = config.get_task_setting("TOCLLMParser", "temperature", 0.0)
        
        doc = fitz.open(toc_pdf_path)
        
        # Extract text + images (similar to SlidingWindowPageTask)
        text_content = ""
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Get text
            text = page.get_text()
            text_content += f"\n=== PAGE {page_num + 1} ===\n{text}\n"
            
            # Get image (adaptive zoom like in PDFProcessing)
            page_rect = page.rect
            adaptive_zoom = min(2.0, 1200 / page_rect.width)  # Target 1200px width
            mat = fitz.Matrix(adaptive_zoom, adaptive_zoom)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            image_base64 = base64.b64encode(img_bytes).decode('utf-8')
            images.append(image_base64)
        
        doc.close()
        
        # Build prompt from config
        prompt_template = config.get_task_setting("TOCLLMParser", "vision_prompt", "")
        prompt = prompt_template.format(text_content=text_content)
        
        # Call LLM with vision
        llm_client = LLMClient(model)
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        response = llm_client.chat(prompt, llm_config, images=images)
        
        # Parse JSON response
        result = parse_llm_json_response(response) or {"entries": []}
        
        return result