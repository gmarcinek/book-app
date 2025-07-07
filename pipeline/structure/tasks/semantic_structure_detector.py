import luigi
import json
import fitz
import re
import statistics
from pathlib import Path
from datetime import datetime
from PIL import Image
from typing import List, Dict, Any
from dataclasses import dataclass
import io
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from luigi_components.structured_task import StructuredTask
from ocr import SuryaClient


@dataclass
class TextLine:
    """Structured text line with layout info"""
    text: str
    bbox: List[float]  # [x1, y1, x2, y2]
    page: int
    font_size: float
    confidence: float
    layout_label: str
    
    @property
    def x_start(self) -> float:
        return self.bbox[0]
    
    @property
    def y_start(self) -> float:
        return self.bbox[1]
    
    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


@dataclass
class Section:
    """Document section"""
    title: str
    start_page: int
    end_page: int
    start_y: float
    end_y: float
    content_lines: List[TextLine]
    section_type: str  # "toc", "lvl1_section", "content"
    page_numbers: List[int]  # Page numbers mentioned in text
    
    @property
    def content_text(self) -> str:
        return "\n".join(line.text for line in self.content_lines)


class SemanticStructureDetector(StructuredTask):
    """
    Detect semantic document structure:
    - TOC sections
    - LVL1 sections (major chapters/articles)
    - Medium-sized content blocks
    """
    
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "structure"
    
    @property
    def task_name(self) -> str:
        return "semantic_structure_detector"
    
    def run(self):
        print("🧠 Starting semantic structure detection...")
        
        config = self._load_config()
        
        # Extract all text lines with layout info
        text_lines = self._extract_text_lines(config)
        
        if not text_lines:
            raise ValueError("No text lines extracted")
        
        print(f"📝 Extracted {len(text_lines)} text lines from {max(line.page for line in text_lines)} pages")
        
        # Analyze document structure
        structure = self._analyze_document_structure(text_lines, config)
        
        # Create sections
        sections = self._create_sections(structure, text_lines, config)
        
        # Output result
        result = {
            "task_name": "SemanticStructureDetector",
            "input_file": str(self.file_path),
            "status": "success",
            "sections": [self._section_to_dict(section) for section in sections],
            "sections_count": len(sections),
            "structure_analysis": structure,
            "config_used": config,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Detected {len(sections)} semantic sections")
        self._print_sections_summary(sections)
    
    def _load_config(self):
        """Load semantic detection config"""
        try:
            import yaml
            config_file = Path(__file__).parent.parent / "config.yaml"
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            return config.get("SemanticStructureDetector", {
                "max_pages": 1000,
                "min_section_pages": 1,
                "header_confidence_threshold": 0.7,
                "toc_detection_enabled": True,
                "extract_page_numbers": True
            })
            
        except Exception as e:
            print(f"⚠️ Config load failed: {e}, using defaults")
            return {
                "max_pages": 1000,
                "min_section_pages": 1, 
                "header_confidence_threshold": 0.7,
                "toc_detection_enabled": True,
                "extract_page_numbers": True
            }
    
    def _extract_text_lines(self, config) -> List[TextLine]:
        """Extract text lines with OCR and layout analysis"""
        doc = fitz.open(self.file_path)
        max_pages = min(len(doc), config.get("max_pages", 1000))
        
        # Convert pages to images (native resolution)
        images = []
        for page_num in range(max_pages):
            page = doc[page_num]
            pix = page.get_pixmap()  # Native resolution
            img_bytes = pix.tobytes("png")
            images.append(Image.open(io.BytesIO(img_bytes)))
        
        doc.close()
        
        # Use Surya OCR + Layout
        surya_client = SuryaClient()
        ocr_results = surya_client.process_pages_with_ocr(images)
        
        # Extract text lines
        text_lines = []
        for page_idx, result in enumerate(ocr_results):
            if 'error' in result:
                print(f"⚠️ OCR error on page {page_idx + 1}: {result['error']}")
                continue
            
            page_lines = self._parse_ocr_result(result, page_idx + 1)
            text_lines.extend(page_lines)
        
        return text_lines
    
    def _parse_ocr_result(self, ocr_result: Dict, page_num: int) -> List[TextLine]:
        """Parse Surya OCR result into TextLine objects"""
        lines = []
        
        ocr_data = ocr_result.get('ocr')
        layout_data = ocr_result.get('layout', [])
        
        if not ocr_data or not hasattr(ocr_data, 'text_lines'):
            return lines
        
        # Create layout lookup
        layout_lookup = {}
        if hasattr(layout_data, 'bboxes'):
            for layout_elem in layout_data.bboxes:
                bbox = getattr(layout_elem, 'bbox', [])
                label = getattr(layout_elem, 'label', 'unknown')
                layout_lookup[tuple(bbox)] = label
        
        # Process text lines
        for text_line in ocr_data.text_lines:
            text = getattr(text_line, 'text', '').strip()
            bbox = getattr(text_line, 'bbox', [0, 0, 0, 0])
            confidence = getattr(text_line, 'confidence', 1.0)
            
            if len(text) < 2:  # Skip very short text
                continue
            
            # Estimate font size from bbox height
            font_size = bbox[3] - bbox[1] if len(bbox) >= 4 else 12
            
            # Find layout label
            layout_label = 'Text'  # Default
            for layout_bbox, label in layout_lookup.items():
                if self._bbox_overlap(bbox, layout_bbox):
                    layout_label = label
                    break
            
            lines.append(TextLine(
                text=text,
                bbox=bbox,
                page=page_num,
                font_size=font_size,
                confidence=confidence,
                layout_label=layout_label
            ))
        
        return lines
    
    def _bbox_overlap(self, bbox1: List[float], bbox2: List[float]) -> bool:
        """Check if two bboxes overlap"""
        if len(bbox1) < 4 or len(bbox2) < 4:
            return False
        
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2
        
        return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)
    
    def _analyze_document_structure(self, text_lines: List[TextLine], config) -> Dict[str, Any]:
        """Analyze document structure patterns"""
        
        # Calculate text statistics
        font_sizes = [line.font_size for line in text_lines]
        avg_font_size = statistics.mean(font_sizes)
        median_font_size = statistics.median(font_sizes)
        
        # Analyze indentation patterns
        indentations = [line.x_start for line in text_lines if len(line.text.split()) > 2]
        common_indent = statistics.mode(indentations) if indentations else 0
        
        # Detect headers
        headers = self._detect_headers(text_lines, avg_font_size, common_indent)
        
        # Detect TOC
        toc_sections = self._detect_toc_sections(text_lines, headers) if config.get("toc_detection_enabled") else []
        
        # Detect LVL1 sections
        lvl1_sections = self._detect_lvl1_sections(headers, text_lines)
        
        return {
            "font_statistics": {
                "avg_font_size": avg_font_size,
                "median_font_size": median_font_size,
                "font_size_range": [min(font_sizes), max(font_sizes)]
            },
            "indentation": {
                "common_indent": common_indent,
                "indent_variations": len(set(indentations))
            },
            "headers_detected": len(headers),
            "toc_sections": len(toc_sections),
            "lvl1_sections": len(lvl1_sections),
            "headers": headers,
            "toc_candidates": toc_sections,
            "lvl1_candidates": lvl1_sections
        }
    
    def _detect_headers(self, text_lines: List[TextLine], avg_font_size: float, common_indent: float) -> List[Dict]:
        """Detect header lines using multi-factor analysis"""
        headers = []
        
        for i, line in enumerate(text_lines):
            score = 0
            reasons = []
            
            # Font size analysis
            if line.font_size > avg_font_size * 1.3:
                score += 3
                reasons.append("large_font")
            elif line.font_size > avg_font_size * 1.1:
                score += 1
                reasons.append("medium_font")
            
            # Numbering patterns
            if re.match(r'^(Art\.|Artykuł|§|Rozdział|\d+\.|\w+\s+\d+|Chapter|Section)', line.text):
                score += 4
                reasons.append("numbering")
            
            # Position and indentation
            if line.x_start < common_indent - 10:  # Less indented
                score += 2
                reasons.append("less_indent")
            
            if line.x_start == 0:  # Flush left
                score += 1
                reasons.append("flush_left")
            
            # Length (headers usually concise)
            word_count = len(line.text.split())
            if 2 <= word_count <= 12:
                score += 1
                reasons.append("concise")
            
            # Layout label
            if line.layout_label in ['Title', 'Header']:
                score += 3
                reasons.append("layout_header")
            
            # Whitespace isolation
            if self._has_whitespace_isolation(line, text_lines, i):
                score += 2
                reasons.append("isolated")
            
            # Common header phrases
            if re.search(r'(warunki|ogólne|definicje|zasady|procedury|część|sekcja)', line.text.lower()):
                score += 1
                reasons.append("header_keywords")
            
            if score >= 5:  # Confidence threshold
                headers.append({
                    "line": line,
                    "score": score,
                    "reasons": reasons,
                    "confidence": min(score / 8.0, 1.0)  # Normalize to 0-1
                })
        
        print(f"🎯 Detected {len(headers)} potential headers")
        return headers
    
    def _has_whitespace_isolation(self, line: TextLine, all_lines: List[TextLine], line_index: int) -> bool:
        """Check if line has whitespace above and below"""
        same_page_lines = [l for l in all_lines if l.page == line.page]
        same_page_lines.sort(key=lambda l: l.y_start)
        
        line_idx_in_page = next((i for i, l in enumerate(same_page_lines) if l == line), -1)
        if line_idx_in_page == -1:
            return False
        
        # Check spacing
        has_space_above = line_idx_in_page == 0 or (line.y_start - same_page_lines[line_idx_in_page - 1].y_start) > 30
        has_space_below = line_idx_in_page == len(same_page_lines) - 1 or (same_page_lines[line_idx_in_page + 1].y_start - line.y_start) > 30
        
        return has_space_above and has_space_below
    
    def _detect_toc_sections(self, text_lines: List[TextLine], headers: List[Dict]) -> List[Dict]:
        """Detect Table of Contents sections"""
        toc_candidates = []
        
        for header in headers:
            line = header["line"]
            
            # TOC keywords
            if re.search(r'(spis treści|table of contents|contents|indice|sommaire)', line.text.lower()):
                # Look for TOC content after this header
                toc_content = self._find_toc_content_after_header(line, text_lines)
                if toc_content:
                    toc_candidates.append({
                        "header_line": line,
                        "content_lines": toc_content,
                        "confidence": header["confidence"]
                    })
        
        return toc_candidates
    
    def _find_toc_content_after_header(self, header_line: TextLine, text_lines: List[TextLine]) -> List[TextLine]:
        """Find TOC content lines after TOC header"""
        toc_lines = []
        
        # Get lines on same and following pages
        relevant_lines = [line for line in text_lines 
                         if line.page >= header_line.page and 
                         (line.page > header_line.page or line.y_start > header_line.y_start)]
        
        for line in relevant_lines[:50]:  # Check next 50 lines max
            # TOC entry patterns
            if re.search(r'.+\.{3,}\s*\d+\s*$|.+\s{3,}\d+\s*$|\d+\.\s+.+\s+\d+', line.text):
                toc_lines.append(line)
            elif len(toc_lines) > 0 and not re.search(r'\d+', line.text):
                # Stop if we have TOC lines and current line doesn't look like TOC
                break
        
        return toc_lines if len(toc_lines) >= 3 else []
    
    def _detect_lvl1_sections(self, headers: List[Dict], text_lines: List[TextLine]) -> List[Dict]:
        """Detect LVL1 sections (major document sections)"""
        lvl1_candidates = []
        
        # Sort headers by position
        sorted_headers = sorted(headers, key=lambda h: (h["line"].page, h["line"].y_start))
        
        for i, header in enumerate(sorted_headers):
            line = header["line"]
            
            # LVL1 criteria
            is_lvl1 = (
                header["score"] >= 6 or  # High confidence header
                re.match(r'^(Art\.|Artykuł|Rozdział|\d+\.|Chapter|Section)', line.text) or  # Strong numbering
                line.layout_label == 'Title' or  # Surya detected as title
                line.font_size > 20  # Large font
            )
            
            if is_lvl1:
                # Calculate section boundaries
                next_header = sorted_headers[i + 1] if i + 1 < len(sorted_headers) else None
                
                end_page = next_header["line"].page if next_header else max(l.page for l in text_lines)
                end_y = next_header["line"].y_start if next_header and next_header["line"].page == line.page else float('inf')
                
                lvl1_candidates.append({
                    "header": header,
                    "start_page": line.page,
                    "start_y": line.y_start,
                    "end_page": end_page,
                    "end_y": end_y,
                    "estimated_pages": end_page - line.page + 1
                })
        
        return lvl1_candidates
    
    def _create_sections(self, structure: Dict, text_lines: List[TextLine], config) -> List[Section]:
        """Create final section objects"""
        sections = []
        
        # Add TOC sections
        for toc in structure["toc_candidates"]:
            header_line = toc["header_line"]
            content_lines = toc["content_lines"]
            
            sections.append(Section(
                title=f"TOC: {header_line.text}",
                start_page=header_line.page,
                end_page=max(line.page for line in content_lines),
                start_y=header_line.y_start,
                end_y=max(line.y_start for line in content_lines),
                content_lines=[header_line] + content_lines,
                section_type="toc",
                page_numbers=self._extract_page_numbers_from_lines(content_lines) if config.get("extract_page_numbers") else []
            ))
        
        # Add LVL1 sections
        for lvl1 in structure["lvl1_candidates"]:
            header = lvl1["header"]
            header_line = header["line"]
            
            # Extract content lines for this section
            content_lines = self._extract_section_content(
                text_lines, 
                lvl1["start_page"], 
                lvl1["start_y"],
                lvl1["end_page"],
                lvl1["end_y"]
            )
            
            sections.append(Section(
                title=self._clean_section_title(header_line.text),
                start_page=lvl1["start_page"],
                end_page=lvl1["end_page"],
                start_y=lvl1["start_y"],
                end_y=lvl1["end_y"],
                content_lines=content_lines,
                section_type="lvl1_section",
                page_numbers=self._extract_page_numbers_from_lines(content_lines) if config.get("extract_page_numbers") else []
            ))
        
        return sorted(sections, key=lambda s: (s.start_page, s.start_y))
    
    def _extract_section_content(self, text_lines: List[TextLine], start_page: int, start_y: float, 
                                end_page: int, end_y: float) -> List[TextLine]:
        """Extract text lines for a section"""
        content_lines = []
        
        for line in text_lines:
            # Check if line is within section boundaries
            if line.page < start_page or line.page > end_page:
                continue
            
            if line.page == start_page and line.y_start < start_y:
                continue
            
            if line.page == end_page and end_y != float('inf') and line.y_start > end_y:
                continue
            
            content_lines.append(line)
        
        return content_lines
    
    def _extract_page_numbers_from_lines(self, lines: List[TextLine]) -> List[int]:
        """Extract page numbers mentioned in text"""
        page_numbers = []
        
        for line in lines:
            # Look for page number patterns
            matches = re.findall(r'\b(\d{1,4})\b', line.text)
            for match in matches:
                num = int(match)
                if 1 <= num <= 9999:  # Reasonable page number range
                    page_numbers.append(num)
        
        return sorted(list(set(page_numbers)))
    
    def _clean_section_title(self, title: str) -> str:
        """Clean section title"""
        # Remove excessive whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Truncate if too long
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title
    
    def _section_to_dict(self, section: Section) -> Dict:
        """Convert Section to dict for JSON output"""
        return {
            "title": section.title,
            "start_page": section.start_page,
            "end_page": section.end_page,
            "start_y": section.start_y,
            "end_y": section.end_y,
            "section_type": section.section_type,
            "content_length": len(section.content_text),
            "lines_count": len(section.content_lines),
            "page_numbers_mentioned": section.page_numbers,
            "estimated_pages": section.end_page - section.start_page + 1
        }
    
    def _print_sections_summary(self, sections: List[Section]):
        """Print sections summary"""
        print("\n📚 SECTIONS SUMMARY:")
        for i, section in enumerate(sections):
            print(f"  {i+1}. [{section.section_type.upper()}] {section.title}")
            print(f"      Pages: {section.start_page}-{section.end_page} ({section.estimated_pages} pages)")
            if section.page_numbers:
                print(f"      References: {section.page_numbers[:10]}{'...' if len(section.page_numbers) > 10 else ''}")
            print()