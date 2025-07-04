import fitz
import base64
from typing import List, Dict, Any
from pathlib import Path

from llm import LLMClient, LLMConfig
from llm.models import get_model_output_limit
from llm.json_utils import parse_json_with_markdown_blocks


class TOCVerificationEngine:
    """Stage 2: LLM verification for uncertain TOC candidates"""
    
    def __init__(self, pdf_path: str, config):
        self.pdf_path = pdf_path
        self.config = config
        
        # Separate model for verification (can be different from detection)
        self.model = config.get_task_setting("TOCDetector", "verification_llm_model", 
                                            config.get_task_setting("TOCDetector", "llm_model", "gpt-4.1-nano"))
        self.temperature = config.get_task_setting("TOCDetector", "llm_temperature", 0.0)
        self.max_tokens = config.get_task_setting("TOCDetector", "llm_max_tokens") or get_model_output_limit(self.model)
        
        self.llm_client = LLMClient(self.model)
        self.llm_config = LLMConfig(
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
    
    def verify_uncertain_tocs(self, uncertain_candidates: List[Dict]) -> List[Dict]:
        """Verify uncertain TOC candidates using LLM vision + OCR"""
        if not uncertain_candidates:
            return []
        
        # SAFETY: Limit max candidates to prevent excessive LLM calls
        MAX_CANDIDATES_TO_VERIFY = 25
        
        if len(uncertain_candidates) > MAX_CANDIDATES_TO_VERIFY:
            print(f"🚨 Too many uncertain TOCs to verify: {len(uncertain_candidates)} > {MAX_CANDIDATES_TO_VERIFY}")
            print(f"🚨 This could indicate poor pattern detection or unusual document structure")
            print(f"🚨 Aborting verification to prevent excessive LLM costs")
            return []
        
        print(f"🤖 LLM verifying {len(uncertain_candidates)} uncertain TOCs...")
        
        verified_tocs = []
        rejected_count = 0
        doc = fitz.open(self.pdf_path)
        
        for candidate in uncertain_candidates:
            try:
                is_valid_toc = self._verify_single_candidate(doc, candidate)
                
                if is_valid_toc:
                    candidate['confidence'] = 'llm_verified'
                    candidate['method'] = 'llm_verification'
                    verified_tocs.append(candidate)
                    print(f"   ✅ Verified TOC at page {candidate['start_page']}")
                else:
                    rejected_count += 1
                    print(f"   ❌ Rejected TOC at page {candidate['start_page']}")
                    
                    # SAFETY: Too many rejections = probably bad pattern detection
                    if rejected_count >= 4:
                        print(f"🚨 LLM rejected {rejected_count} candidates - pattern detection likely failing")
                        print(f"🚨 Aborting verification to prevent further waste of LLM calls")
                        doc.close()
                        return []  # Return empty = signal failure to caller
                    
            except Exception as e:
                print(f"   ⚠️ LLM verification failed for page {candidate['start_page']}: {e}")
                continue
        
        doc.close()
        print(f"🎯 LLM verified {len(verified_tocs)}/{len(uncertain_candidates)} uncertain TOCs")
        
        return verified_tocs
    
    def _verify_single_candidate(self, doc: fitz.Document, candidate: Dict) -> bool:
        """Verify single TOC candidate using LLM"""
        start_page = candidate['start_page']
        end_page = candidate['end_page']
        start_y = candidate['start_y']
        end_y = candidate['end_y']
        
    def _verify_single_candidate(self, doc: fitz.Document, candidate: Dict) -> bool:
        """Verify single TOC candidate using LLM"""
        start_page = candidate['start_page']
        end_page = candidate['end_page']
        start_y = candidate['start_y']
        end_y = candidate['end_y']
        
        # Extract TOC section as text + image
        toc_text = self._extract_toc_text(doc, candidate)
        toc_image = self._create_toc_screenshot(doc, candidate)
        
        # Build LLM prompt from YAML
        prompt_template = self.config.get_task_setting("TOCDetector", "verification_prompt", "")
        prompt = prompt_template.replace("{text}", toc_text)
        
        # Call LLM with vision
        response = self.llm_client.chat(prompt, self.llm_config, images=[toc_image])
        
        # Parse response
        result = parse_json_with_markdown_blocks(response)
        
        if result and isinstance(result, dict):
            return result.get('is_toc', False)
        
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
            
            # Determine crop area for this page
            if page_num == start_page and page_num == end_page:
                # Single page TOC
                crop_rect = fitz.Rect(0, start_y, page_rect.width, end_y)
            elif page_num == start_page:
                # First page - from start_y to bottom
                crop_rect = fitz.Rect(0, start_y, page_rect.width, page_rect.height)
            elif page_num == end_page:
                # Last page - from top to end_y
                crop_rect = fitz.Rect(0, 0, page_rect.width, end_y)
            else:
                # Middle page - full page
                crop_rect = page_rect
            
            # Extract text from crop area
            page_text = page.get_text(clip=crop_rect).strip()
            if page_text:
                text_parts.append(page_text)
        
        return "\n\n".join(text_parts)
    
    def _create_toc_screenshot(self, doc: fitz.Document, candidate: Dict) -> str:
        """Create base64 screenshot of TOC section"""
        start_page = candidate['start_page']
        start_y = candidate['start_y']
        end_y = candidate.get('end_y', start_y + 600)  # Fallback height
        
        # For simplicity, screenshot just the start page
        page = doc[start_page]
        page_rect = page.rect
        
        # Crop area around TOC
        crop_height = min(600, end_y - start_y + 100)  # Max 600px height
        crop_rect = fitz.Rect(0, start_y, page_rect.width, start_y + crop_height)
        
        # Create screenshot with good resolution
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=crop_rect)
        
        # Convert to base64
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode('utf-8')