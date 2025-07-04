from llm.utils import parse_json_with_markdown_blocks
import luigi
import json
import fitz
import base64
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from luigi_pipeline.tasks.base.structured_task import StructuredTask
from luigi_toc_pipeline.config import load_config
from llm import LLMClient, LLMConfig
from llm.models import get_model_output_limit
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
        with self.input().open('r') as f:
            extractor_data = json.load(f)
        
        if not extractor_data.get("toc_extracted", False):
            result = {"toc_parsed": False, "reason": "no_toc_extracted"}
        else:
            try:
                toc_structure = self._parse_toc_with_vision(extractor_data["toc_pdf_path"])
                result = {
                    "toc_parsed": True,
                    "toc_structure": toc_structure,
                    "source_toc_pdf": extractor_data["toc_pdf_path"]
                }
            except Exception as e:
                print(f"❌ TOC parsing failed: {e}")
                result = {"toc_parsed": False, "reason": f"parsing_error: {str(e)}"}
        
        with self.output().open('w') as f:
            json.dump(result, f)
    
    def _parse_toc_with_vision(self, toc_pdf_path):
        config = load_config()
        model = config.get_task_setting("TOCLLMParser", "model", "claude-4-sonnet")
        temperature = config.get_task_setting("TOCLLMParser", "temperature", 0.0)
        max_tokens = config.get_task_setting("TOCLLMParser", "max_tokens") or get_model_output_limit(model)
        prompt_template = config.get_task_setting("TOCLLMParser", "vision_prompt", "")
        
        llm_client = LLMClient(model)
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        doc = fitz.open(toc_pdf_path)
        all_entries = []
        
        for page_num in range(len(doc)):
            print(f"📄 Processing TOC page {page_num + 1}/{len(doc)}")
            
            page_entries = self._process_page(doc, page_num, prompt_template, llm_client, llm_config, model, config)
            all_entries.extend(page_entries)
            print(f"   Found {len(page_entries)} entries")
        
        doc.close()
        print(f"✅ Total TOC entries: {len(all_entries)}")
        return {"entries": all_entries}
    
    def _process_page(self, doc, page_num, prompt_template, llm_client, llm_config, model, config):
        """Process single TOC page"""
        page = doc[page_num]
        
        # Extract text
        text = page.get_text().strip() or "[No text extracted]"
        
        # Create JPG screenshot
        page_rect = page.rect
        target_width = config.get_task_setting("TOCLLMParser", "target_width_px", 800)
        zoom = target_width / page_rect.width
        zoom = max(0.5, min(3.0, zoom))
        
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        jpg_quality = config.get_task_setting("TOCLLMParser", "jpg_quality", 85)
        img_bytes = pix.tobytes("jpeg", jpg_quality=jpg_quality)
        image_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        print(f"📸 Page {page_num + 1}: {len(img_bytes):,} bytes JPG")
        
        # Build prompt
        prompt = prompt_template.replace("{text_content}", text)
        if not prompt.strip():
            return []
        
        # Call LLM
        try:
            print(f"🤖 Calling {model}")
            response = llm_client.chat(prompt, llm_config, images=[image_base64])
            print(f"📥 Response: {len(response)} chars")
            
            data = parse_json_with_markdown_blocks(response)
            if not data:
                print("❌ Failed to parse JSON from response")
                return []
            
            entries = data.get("entries", [])
            print(f"🎯 Parsed {len(entries)} entries")
            
            for i, entry in enumerate(entries):
                title = entry.get("title", "Unknown")
                page_ref = entry.get("page", "?")
                print(f"   {i+1}. {title} → page {page_ref}")
            
            return entries
            
        except Exception as e:
            print(f"❌ LLM failed: {e}")
            return []