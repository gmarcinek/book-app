import os

from openai import OpenAI

from .base import BaseLLMClient, LLMConfig
from .models import ModelProvider

class OpenAIClient(BaseLLMClient):
    """Klient dla modeli OpenAI - tylko elite models"""
    
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Brak zmiennej środowiskowej OPENAI_API_KEY")
    
    def chat(self, prompt: str, config: LLMConfig) -> str:
        """Wyślij prompt do OpenAI"""
        try:
            # Przygotuj messages
            messages = []
            if config.system_message:
                messages.append({"role": "system", "content": config.system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Przygotuj parametry
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
            }
            
            # Dodaj dodatkowe parametry
            if config.extra_params:
                # OpenAI obsługuje różne parametry
                supported_params = ['top_p', 'frequency_penalty', 'presence_penalty', 'stop', 'seed']
                for key, value in config.extra_params.items():
                    if key in supported_params:
                        params[key] = value
            
            response = self.client.chat.completions.create(**params)
            
            if not response.choices:
                raise RuntimeError("Brak odpowiedzi z OpenAI (choices == []).")
            
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise RuntimeError("OpenAI zwrócił pustą odpowiedź.")
            
            return content.strip()
            
        except Exception as e:
            raise RuntimeError(f"❌ Błąd OpenAI ({self.model}): {e}")
    
    def get_provider(self) -> ModelProvider:
        """Zwróć providera"""
        return ModelProvider.OPENAI