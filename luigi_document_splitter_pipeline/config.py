"""
Config loader for document splitter
"""

import yaml
from pathlib import Path

class DocumentSplitterConfig:
    def __init__(self, config_file="config.yaml"):
        self.config_file = Path(__file__).parent / config_file
        self._load_config()
    
    def _load_config(self):
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}
    
    def get_task_setting(self, task_name, setting_name, default=None):
        return self.config.get(task_name, {}).get(setting_name, default)

def load_config():
    return DocumentSplitterConfig()