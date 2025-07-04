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
            
            # Step 3: Aggregate entries from all pages
            all_entries = []
            for result in results:
                if result.status == "success" and result.result:
                    entries = result.result.get("entries", [])
                    all_entries.extend(entries)
            
            # Step 4: Store results in candidate
            if all_entries:
                candidate['toc_entries'] = all_entries
                candidate['toc_entries_count'] = len(all_entries)
                print(f"📋 PDFLLMProcessor extracted {len(all_entries)} entries")
                return True
            else:
                print(f"⚠️ PDFLLMProcessor found no entries")
                return False
                
        finally:
            # Cleanup temp file
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
    
    def _create_temp_toc_pdf(self, candidate: Dict) -> str:
        """Create temporary PDF with TOC section cropped from coordinates"""
        source_doc = fitz.open(self.pdf_path)
        
        # Get coordinates
        start_page = candidate['start_page']
        end_page = candidate['end_page']
        start_y = candidate['start_y']
        end_y = candidate['end_y']
        
        # Create new temporary PDF
        toc_doc = fitz.open()
        
        try:
            for page_num in range(start_page, end_page + 1):
                source_page = source_doc[page_num]
                page_rect = source_page.rect
                
                # Determine crop coordinates for this page
                if page_num == start_page and page_num == end_page:
                    # Single page TOC
                    crop_rect = fitz.Rect(0, start_y, page_rect.width, end_y)
                elif page_num == start_page:
                    # First page - crop from start_y to bottom
                    crop_rect = fitz.Rect(0, start_y, page_rect.width, page_rect.height)
                elif page_num == end_page:
                    # Last page - crop from top to end_y
                    crop_rect = fitz.Rect(0, 0, page_rect.width, end_y)
                else:
                    # Middle page - full page
                    crop_rect = page_rect
                
                # Create new page in TOC document
                new_page = toc_doc.new_page(width=page_rect.width, height=crop_rect.height)
                
                # Copy content from cropped area
                new_page.show_pdf_page(new_page.rect, source_doc, page_num, clip=crop_rect)
            
            # Save to temporary file
            temp_dir = Path(tempfile.gettempdir())
            candidate_id = candidate.get('candidate_id', f"toc_{start_page}_{int(start_y)}")
            temp_filename = f"toc_verification_{candidate_id}.pdf"
            temp_pdf_path = str(temp_dir / temp_filename)
            
            toc_doc.save(temp_pdf_path)
            print(f"📄 Created temp TOC PDF: {temp_filename}")
            
            return temp_pdf_path
            
        finally:
            source_doc.close()
            toc_doc.close()