import fitz
import base64
from typing import List, Dict
from llm import LLMClient, LLMConfig
from llm.models import get_model_output_limit
from llm.json_utils import parse_json_with_markdown_blocks


class TOCVerificationEngine:
    """LLM verification for uncertain TOC candidates"""
    
    def __init__(self, pdf_path: str, config):
        self.pdf_path = pdf_path
        self.config = config
        
        self.model = config.get_task_setting("TOCDetector", "verification_llm_model", "gpt-4.1-nano")
        self.temperature = config.get_task_setting("TOCDetector", "verification_temperature", 0.0)
        self.max_tokens = get_model_output_limit(self.model)
        
        self.llm_client = LLMClient(self.model)
        self.llm_config = LLMConfig(temperature=self.temperature, max_tokens=self.max_tokens)
    
    def process_all_candidates(self, all_candidates: List[Dict]) -> List[Dict]:
        """Process all TOC candidates (certain + uncertain) using LLM"""
        if not all_candidates:
            return []
        
        if len(all_candidates) > 25:
            print(f"🚨 Too many candidates ({len(all_candidates)} > 25) - aborting processing")
            return []
        
        print(f"🤖 LLM processing {len(all_candidates)} TOC candidates...")
        
        processed_tocs = []
        rejected_count = 0
        failure_count = 0
        doc = fitz.open(self.pdf_path)
        
        for candidate in all_candidates:
            try:
                is_valid = self._verify_single_candidate(doc, candidate)
                
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
                print(f"   💥 LLM failure #{failure_count} for page {candidate['start_page']}: {e}")
                
                if failure_count >= 3:
                    print(f"🚨 Too many LLM failures ({failure_count}) - aborting processing")
                    break
        
        doc.close()
        print(f"🎯 Processed {len(processed_tocs)}/{len(all_candidates)} TOCs")
        return processed_tocs

    def verify_uncertain_tocs(self, uncertain_candidates: List[Dict]) -> List[Dict]:
        """Legacy method - calls process_all_candidates"""
        return self.process_all_candidates(uncertain_candidates)
    
    def _verify_single_candidate(self, doc: fitz.Document, candidate: Dict) -> bool:
        """Verify single TOC candidate using LLM vision"""
        # Extract text and image
        toc_text = self._extract_toc_text(doc, candidate)
        toc_image = self._create_toc_screenshot(doc, candidate)
        
        # Build prompt
        prompt_template = self.config.get_task_setting("TOCDetector", "verification_prompt", "")
        prompt = prompt_template.replace("{text}", toc_text)
        
        # Call LLM
        response = self.llm_client.chat(prompt, self.llm_config, images=[toc_image])
        
        # Parse response
        result = parse_json_with_markdown_blocks(response)
        if result and isinstance(result, dict):
            # Store parsed entries in candidate
            if result.get('toc_entries'):
                candidate['toc_entries'] = result['toc_entries']
                candidate['toc_entries_count'] = len(result['toc_entries'])
            
            return result.get('toc_found', False)
        
        return False
    
    def _extract_toc_text(self, doc: fitz.Document, candidate: Dict) -> str:
        """Extract text from TOC section"""
        start_page = candidate['start_page']
        end_page = candidate['end_page']
        start_y = candidate['start_y']
        end_y = candidate['end_y']
        
        text_parts = []
        
        for page_num in range(start_page, end_page + 1):
            page = doc[page_num]
            page_rect = page.rect
            
            # Determine crop area
            if page_num == start_page and page_num == end_page:
                crop_rect = fitz.Rect(0, start_y, page_rect.width, end_y)
            elif page_num == start_page:
                crop_rect = fitz.Rect(0, start_y, page_rect.width, page_rect.height)
            elif page_num == end_page:
                crop_rect = fitz.Rect(0, 0, page_rect.width, end_y)
            else:
                crop_rect = page_rect
            
            page_text = page.get_text(clip=crop_rect).strip()
            if page_text:
                text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def _create_toc_screenshot(self, doc: fitz.Document, candidate: Dict) -> str:
        """Create base64 screenshot of TOC section"""
        start_page = candidate['start_page']
        start_y = candidate['start_y']
        end_y = candidate.get('end_y', start_y + 600)
        
        page = doc[start_page]
        page_rect = page.rect
        
        crop_height = min(600, end_y - start_y + 100)
        crop_rect = fitz.Rect(0, start_y, page_rect.width, start_y + crop_height)
        
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=crop_rect)
        
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode('utf-8')