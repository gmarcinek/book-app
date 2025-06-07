import os

from anthropic import Anthropic

from .base import BaseLLMClient, LLMConfig
from .models import ModelProvider

class AnthropicClient(BaseLLMClient):
    """Klient dla Claude 4 - scenario & planning powerhouse"""
    
    # Mapowanie nazw modeli na rzeczywiste nazwy API - tylko Claude 4
    MODEL_MAPPING = {
        "claude-4-sonnet": "claude-sonnet-4-20250514"
    }
    
    def __init__(self, model: str):
        self.model = model
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("Brak zmiennej środowiskowej ANTHROPIC_API_KEY")
    
    def _get_api_model_name(self) -> str:
        """Zwróć rzeczywistą nazwę modelu dla API"""
        return self.MODEL_MAPPING.get(self.model, self.model)
    
    def chat(self, prompt: str, config: LLMConfig) -> str:
        """Wyślij prompt do Claude 4 - optimized for mega scenarios"""
        try:
            api_model = self._get_api_model_name()
            
            # Przygotuj parametry - Claude 4 lubi duże limity
            params = {
                "model": api_model,
                "max_tokens": config.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": config.temperature,
                "timeout": 600.0,  # 10 minut timeout
                "stream": False    # Explicit non-streaming
            }
            
            # Dodaj system message jeśli istnieje
            if config.system_message:
                params["system"] = config.system_message
            
            # Dodaj dodatkowe parametry wspierane przez Anthropic
            if config.extra_params:
                supported_params = ['top_p', 'top_k', 'stop_sequences']
                for key, value in config.extra_params.items():
                    if key in supported_params:
                        params[key] = value
            
            response = self.client.messages.create(**params)
            
            if not response.content:
                raise RuntimeError("Brak odpowiedzi z Claude 4 (content == []).")
            
            # Claude zwraca listę bloków treści
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text
            
            if not content.strip():
                raise RuntimeError("Claude 4 zwrócił pustą odpowiedź.")
            
            return content.strip()
            
        except Exception as e:
            raise RuntimeError(f"❌ Błąd Claude 4 ({self.model}): {e}")
    
    def get_provider(self) -> ModelProvider:
        """Zwróć providera"""
        return ModelProvider.ANTHROPIC