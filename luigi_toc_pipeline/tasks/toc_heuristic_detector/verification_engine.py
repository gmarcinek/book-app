import fitz
import tempfile
import os
from pathlib import Path
from typing import List, Dict
from llm.json_utils import parse_json_with_markdown_blocks
from luigi_components.pdf_llm_processor import PDFLLMProcessor


class TOCVerificationEngine:
    """LLM verification for uncertain TOC candidates using PDFLLMProcessor"""
    
    def __init__(self, pdf_path: str, config):
        self.pdf_path = pdf_path
        self.config = config
        
        # Get PDFLLMProcessor config from YAML
        self.processor_config = config.get_all_task_settings("TOCDetector").get("verification_processor", {})
        
        if not self.processor_config:
            raise RuntimeError("Missing verification_processor config in TOCDetector section")
    
    def process_all_candidates(self, all_candidates: List[Dict]) -> List[Dict]:
        """Process all TOC candidates using PDFLLMProcessor"""
        if not all_candidates:
            return []
        
        if len(all_candidates) > 25:
            print(f"🚨 Too many candidates ({len(all_candidates)} > 25) - aborting processing")
            return []
        
        print(f"🤖 PDFLLMProcessor processing {len(all_candidates)} TOC candidates...")
        
        processed_tocs = []
        rejected_count = 0
        failure_count = 0
        
        for candidate in all_candidates:
            try:
                is_valid = self._verify_single_candidate_with_processor(candidate)
                
                if is_valid:
                    # Reset counters on success
                    rejected_count = 0
                    failure_count = 0
                    candidate['confidence'] = 'llm_processed'
                    candidate['method'] = 'llm_processing'
                    processed_tocs.append(candidate)
                    print(f"   ✅ Processed TOC at page {candidate['start_page']}")
                else:
                    rejected_count += 1
                    print(f"   ❌ Rejected TOC at page {candidate['start_page']}")
                    
                    if rejected_count >= 4:
                        print(f"🚨 Too many rejections ({rejected_count}) - pattern detection likely failing")
                        break
                    
            except Exception as e:
                failure_count += 1
                print(f"   💥 PDFLLMProcessor failure #{failure_count} for page {candidate['start_page']}: {e}")
                
                if failure_count >= 3:
                    print(f"🚨 Too many PDFLLMProcessor failures ({failure_count}) - aborting processing")
                    break
        
        print(f"🎯 Processed {len(processed_tocs)}/{len(all_candidates)} TOCs")
        return processed_tocs

    def verify_uncertain_tocs(self, uncertain_candidates: List[Dict]) -> List[Dict]:
        """Legacy method - calls process_all_candidates"""
        return self.process_all_candidates(uncertain_candidates)
    
    def _verify_single_candidate_with_processor(self, candidate: Dict) -> bool:
        """Verify single TOC candidate using PDFLLMProcessor"""
        
        # Step 1: Create temporary TOC PDF from coordinates
        temp_pdf_path = self._create_temp_toc_pdf(candidate)
        
        try:
            # Step 2: Use PDFLLMProcessor to process the temp PDF
            processor = PDFLLMProcessor(self.processor_config, "TOCVerification")
            results = processor.process_pdf(temp_pdf_path, parse_json_with_markdown_blocks)
            
            # Step 3: Aggregate entries from all pages AND FILTER NULL LEVELS
            all_entries = []
            discarded_count = 0
            
            for result in results:
                if result.status == "success" and result.result:
                    raw_entries = result.result.get("entries", [])
                    
                    for entry in raw_entries:
                        if entry.get('level') is None:
                            discarded_count += 1
                            print(f"⚠️ Discarding entry '{entry.get('title', 'unknown')}' - no level detected")
                        else:
                            all_entries.append(entry)
            
            print(f"📋 Entry filtering: {len(all_entries)} valid, {discarded_count} discarded (NULL level)")
            
            # Step 4: Store ONLY valid entries in candidate
            if all_entries:
                candidate['toc_entries'] = all_entries
                candidate['toc_entries_count'] = len(all_entries)
                print(f"📋 PDFLLMProcessor extracted {len(all_entries)} valid entries")
                return True
            else:
                print(f"⚠️ No valid entries after filtering")
                return False
                
        finally:
            # Cleanup temp file
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
    
    def _create_temp_toc_pdf(self, candidate: Dict) -> str:
        """Create debug PDF with better cropping (like debug_utils margins)"""
        source_doc = fitz.open(self.pdf_path)
        
        start_page = candidate['start_page']
        start_y = candidate['start_y']
        candidate_id = candidate.get('candidate_id', f"toc_{start_page}_{int(start_y)}")
        
        toc_doc = fitz.open()
        
        try:
            page = source_doc[start_page]
            page_rect = page.rect
            
            # BETTER CROPPING: Add margins like debug_utils
            crop_top = max(0, start_y - 100)  # 100px above TOC start
            crop_bottom = min(page_rect.height, start_y + 600)  # 600px below (more than debug)
            crop_rect = fitz.Rect(0, crop_top, page_rect.width, crop_bottom)
            
            # Single page with smart margins
            new_page = toc_doc.new_page(width=page_rect.width, height=crop_rect.height)
            new_page.show_pdf_page(new_page.rect, source_doc, start_page, clip=crop_rect)
            
            # Save to debug (not temp)
            doc_name = Path(self.pdf_path).stem
            debug_dir = Path("output") / doc_name / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            debug_filename = f"toc_verification_{candidate_id}.pdf"
            debug_pdf_path = str(debug_dir / debug_filename)
            
            toc_doc.save(debug_pdf_path)
            print(f"📄 Saved verification PDF: {debug_filename}")
            
            return debug_pdf_path
            
        finally:
            source_doc.close()
            toc_doc.close()