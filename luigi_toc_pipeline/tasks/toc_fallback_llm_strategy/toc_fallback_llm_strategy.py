import luigi
import json
import fitz
import re
from pathlib import Path

from luigi_components.structured_task import StructuredTask
from luigi_toc_pipeline.tasks.toc_heuristic_detector.toc_heuristic_detector import TOCHeuristicDetector
from llm import LLMClient, LLMConfig
from llm.models import get_model_output_limit
from llm.json_utils import parse_json_with_markdown_blocks


class TOCFallbackLLMStrategy(StructuredTask):
    """
    Fallback orchestrator: use heuristic detection, if fails -> semantic LLM check
    """
    file_path = luigi.Parameter()

    @property
    def pipeline_name(self) -> str:
        return "toc_processing"
    
    @property
    def task_name(self) -> str:
        return "toc_fallback_llm_strategy"

    def requires(self):
        return TOCHeuristicDetector(file_path=self.file_path)

    def run(self):
        from luigi_toc_pipeline.config import load_config
        config = load_config()
        
        # Read heuristic detector result
        with self.input().open('r') as f:
            heuristic_result = json.load(f)
        
        if heuristic_result.get("status") == "success" and heuristic_result.get("toc_found", False):
            # TOC found - pass through coordinates
            result = heuristic_result
            result["method"] = "heuristic_detection"
            print("✅ Heuristic TOC detection succeeded - using coordinates")
            
        else:
            # TOC failed - try semantic approach
            print("🔄 Heuristic TOC failed - falling back to semantic LLM check")
            print(f"🔄 Failure reason: {heuristic_result.get('reason', 'unknown')}")
            
            semantic_result = self._semantic_toc_detection(config)
            
            if semantic_result.get("toc_found", False):
                # Convert semantic mapping to coordinates format
                result = self._convert_semantic_to_coordinates(semantic_result)
                result["method"] = "semantic_llm_fallback"
                print("✅ Semantic LLM fallback found TOC")
            else:
                result = {
                    "toc_found": False,
                    "status": "failed", 
                    "reason": "both_methods_failed",
                    "heuristic_failure": heuristic_result,
                    "semantic_failure": semantic_result
                }
                print("❌ Both heuristic and semantic methods failed")
        
        # Save result in TOCHeuristicDetector format for TOCExtractor
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def _semantic_toc_detection(self, config) -> dict:
        """Semantic LLM-based TOC detection - headers only approach"""
        doc = fitz.open(self.file_path)
        
        # Extract tylko NAGŁÓWKI z pierwszych 50 stron
        print("📖 Extracting headers from first 50 pages...")
        headers_text = ""
        max_pages_for_semantic = 50
        page_count = min(max_pages_for_semantic, len(doc))
        
        for page_num in range(page_count):
            page = doc[page_num]
            page_headers = self._extract_headers_from_page(page, page_num + 1)
            if page_headers:
                headers_text += page_headers + "\n"
        
        doc.close()
        
        print(f"📊 Headers extracted: {len(headers_text):,} characters from {page_count} pages")
        
        # LLM config from YAML
        model = config.get_task_setting("TOCFallbackLLMStrategy", "model", "claude-3-5-haiku")
        temperature = config.get_task_setting("TOCFallbackLLMStrategy", "temperature", 0.0)
        max_tokens = get_model_output_limit(model)  # from llm/models
        
        llm_client = LLMClient(model)
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        print(f"🧠 Running semantic TOC analysis (model: {model})")
        
        try:
            # Get prompt template and insert headers
            prompt_template = config.get_task_setting("TOCFallbackLLMStrategy", "semantic_prompt", "")
            prompt = prompt_template.replace("{text}", headers_text)
            
            # Call LLM
            response = llm_client.chat(prompt, llm_config)
            
            # Parse JSON response
            toc_mapping = parse_json_with_markdown_blocks(response)
            
            if toc_mapping and isinstance(toc_mapping, dict) and len(toc_mapping) > 0:
                # Validation - sprawdź czy nie za dużo sekcji
                if len(toc_mapping) > 30:
                    print(f"⚠️ LLM returned too many sections ({len(toc_mapping)}), likely analyzed whole document")
                    return {
                        "status": "failed",
                        "toc_found": False,
                        "error": "llm_returned_too_many_sections",
                        "sections_count": len(toc_mapping)
                    }
                
                print(f"✅ LLM found {len(toc_mapping)} TOC sections")
                
                # Validate that start_text fragments exist in document
                validated_sections = self._validate_toc_mapping(headers_text, toc_mapping)
                
                return {
                    "status": "success",
                    "toc_found": True,
                    "toc_mapping": validated_sections,
                    "sections_count": len(validated_sections),
                    "method": "semantic_llm_headers_only",
                    "model_used": model
                }
            else:
                print("❌ LLM returned empty or invalid TOC mapping")
                return {
                    "status": "failed",
                    "toc_found": False,
                    "error": "llm_returned_empty_mapping",
                    "method": "semantic_llm_headers_only"
                }
                
        except Exception as e:
            print(f"❌ Semantic LLM analysis failed: {e}")
            return {
                "status": "failed",
                "toc_found": False,
                "error": str(e),
                "method": "semantic_llm_headers_only"
            }

    def _extract_headers_from_page(self, page, page_num: int) -> str:
        """Extract potential headers from page using font size and formatting"""
        text_dict = page.get_text("dict")
        headers = []
        
        # Analyze font sizes to find headers
        font_sizes = []
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    font_sizes.append(span.get("size", 12))
        
        if not font_sizes:
            return ""
        
        # Headers are usually larger fonts (top 20% of sizes)
        avg_font_size = sum(font_sizes) / len(font_sizes)
        header_threshold = avg_font_size * 1.2  # 20% bigger than average
        
        # Extract lines with larger fonts
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = ""
                max_font_size = 0
                
                for span in line["spans"]:
                    line_text += span["text"]
                    max_font_size = max(max_font_size, span.get("size", 12))
                
                line_text = line_text.strip()
                
                # Check if this looks like a header
                if (max_font_size >= header_threshold and 
                    len(line_text) > 3 and 
                    self._looks_like_header(line_text)):
                    headers.append(line_text)
        
        return "\n".join(headers)

    def _looks_like_header(self, text: str) -> bool:
        """Check if text looks like a header/title"""
        text = text.strip()
        
        # Skip page numbers, footers, etc.
        if text.isdigit() or len(text) < 4:
            return False
        
        # Headers often start with capital letter or number
        if text[0].isupper() or text[0].isdigit():
            return True
        
        # Known header patterns
        header_patterns = [
            r'^(chapter|rozdział|section|część|art\.|§)',
            r'^\d+\.', 
            r'^[IVX]+\.',
        ]
        
        return any(re.match(p, text, re.IGNORECASE) for p in header_patterns)

    def _validate_toc_mapping(self, headers_text: str, toc_mapping: dict) -> dict:
        """Validate that start_text fragments actually exist in headers"""
        validated = {}
        
        for title, start_text in toc_mapping.items():
            if isinstance(start_text, str) and len(start_text.strip()) > 0:
                # Check if start_text exists in headers
                if start_text.strip() in headers_text:
                    validated[title] = start_text.strip()
                    print(f"   ✅ Validated section: {title}")
                else:
                    # Try partial match for robustness
                    start_words = start_text.strip().split()[:5]  # First 5 words
                    partial_text = " ".join(start_words)
                    
                    if partial_text in headers_text:
                        validated[title] = partial_text
                        print(f"   ⚠️ Partial match for section: {title}")
                    else:
                        print(f"   ❌ Invalid start_text for section: {title}")
        
        print(f"📋 Validated {len(validated)}/{len(toc_mapping)} sections")
        return validated

    def _convert_semantic_to_coordinates(self, semantic_result: dict) -> dict:
        """Convert semantic LLM mapping to coordinates format for TOCExtractor"""
        toc_mapping = semantic_result.get("toc_mapping", {})
        
        if not toc_mapping:
            return {"toc_found": False, "reason": "empty_semantic_mapping"}
        
        doc = fitz.open(self.file_path)
        
        # Find first and last TOC entries in PDF to determine coordinates
        first_match = None
        last_match = None
        
        for title, start_text in toc_mapping.items():
            match_info = self._find_text_coordinates_in_pdf(doc, start_text)
            
            if match_info:
                if first_match is None or match_info["page"] < first_match["page"]:
                    first_match = match_info
                    first_match["title"] = title
                
                if last_match is None or match_info["page"] > last_match["page"] or \
                   (match_info["page"] == last_match["page"] and match_info["y"] > last_match["y"]):
                    last_match = match_info
                    last_match["title"] = title
        
        doc.close()
        
        if not first_match or not last_match:
            print("❌ Could not find semantic TOC entries in PDF")
            return {"toc_found": False, "reason": "semantic_entries_not_found_in_pdf"}
        
        # Calculate TOC bounds
        start_page = first_match["page"]
        start_y = max(0, first_match["y"] - 50)  # Little padding above first entry
        end_page = last_match["page"] 
        end_y = last_match["y"] + 100  # Little padding below last entry
        
        print(f"📍 Semantic TOC coordinates: page {start_page}-{end_page}, y {start_y}-{end_y}")
        print(f"   First entry: '{first_match['title']}' at page {start_page}")
        print(f"   Last entry: '{last_match['title']}' at page {end_page}")
        
        return {
            "toc_found": True,
            "status": "success",
            "start_page": start_page,
            "start_y": start_y,
            "end_page": end_page,
            "end_y": end_y,
            "semantic_mapping": toc_mapping,
            "first_entry": first_match["title"],
            "last_entry": last_match["title"]
        }

    def _find_text_coordinates_in_pdf(self, doc: fitz.Document, search_text: str) -> dict:
        """Find coordinates of text fragment in PDF"""
        search_text = search_text.strip()
        
        # Try exact match first
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            if search_text in page_text:
                # Get detailed text with coordinates
                text_dict = page.get_text("dict")
                match_y = self._find_text_y_coordinate(text_dict, search_text)
                
                if match_y is not None:
                    return {
                        "page": page_num,
                        "y": match_y,
                        "matched_text": search_text
                    }
        
        # Try partial match (first 50 characters)
        if len(search_text) > 50:
            partial_text = search_text[:50]
            return self._find_text_coordinates_in_pdf(doc, partial_text)
        
        # Try word-by-word match (first 5 words)
        words = search_text.split()
        if len(words) > 5:
            partial_words = " ".join(words[:5])
            return self._find_text_coordinates_in_pdf(doc, partial_words)
        
        return None

    def _find_text_y_coordinate(self, text_dict: dict, search_text: str) -> float:
        """Find Y coordinate of text in page text_dict"""
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                
                if search_text in line_text:
                    return line["bbox"][1]  # Top Y coordinate
        
        return None