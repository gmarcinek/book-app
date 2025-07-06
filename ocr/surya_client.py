from typing import List, Dict, Any, Optional
from .base import BaseOCRClient
from .surya_manager import SuryaModelManager


class SuryaClient(BaseOCRClient):
    """Surya OCR client implementation"""
    
    def __init__(self, languages: List[str] = None):
        self.languages = languages or ['en']
        self.manager = SuryaModelManager()
    
    def process_pages(self, images: List, languages: List[str] = None) -> List[Dict[str, Any]]:
        """Process images using Surya OCR and Layout Analysis"""
        try:
            models = self.manager.get_models()
            use_languages = languages or self.languages
            
            detection_predictor = models['detection_predictor']
            recognition_predictor = models['recognition_predictor']
            layout_predictor = models['layout_predictor']
            
            print(f"🔍 Processing {len(images)} images with languages: {use_languages}")
            
            # Fix: Use supported task names instead of languages
            # Supported tasks: 'ocr_with_boxes', 'ocr_without_boxes', 'block_without_boxes'
            task_names = ['ocr_with_boxes'] * len(images)
            
            print(f"🧠 Running OCR recognition with task: ocr_with_boxes")
            ocr_predictions = recognition_predictor(images, task_names, detection_predictor)
            
            print(f"🏗️ Running layout analysis...")
            layout_predictions = layout_predictor(images)
            
            print(f"📝 Formatting results...")
            
            # Combine results
            formatted_results = []
            for i, (ocr_pred, layout_pred) in enumerate(zip(ocr_predictions, layout_predictions)):
                
                # Extract text lines with bboxes
                text_lines = []
                full_text = ""
                
                if hasattr(ocr_pred, 'text_lines') and ocr_pred.text_lines:
                    for line in ocr_pred.text_lines:
                        line_text = getattr(line, 'text', '')
                        line_bbox = getattr(line, 'bbox', [0, 0, 0, 0])
                        line_confidence = getattr(line, 'confidence', 1.0)
                        
                        text_lines.append({
                            'text': line_text,
                            'bbox': line_bbox,
                            'confidence': line_confidence
                        })
                        full_text += line_text + "\n"
                
                # Extract layout elements
                layout_elements = []
                if hasattr(layout_pred, 'bboxes') and layout_pred.bboxes:
                    for bbox_info in layout_pred.bboxes:
                        layout_elements.append({
                            'bbox': getattr(bbox_info, 'bbox', [0, 0, 0, 0]),
                            'label': getattr(bbox_info, 'label', 'unknown'),
                            'confidence': getattr(bbox_info, 'confidence', 1.0),
                            'position': getattr(bbox_info, 'position', 0)
                        })
                
                formatted_results.append({
                    "text": full_text.strip(),
                    "text_lines": text_lines,
                    "bboxes": [line['bbox'] for line in text_lines],
                    "layout": layout_elements
                })
                
                print(f"   Page {i+1}: {len(text_lines)} text lines, {len(layout_elements)} layout elements")
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Surya OCR failed: {e}")
            import traceback
            traceback.print_exc()
            return [{"text": "", "text_lines": [], "bboxes": [], "layout": [], "error": str(e)} for _ in images]