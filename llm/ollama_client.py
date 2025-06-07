import requests
import json

from .base import BaseLLMClient, LLMConfig
from .models import ModelProvider

class OllamaClient(BaseLLMClient):
    """Klient dla lokalnych coding models - zero kosztów, maksymalna wydajność"""
    
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip('/')
        
        # Sprawdź czy Ollama działa
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                raise RuntimeError(f"Ollama niedostępna pod {self.base_url}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Nie można połączyć z Ollama: {e}")
    
    def chat(self, prompt: str, config: LLMConfig) -> str:
        """Wyślij prompt do lokalnego coding model"""
        try:
            # Przygotuj messages
            messages = []
            if config.system_message:
                messages.append({"role": "system", "content": config.system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Przygotuj parametry - optimized for coding
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": config.max_tokens,
                    # Coding-specific optimizations
                    "repeat_penalty": 1.1,  # unikaj powtórzeń w kodzie
                    "top_p": 0.9,           # zachowaj kreatywność ale z kontrolą
                }
            }
            
            # Dodaj dodatkowe parametry
            if config.extra_params:
                # Ollama obsługuje różne parametry w "options"
                supported_params = ['top_p', 'top_k', 'repeat_penalty', 'seed', 'num_ctx']
                for key, value in config.extra_params.items():
                    if key in supported_params:
                        payload["options"][key] = value
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300  # 5 minut timeout dla dużych modeli i długiego kodu
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
            
            result = response.json()
            
            if "message" not in result or "content" not in result["message"]:
                raise RuntimeError("Brak odpowiedzi z Ollama (nieprawidłowy format).")
            
            content = result["message"]["content"].strip()
            if not content:
                raise RuntimeError("Ollama zwróciła pustą odpowiedź.")
            
            return content
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"❌ Błąd połączenia z Ollama ({self.model}): {e}")
        except Exception as e:
            raise RuntimeError(f"❌ Błąd Ollama ({self.model}): {e}")
    
    def get_provider(self) -> ModelProvider:
        """Zwróć providera"""
        return ModelProvider.OLLAMA
    
    def list_models(self) -> list:
        """Lista dostępnych modeli w Ollama - przydatne do sprawdzenia co mamy"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []
    
    def pull_model(self, model_name: str = None) -> bool:
        """Pobierz model jeśli nie istnieje - auto-pull bieżącego modelu"""
        try:
            target_model = model_name or self.model
            payload = {"name": target_model}
            response = requests.post(f"{self.base_url}/api/pull", json=payload, timeout=1800)
            return response.status_code == 200
        except:
            return False
    
    def ensure_model_exists(self) -> bool:
        """Sprawdź czy model istnieje, jeśli nie - pobierz go"""
        available_models = self.list_models()
        if self.model not in available_models:
            print(f"Model {self.model} nie znaleziony. Pobieram...")
            return self.pull_model()
        return True