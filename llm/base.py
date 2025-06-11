from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .models import ModelProvider


@dataclass
class LLMConfig:
    """Konfiguracja dla modeli LLM"""
    max_tokens: int = 4096
    temperature: float = 0.0
    system_message: Optional[str] = None
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class BaseLLMClient(ABC):
    """Abstrakcyjna klasa bazowa dla clientów LLM"""
    
    @abstractmethod
    def chat(self, prompt: str, config: LLMConfig) -> str:
        """Wyślij prompt i otrzymaj odpowiedź"""
        pass
    
    @abstractmethod
    def get_provider(self) -> ModelProvider:
        """Zwróć providera modelu"""
        pass