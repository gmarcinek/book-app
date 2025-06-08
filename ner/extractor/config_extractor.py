"""
Extractor configuration management
"""

import json
from pathlib import Path
from typing import Dict, Any


class ExtractorConfig:
    """Konfiguracja dla ekstraktora encji"""
    
    def __init__(self, config_path: str = "ner/extractor_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load extractor config from {self.config_path}: {e}")
        
        # Fallback defaults
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            "extraction": {
                "max_tokens": 5000,
                "meta_analysis_temperature": 0.3,
                "entity_extraction_temperature": 0.1
            }
        }
    
    def get_meta_analysis_temperature(self) -> float:
        """Get temperature for meta-analysis phase"""
        return self.config.get("extraction", {}).get("meta_analysis_temperature", 0.3)
    
    def get_entity_extraction_temperature(self) -> float:
        """Get temperature for entity extraction phase"""
        return self.config.get("extraction", {}).get("entity_extraction_temperature", 0.1)
    
    def get_max_tokens(self) -> int:
        """Get max tokens for extraction"""
        return self.config.get("extraction", {}).get("max_tokens", 5000)
    
    def get_config(self) -> Dict[str, Any]:
        """Get full configuration"""
        return self.config.copy()