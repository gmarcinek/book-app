"""
PDF cutting utilities - bbox operations and text extraction
"""

import fitz
from typing import Tuple, Optional


class PDFCuttingUtils:
    """Utilities for PDF coordinate-based cutting and text extraction"""
    
    # Default config values
    DEFAULT_MARGIN_PX = 30
    DEFAULT_TOP_THRESHOLD_PERCENT = 15
    
    @staticmethod
    def extract_bbox_text(doc, start_page, start_y, end_page, end_y) -> str:
        """Extract text from bbox coordinates across pages"""
        if start_page == end_page:
            return PDFCuttingUtils._extract_same_page_text(doc, start_page, start_y, end_y)
        else:
            return PDFCuttingUtils._extract_multipage_text(doc, start_page, start_y, end_page, end_y)
    
    @staticmethod
    def _extract_same_page_text(doc, page_num, start_y, end_y) -> str:
        """Extract text from same page bbox"""
        source_page = doc[page_num - 1]
        page_rect = source_page.rect
        
        # Apply margin adjustment
        adjusted_start_y = PDFCuttingUtils._adjust_start_y_with_margin(start_y, page_rect.height)
        
        # Create crop rectangle
        crop_rect = fitz.Rect(0, adjusted_start_y, page_rect.width, end_y or page_rect.height)
        
        return source_page.get_text(clip=crop_rect)
    
    @staticmethod
    def _extract_multipage_text(doc, start_page, start_y, end_page, end_y) -> str:
        """Extract text from multiple pages with crops"""
        extracted_text = ""
        
        # First page: crop from start_y to bottom
        if start_y:
            source_page = doc[start_page - 1]
            page_rect = source_page.rect
            adjusted_start_y = PDFCuttingUtils._adjust_start_y_with_margin(start_y, page_rect.height)
            crop_rect = fitz.Rect(0, adjusted_start_y, page_rect.width, page_rect.height)
            extracted_text += source_page.get_text(clip=crop_rect) + "\n"
        else:
            extracted_text += doc[start_page - 1].get_text() + "\n"
        
        # Middle pages - full text
        for page_num in range(start_page, min(end_page - 1, len(doc))):
            extracted_text += doc[page_num].get_text() + "\n"
        
        # Last page: crop from top to end_y
        if end_page <= len(doc) and end_y:
            source_page = doc[end_page - 1]
            page_rect = source_page.rect
            crop_rect = fitz.Rect(0, 0, page_rect.width, end_y)
            extracted_text += source_page.get_text(clip=crop_rect)
        
        return extracted_text
    
    @staticmethod
    def create_cropped_page(section_doc, source_doc, page_num, crop_rect) -> None:
        """Add cropped page to section document"""
        new_page = section_doc.new_page(
            width=crop_rect.width, 
            height=crop_rect.height
        )
        new_page.show_pdf_page(new_page.rect, source_doc, page_num - 1, clip=crop_rect)
    
    @staticmethod
    def add_full_page(section_doc, source_doc, page_num) -> None:
        """Add full page to section document"""
        section_doc.insert_pdf(source_doc, from_page=page_num - 1, to_page=page_num - 1)
    
    @staticmethod
    def calculate_crop_rect(page_rect, start_y=None, end_y=None) -> fitz.Rect:
        """Calculate crop rectangle with margin adjustment"""
        adjusted_start_y = PDFCuttingUtils._adjust_start_y_with_margin(
            start_y or 0, page_rect.height
        )
        return fitz.Rect(
            0, 
            adjusted_start_y, 
            page_rect.width, 
            end_y or page_rect.height
        )
    
    @staticmethod
    def _adjust_start_y_with_margin(start_y, page_height):
        """Adjust start Y with margin and top threshold from config"""
        if start_y is None:
            return 0
        
        # Load config with fallback defaults
        try:
            from luigi_document_splitter_pipeline.config import load_config
            config = load_config()
            margin = config.get_task_setting("DocumentSplitter", "top_margin_px", PDFCuttingUtils.DEFAULT_MARGIN_PX)
            threshold_percent = config.get_task_setting("DocumentSplitter", "top_threshold_percent", PDFCuttingUtils.DEFAULT_TOP_THRESHOLD_PERCENT)
        except:
            margin = PDFCuttingUtils.DEFAULT_MARGIN_PX
            threshold_percent = PDFCuttingUtils.DEFAULT_TOP_THRESHOLD_PERCENT
            
        # Top threshold check
        top_threshold = page_height * (threshold_percent / 100)
        if start_y <= top_threshold:
            return 0
        
        # Apply margin
        return max(0, start_y - margin)