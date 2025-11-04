import os
from typing import Optional, List

from openai import OpenAI

from .base import BaseLLMClient, LLMConfig
from .models import ModelProvider, MODEL_MAX_TOKENS

class OpenAIClient(BaseLLMClient):
    """Klient dla modeli OpenAI - obsługuje GPT-4 i GPT-5 API"""
    
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("Brak zmiennej środowiskowej OPENAI_API_KEY")
    
    def chat(self, prompt: str, config: LLMConfig, images: Optional[List[str]] = None) -> str:
        """Wyślij prompt do OpenAI - automatycznie wybiera API (GPT-4 vs GPT-5)"""
        try:
            # Handle None max_tokens with model-specific fallback
            max_tokens = config.max_tokens or MODEL_MAX_TOKENS[self.model]
            
            # GPT-5 uses completely different API
            if self.model.startswith("gpt-5"):
                return self._chat_gpt5(prompt, config, images, max_tokens)
            else:
                return self._chat_gpt4(prompt, config, images, max_tokens)
                
        except Exception as e:
            raise RuntimeError(f"❌ Błąd OpenAI ({self.model}): {e}")
    
    def _chat_gpt5(self, prompt: str, config: LLMConfig, images: Optional[List[str]], max_tokens: int) -> str:
        """GPT-5 używa responses.create() API"""
        
        # Prepare input messages for GPT-5
        input_messages = []
        
        # Add system message as developer role
        if config.system_message:
            input_messages.append({
                "role": "developer", 
                "content": config.system_message
            })
        
        # Add main prompt as user message
        if images:
            # Vision mode - GPT-5 format
            content = [{"type": "text", "text": prompt}]
            for image_base64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                })
            input_messages.append({"role": "user", "content": content})
        else:
            # Text-only mode
            input_messages.append({"role": "user", "content": prompt})
        
        # Prepare GPT-5 parameters
        params = {
            "model": self.model,
            "input": input_messages,
        }
        
        # GPT-5 może nie obsługiwać max_completion_tokens w responses.create()
        # Zostawiamy bez ograniczenia tokenów na razie
        
        # GPT-5 reasoning effort
        if config.reasoning_effort:
            # GPT-5 API uses exact values: 'low', 'medium', 'high'
            effort = config.reasoning_effort  # Use direct mapping
            params["reasoning"] = {"effort": effort}
            print(f"🧠 GPT-5 reasoning effort: {effort}")
        
        # Call GPT-5 responses API
        response = self.client.responses.create(**params)
        
        # GPT-5 response structure debugging
        print(f"🔍 GPT-5 response.text type: {type(response.text)}")
        print(f"🔍 GPT-5 response.output_text type: {type(response.output_text)}")
        print(f"🔍 GPT-5 response.output type: {type(response.output)}")
        
        # Try different ways to get content
        content = None
        
        # Method 1: output_text
        if hasattr(response, 'output_text') and response.output_text:
            content = str(response.output_text)
            print(f"✅ Using output_text: {content[:100]}...")
        
        # Method 2: output 
        elif hasattr(response, 'output') and response.output:
            content = str(response.output)
            print(f"✅ Using output: {content[:100]}...")
        
        # Method 3: text as string
        elif hasattr(response, 'text'):
            content = str(response.text)
            print(f"✅ Using text: {content[:100]}...")
            
        # Method 4: whole response
        else:
            content = str(response)
            print(f"⚠️ Using whole response: {content[:100]}...")
        
        if not content or not content.strip():
            raise RuntimeError("GPT-5 zwrócił pustą odpowiedź.")
        
        return content.strip()
    
    def _chat_gpt4(self, prompt: str, config: LLMConfig, images: Optional[List[str]], max_tokens: int) -> str:
        """GPT-4 używa standardowego chat.completions.create() API"""
        
        # Przygotuj messages
        if images:
            # Vision mode - OpenAI format
            content = [{"type": "text", "text": prompt}]
            for image_base64 in images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                })
            messages = [{"role": "user", "content": content}]
        else:
            # Text-only mode
            messages = [{"role": "user", "content": prompt}]
        
        # Dodaj system message jeśli istnieje
        if config.system_message:
            messages.insert(0, {"role": "system", "content": config.system_message})
        
        # Przygotuj parametry GPT-4
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": config.temperature,
        }
        
        # Dodaj dodatkowe parametry
        if config.extra_params:
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
    
    def get_provider(self) -> ModelProvider:
        """Zwróć providera"""
        return ModelProvider.OPENAI