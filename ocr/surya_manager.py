import os
from typing import Dict, Any, Optional


class SuryaModelManager:
    """Singleton manager for Surya models to avoid repeated loading"""
    
    _instance = None
    _models = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_models(self) -> Dict[str, Any]:
        """Get loaded Surya models, load if first time"""
        if self._models is None:
            self._load_models()
        return self._models
    
    def _load_models(self):
        """Load Surya models once"""
        try:
            print(f"🔄 Loading Surya models in PID {os.getpid()}")
            
            from surya.detection import DetectionPredictor
            from surya.recognition import RecognitionPredictor
            from surya.layout import LayoutPredictor
            
            self._models = {
                'detection_predictor': DetectionPredictor(),
                'recognition_predictor': RecognitionPredictor(),
                'layout_predictor': LayoutPredictor()
            }
            
            print(f"✅ Surya models loaded (~3-4GB VRAM)")
            
        except Exception as e:
            print(f"❌ Failed to load Surya models: {e}")
            raise RuntimeError(f"Cannot initialize Surya: {e}")