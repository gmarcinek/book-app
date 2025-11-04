"""
Simple YAML-based Luigi Pipeline Configuration
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from llm.models import get_model_provider, get_model_output_limit


class PipelineConfig:
    """
    Simple YAML-based configuration loader for Luigi preprocessing pipeline
    """
    
    def __init__(self, config_file: str = "luigi_pipeline/config.yaml"):
        self.config_file = Path(config_file)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get_task_setting(self, task_name: str, setting_name: str, default: Any = None) -> Any:
        return self.config.get(task_name, {}).get(setting_name, default)
    
    def get_max_tokens_for_model(self, model: str) -> int:
        """Get max output tokens for model from llm.models config"""
        return get_model_output_limit(model)
    
    def get_global_setting(self, setting_path: str, default: Any = None) -> Any:
        keys = setting_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_model_delay(self, model: str) -> float:
        """Get delay for specific model based on provider"""
        try:
            provider = get_model_provider(model)
            provider_delays = self.config.get("provider_delays", {})
            return provider_delays.get(provider.value, 0.0)
        except:
            # Fallback for unknown models
            return 0.0
    
    def get_all_task_settings(self, task_name: str) -> Dict[str, Any]:
        """Get all settings for a specific task"""
        return self.config.get(task_name, {})
    
    def reload(self):
        """Reload configuration from file"""
        self._load_config()


# Convenience functions for common usage patterns
def load_config() -> PipelineConfig:
    """Load configuration"""
    return PipelineConfig()


def get_task_config(task_name: str) -> Dict[str, Any]:
    """Get all configuration for a specific task"""
    config = load_config()
    return config.get_all_task_settings(task_name)


def get_model_for_task(task_name: str) -> str:
    """Get model name for specific task"""
    config = load_config()
    return config.get_task_setting(task_name, "model", "gpt-5-mini")


def get_max_tokens_for_task_model(task_name: str) -> int:
    """Get max_tokens for task's model from llm.models"""
    config = load_config()
    model = config.get_task_setting(task_name, "model", "gpt-5-mini")
    return config.get_max_tokens_for_model(model)