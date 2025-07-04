from llm.json_utils import parse_json_with_markdown_blocks
import luigi
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from luigi_toc_pipeline.config import load_config
from llm.models import get_model_output_limit
from .toc_extractor import TOCExtractor
from luigi_components.pdf_llm_processor import PDFLLMProcessor

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
                result = {"toc_parsed": False, "reason": f"parsing_error: {str(e)}"}
        
        with self.output().open('w') as f:
            json.dump(result, f)

    def _parse_toc_with_vision(self, toc_pdf_path):
        config = load_config()
        yaml_section = config.get_all_task_settings("TOCLLMParser")
        
        processor = PDFLLMProcessor(yaml_section)
        results = processor.process_pdf(toc_pdf_path, parse_json_with_markdown_blocks)
        
        all_entries = []
        for result in results:
            if result.status == "success" and result.result:
                entries = result.result.get("entries", [])
                all_entries.extend(entries)
    
        return {"entries": all_entries}