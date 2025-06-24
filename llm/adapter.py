from typing import Dict, Any, Optional
from .base import LLMConfig, BaseLLMClient
from .models import ModelProvider, MODEL_PROVIDERS, MODEL_MAX_TOKENS
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from .ollama_client import OllamaClient

class LLMClient:
    """Minimalistyczny adapter zarządzający różnymi providerami LLM"""
    
    def __init__(self, model: str, max_tokens: Optional[int] = None, temperature: float = 0.0, system_message: Optional[str] = None):
        """
        Inicjalizuj klienta LLM
        
        Args:
            model: Nazwa modelu (np. Models.CLAUDE_4_SONNET, Models.QWEN_CODER_32B)
            max_tokens: Maksymalna liczba tokenów (None = użyj maksimum dla modelu)
            temperature: Temperatura modelu (0.0-1.0)
            system_message: Opcjonalny system message
        """
        if model not in MODEL_PROVIDERS:
            raise ValueError(f"Nieobsługiwany model: {model}. Dostępne: {list(MODEL_PROVIDERS.keys())}")
        
        self.model = model
        self.provider = MODEL_PROVIDERS[model]
        
        # Ustaw max_tokens - użyj maksimum dla modelu jeśli nie podano
        if max_tokens is None:
            max_tokens = MODEL_MAX_TOKENS[self.model]
        
        self.config = LLMConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            system_message=system_message
        )
        
        # Zainicjalizuj odpowiedni klient
        self.client = self._create_client()
    
    def _create_client(self) -> BaseLLMClient:
        """Utwórz odpowiedni klient na podstawie providera"""
        if self.provider == ModelProvider.OPENAI:
            return OpenAIClient(self.model)
        elif self.provider == ModelProvider.ANTHROPIC:
            return AnthropicClient(self.model)
        elif self.provider == ModelProvider.OLLAMA:
            return OllamaClient(self.model)
        else:
            raise ValueError(f"Nieobsługiwany provider: {self.provider}")
    
    def chat(self, prompt: str, config: Optional[LLMConfig] = None) -> str:
        """
        Wyślij prompt do modelu
        
        Args:
            prompt: Tekst zapytania
            config: Opcjonalna konfiguracja (nadpisuje domyślną)
        """
        use_config = config if config else self.config
        
        # LOG REQUEST
        self._log_llm_request(prompt, use_config)
        
        response = self.client.chat(prompt, use_config)
        
        # LOG RESPONSE  
        self._log_llm_response(prompt, response, use_config)
        
        return response
    
    def get_max_tokens_for_model(self) -> int:
        """Zwróć maksymalną liczbę tokenów dla bieżącego modelu"""
        return MODEL_MAX_TOKENS[self.model]
    
    def get_model_info(self) -> Dict[str, Any]:
        """Zwróć informacje o modelu"""
        return {
            "model": self.model,
            "provider": self.provider.value,
            "max_tokens_available": MODEL_MAX_TOKENS[self.model],
            "current_config": {
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "has_system_message": bool(self.config.system_message)
            }
        }
    
    def _log_llm_request(self, prompt: str, config: LLMConfig):
        """Log LLM request to file"""
        try:
            from pathlib import Path
            from datetime import datetime
            import json
            
            # Create logs directory
            logs_dir = Path("semantic_store/logs")
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # milliseconds
            filename = f"llm_{timestamp}_REQUEST.txt"
            
            log_content = f"""=== LLM REQUEST ===
    Timestamp: {datetime.now().isoformat()}
    Model: {self.model}
    Temperature: {config.temperature}
    Max Tokens: {config.max_tokens}
    System Message: {config.system_message or 'None'}

    PROMPT:
    {prompt}

    =====================================
    """
            
            (logs_dir / filename).write_text(log_content, encoding='utf-8')
            
        except Exception as e:
            print(f"⚠️ Failed to log LLM request: {e}")

    def _log_llm_response(self, prompt: str, response: str, config: LLMConfig):
        """Log LLM response to file"""
        try:
            from pathlib import Path
            from datetime import datetime
            
            logs_dir = Path("semantic_store/logs")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"llm_{timestamp}_RESPONSE.txt"
            
            log_content = f"""=== LLM RESPONSE ===
    Timestamp: {datetime.now().isoformat()}
    Model: {self.model}
    Prompt Length: {len(prompt)} chars
    Response Length: {len(response)} chars
    Response Word Count: {len(response.split())}

    PROMPT (first 200 chars):
    {prompt[:200]}...

    RESPONSE:
    {response}

    =====================================
    """
            
            (logs_dir / filename).write_text(log_content, encoding='utf-8')
            
        except Exception as e:
            print(f"⚠️ Failed to log LLM response: {e}")