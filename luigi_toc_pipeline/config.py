"""
Configuration loader for TOC pipeline
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
load_dotenv()

class TOCConfig:
    """Configuration loader for TOC pipeline"""
    
    def __init__(self, config_file: str = None):
        if config_file is None:
            config_file = Path(__file__).parent / "config.yaml"
        
        self.config_file = Path(config_file)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get_task_setting(self, task_name: str, setting_name: str, default: Any = None) -> Any:
        """Get setting for specific task"""
        return self.config.get(task_name, {}).get(setting_name, default)
    
    def get_all_task_settings(self, task_name: str) -> Dict[str, Any]:
        """Get all settings for specific task"""
        return self.config.get(task_name, {})
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()


# Convenience function
def load_config() -> TOCConfig:
    """Load TOC pipeline configuration"""
    return TOCConfig()