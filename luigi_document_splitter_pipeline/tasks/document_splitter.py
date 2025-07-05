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
    """Split document into individual entity chunks based on TOC entries"""
    
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "doc_splitting"
    
    @property
    def task_name(self) -> str:
        return "document_splitter"
    

    def requires(self):
        """Conditional dependency with comprehensive TOC validation"""
        doc = fitz.open(self.file_path)
        builtin_toc = doc.get_toc()
        doc_pages = len(doc)
        doc.close()
        
        if builtin_toc:
            print(f"📚 Built-in TOC found ({len(builtin_toc)} entries)")
            print(f"   Document pages: {doc_pages}")
            
            if TOCValidator.is_valid_toc(builtin_toc, doc_pages, self.file_path):
                print("✅ TOC appears valid - using built-in")
                return None
            else:
                print("⚠️ TOC has quality issues - using detection")
                return TOCOrchestrator(file_path=self.file_path)
        else:
            print("📖 No built-in TOC - running detection pipeline")
            return TOCOrchestrator(file_path=self.file_path)
    
    def run(self):
        """Split using individual entity chunking"""
        doc = fitz.open(self.file_path)
        builtin_toc = doc.get_toc()
        doc_pages = len(doc)
        doc.close()
        
        # Check if we have input (detected TOC) or should use built-in
        if builtin_toc and TOCValidator.is_valid_toc(builtin_toc, doc_pages, self.file_path):
            # Use built-in TOC - no input dependency
            result = self._split_by_builtin_toc_individual(builtin_toc)
        else:
            # Use detected TOC - has input dependency
            with self.input().open('r') as f:
                toc_data = json.load(f)
            result = self._handle_detected_toc_individual(toc_data)
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
    def _split_by_builtin_toc_individual(self, builtin_toc):
        """Split document using built-in TOC with individual entity chunking"""
        doc = fitz.open(self.file_path)
        base_output_dir = PDFUtils.get_base_output_dir()
        doc_name = PDFUtils.get_doc_name(self.file_path)
        
        try:
            # NEW: Individual entity chunking for ALL entries
            all_sections = PDFUtils.split_by_individual_entities(
                builtin_toc, doc, base_output_dir, doc_name, "builtin"
            )
            
        finally:
            doc.close()
        
        # Count by level for stats
        level_1_count = len([s for s in all_sections if s["level"] == 1])
        level_2_count = len([s for s in all_sections if s["level"] == 2])
        other_levels_count = len(all_sections) - level_1_count - level_2_count
        
        result = {
            "status": "success",
            "method": "builtin_toc_individual_entities",
            "total_entities_created": len(all_sections),
            "level_1_entities": level_1_count,
            "level_2_entities": level_2_count,
            "other_levels_entities": other_levels_count,
            "sections": all_sections,
            "output_base_directory": str(base_output_dir),
            "chunking_strategy": "individual_entity"
        }
        
        print(f"✅ Individual entity chunking complete: {len(all_sections)} total entities")
        print(f"   Level 1: {level_1_count} entities")
        print(f"   Level 2: {level_2_count} entities")
        if other_levels_count > 0:
            print(f"   Other levels: {other_levels_count} entities")
        
        return result
    
    def _handle_detected_toc_individual(self, toc_data):
        """Handle detected TOC results with individual entity chunking"""
        if not toc_data.get("toc_found", False):
            result = {
                "status": "no_toc",
                "reason": toc_data.get("reason", "TOC not found"),
                "entities_created": 0,
                "chunking_strategy": "none"
            }
            print("❌ Cannot split document - no TOC found")
            return result
        else:
            return self._split_by_detected_toc_individual(toc_data)
    
    def _split_by_detected_toc_individual(self, toc_data):
        """Split document using detected TOC with individual entity chunking"""
        toc_entries = toc_data.get("toc_entries", [])
        if not toc_entries:
            return {
                "status": "success",
                "method": "detected_toc_individual_entities", 
                "total_entities_created": 0,
                "sections": [],
                "output_directory": "none",
                "chunking_strategy": "individual_entity"
            }
        
        doc = fitz.open(self.file_path)
        base_output_dir = PDFUtils.get_base_output_dir()
        doc_name = PDFUtils.get_doc_name(self.file_path)
        
        try:
            # NEW: Individual entity chunking for ALL detected entries
            all_sections = PDFUtils.split_by_individual_entities(
                toc_entries, doc, base_output_dir, doc_name, "detected"
            )
            
        finally:
            doc.close()
        
        # Count by level for stats
        level_1_count = len([s for s in all_sections if s["level"] == 1])
        level_2_count = len([s for s in all_sections if s["level"] == 2])
        other_levels_count = len(all_sections) - level_1_count - level_2_count
        
        result = {
            "status": "success",
            "method": "detected_toc_individual_entities", 
            "total_entities_created": len(all_sections),
            "level_1_entities": level_1_count,
            "level_2_entities": level_2_count,
            "other_levels_entities": other_levels_count,
            "sections": all_sections,
            "output_base_directory": str(base_output_dir),
            "chunking_strategy": "individual_entity"
        }
        
        print(f"✅ Individual entity chunking complete: {len(all_sections)} total entities")
        print(f"   Level 1: {level_1_count} entities")
        print(f"   Level 2: {level_2_count} entities")
        if other_levels_count > 0:
            print(f"   Other levels: {other_levels_count} entities")
        
        return result