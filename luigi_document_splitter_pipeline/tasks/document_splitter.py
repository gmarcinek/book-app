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
from .section_creator import SectionCreator


class DocumentSplitter(StructuredTask):
    """Split document into sections based on TOC entries with smart validation"""
    
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
            
            if TOCValidator.is_valid_toc(builtin_toc, doc_pages, self.file_path):  # ← dodaj file_path
                print("✅ TOC appears valid - using built-in")
                return None
            else:
                print("⚠️ TOC has quality issues - using detection")
                return TOCOrchestrator(file_path=self.file_path)
        else:
            print("📖 No built-in TOC - running detection pipeline")
            return TOCOrchestrator(file_path=self.file_path)
    
    def run(self):
        """Split with smart TOC validation"""
        doc = fitz.open(self.file_path)
        builtin_toc = doc.get_toc()
        doc_pages = len(doc)
        doc.close()
        
        # Check if we have input (detected TOC) or should use built-in
        if builtin_toc and TOCValidator.is_valid_toc(builtin_toc, doc_pages, self.file_path):
            # Use built-in TOC - no input dependency
            result = self._split_by_builtin_toc(builtin_toc)
        else:
            # Use detected TOC - has input dependency
            with self.input().open('r') as f:  # ← ONLY call input() when we have dependency
                toc_data = json.load(f)
            result = self._handle_detected_toc(toc_data)
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    
    def _split_by_builtin_toc(self, builtin_toc):
        """Split document using built-in TOC with level-based folders"""
        doc = fitz.open(self.file_path)
        base_output_dir = PDFUtils.get_base_output_dir()
        doc_name = PDFUtils.get_doc_name(self.file_path)
        
        # Group entries by level
        level_1_entries = [entry for entry in builtin_toc if entry[0] == 1]
        level_2_entries = [entry for entry in builtin_toc if entry[0] == 2]
        
        all_sections = []
        
        try:
            # Split by level 1
            if level_1_entries:
                lvl1_sections = PDFUtils.create_sections_for_level(
                    doc, level_1_entries, 1, base_output_dir, doc_name
                )
                all_sections.extend(lvl1_sections)
            
            # Split by level 2  
            if level_2_entries:
                lvl2_sections = PDFUtils.create_sections_for_level(
                    doc, level_2_entries, 2, base_output_dir, doc_name
                )
                all_sections.extend(lvl2_sections)
            
        finally:
            doc.close()
        
        result = {
            "status": "success",
            "method": "builtin_toc",
            "total_sections_created": len(all_sections),
            "level_1_sections": len([s for s in all_sections if s["level"] == 1]),
            "level_2_sections": len([s for s in all_sections if s["level"] == 2]),
            "sections": all_sections,
            "output_base_directory": str(base_output_dir)
        }
        
        print(f"✅ Split by built-in TOC: {len(all_sections)} total sections")
        print(f"   Level 1: {result['level_1_sections']} sections")
        print(f"   Level 2: {result['level_2_sections']} sections")
        
        return result
    
    def _handle_detected_toc(self, toc_data):
        """Handle detected TOC results"""
        if not toc_data.get("toc_found", False):
            result = {
                "status": "no_toc",
                "reason": toc_data.get("reason", "TOC not found"),
                "sections_created": 0
            }
            print("❌ Cannot split document - no TOC found")
            return result
        else:
            return self._split_by_detected_toc(toc_data)
    
    def _split_by_detected_toc(self, toc_data):
        """Split document using detected TOC with level-based folders"""
        toc_entries = toc_data.get("toc_entries", [])
        if not toc_entries:
            return {
                "status": "success",
                "method": "detected_toc", 
                "total_sections_created": 0,
                "sections": [],
                "output_directory": "none"
            }
        
        doc = fitz.open(self.file_path)
        base_output_dir = PDFUtils.get_base_output_dir()
        doc_name = PDFUtils.get_doc_name(self.file_path)
        
        try:
            # Use unified level-based splitting (same as built-in TOC)
            all_sections = PDFUtils.split_by_levels(
                toc_entries, doc, base_output_dir, doc_name, "detected"
            )
            
        finally:
            doc.close()
        
        result = {
            "status": "success",
            "method": "detected_toc", 
            "total_sections_created": len(all_sections),
            "level_1_sections": len([s for s in all_sections if s["level"] == 1]),
            "level_2_sections": len([s for s in all_sections if s["level"] == 2]),
            "sections": all_sections,
            "output_base_directory": str(base_output_dir)
        }
        
        print(f"✅ Split by detected TOC: {len(all_sections)} total sections")
        print(f"   Level 1: {result['level_1_sections']} sections")
        print(f"   Level 2: {result['level_2_sections']} sections")
        
        return result