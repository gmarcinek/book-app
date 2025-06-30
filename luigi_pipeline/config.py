"""
Simple YAML-based Luigi Pipeline Configuration
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from llm.models import ModelProvider, get_model_provider, get_model_output_limit


class PipelineConfig:
    """
    Simple YAML-based configuration loader for Luigi preprocessing pipeline
    
    Usage:
        config = PipelineConfig()
        model = config.get_task_setting("LLMMarkdownProcessor", "model")
        tokens = config.get_max_tokens_for_model(model)  # Auto from llm.models
    """
    
    def __init__(self, config_file: str = "luigi_pipeline/config.yaml"):
        """
        Load configuration from YAML file
        
        Args:
            config_file: Path to YAML config file
        """
        self.config_file = Path(config_file)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get_task_setting(self, task_name: str, setting_name: str, default: Any = None) -> Any:
        """
        Get setting for specific task
        
        Args:
            task_name: Name of the Luigi task (e.g., "LLMMarkdownProcessor")
            setting_name: Name of the setting (e.g., "model", "temperature")
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        return self.config.get(task_name, {}).get(setting_name, default)
    
    def get_max_tokens_for_model(self, model: str) -> int:
        """Get max output tokens for model from llm.models config"""
        return get_model_output_limit(model)
    
    def get_global_setting(self, setting_path: str, default: Any = None) -> Any:
        """
        Get global setting using dot notation
        
        Args:
            setting_path: Dot-separated path (e.g., "performance.timeout")
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
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
    return config.get_task_setting(task_name, "model", "gpt-4o-mini")


def get_max_tokens_for_task_model(task_name: str) -> int:
    """Get max_tokens for task's model from llm.models"""
    config = load_config()
    model = config.get_task_setting(task_name, "model", "gpt-4o-mini")
    return config.get_max_tokens_for_model(model)