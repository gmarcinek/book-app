import luigi
import json
import fitz
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from luigi_toc_pipeline.tasks.toc_orchestrator import TOCOrchestrator
from .toc_validator import TOCValidator
from .pdf_utils import PDFUtils


class DocumentSplitter(StructuredTask):
    """Split document into individual entity chunks with precise coordinates"""
    
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "doc_splitting"
    
    @property
    def task_name(self) -> str:
        return "document_splitter"
    

    def requires(self):
        """Conditional dependency with TOC validation"""
        doc = fitz.open(self.file_path)
        builtin_toc = doc.get_toc()
        doc_pages = len(doc)
        doc.close()
        
        if builtin_toc and TOCValidator.is_valid_toc(builtin_toc, doc_pages, self.file_path):
            print("✅ Valid built-in TOC found - using built-in")
            return None
        else:
            print("📖 Using detection pipeline")
            return TOCOrchestrator(file_path=self.file_path)
    
    def run(self):
        """Split using precise coordinate cutting"""
        doc = fitz.open(self.file_path)
        builtin_toc = doc.get_toc()
        doc_pages = len(doc)
        doc.close()
        
        # Determine TOC source
        if builtin_toc and TOCValidator.is_valid_toc(builtin_toc, doc_pages, self.file_path):
            result = self._split_by_builtin_toc_precise(builtin_toc)
        else:
            with self.input().open('r') as f:
                toc_data = json.load(f)
            result = self._handle_detected_toc_precise(toc_data)
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
    def _split_by_builtin_toc_precise(self, builtin_toc):
        """Split using built-in TOC with precise coordinates"""
        doc = fitz.open(self.file_path)
        base_output_dir = PDFUtils.get_base_output_dir()
        doc_name = PDFUtils.get_doc_name(self.file_path)
        
        try:
            # Use precise coordinate splitting
            all_sections = PDFUtils.split_by_individual_entities(
                builtin_toc, doc, base_output_dir, doc_name, "builtin"
            )
            
        finally:
            doc.close()
        
        # Count precision stats
        precise_sections = len([s for s in all_sections if s.get("precision") == "coordinate_based"])
        page_sections = len([s for s in all_sections if s.get("precision") == "page_based"])
        
        # Level stats
        level_1_count = len([s for s in all_sections if s["level"] == 1])
        level_2_count = len([s for s in all_sections if s["level"] == 2])
        
        result = {
            "status": "success",
            "method": "builtin_toc_precise_cutting",
            "total_entities_created": len(all_sections),
            "precision_stats": {
                "coordinate_based": precise_sections,
                "page_based": page_sections,
                "precision_rate": precise_sections / len(all_sections) if all_sections else 0
            },
            "level_stats": {
                "level_1_entities": level_1_count,
                "level_2_entities": level_2_count
            },
            "sections": all_sections,
            "output_base_directory": str(base_output_dir)
        }
        
        print(f"✅ Precise cutting complete: {len(all_sections)} entities")
        print(f"   Coordinate-based: {precise_sections}/{len(all_sections)}")
        print(f"   Level 1: {level_1_count}, Level 2: {level_2_count}")
        
        return result
    
    def _handle_detected_toc_precise(self, toc_data):
        """Handle detected TOC with precise coordinates"""
        if not toc_data.get("toc_found", False):
            return {
                "status": "no_toc",
                "reason": toc_data.get("reason", "TOC not found"),
                "entities_created": 0
            }
        
        return self._split_by_detected_toc_precise(toc_data)
    
    def _split_by_detected_toc_precise(self, toc_data):
        """Split using detected TOC with precise coordinates"""
        toc_entries = toc_data.get("toc_entries", [])
        if not toc_entries:
            return {
                "status": "success",
                "method": "detected_toc_precise_cutting", 
                "total_entities_created": 0,
                "precision_stats": {"coordinate_based": 0, "page_based": 0},
                "sections": []
            }
        
        doc = fitz.open(self.file_path)
        base_output_dir = PDFUtils.get_base_output_dir()
        doc_name = PDFUtils.get_doc_name(self.file_path)
        
        try:
            # Use precise coordinate splitting
            all_sections = PDFUtils.split_by_individual_entities(
                toc_entries, doc, base_output_dir, doc_name, "detected"
            )
            
        finally:
            doc.close()
        
        # Precision and level stats
        precise_sections = len([s for s in all_sections if s.get("precision") == "coordinate_based"])
        page_sections = len([s for s in all_sections if s.get("precision") == "page_based"])
        level_1_count = len([s for s in all_sections if s["level"] == 1])
        level_2_count = len([s for s in all_sections if s["level"] == 2])
        
        result = {
            "status": "success",
            "method": "detected_toc_precise_cutting", 
            "total_entities_created": len(all_sections),
            "precision_stats": {
                "coordinate_based": precise_sections,
                "page_based": page_sections,
                "precision_rate": precise_sections / len(all_sections) if all_sections else 0
            },
            "level_stats": {
                "level_1_entities": level_1_count,
                "level_2_entities": level_2_count
            },
            "sections": all_sections,
            "output_base_directory": str(base_output_dir)
        }
        
        print(f"✅ Precise cutting complete: {len(all_sections)} entities")
        print(f"   Coordinate-based: {precise_sections}/{len(all_sections)}")
        
        return result