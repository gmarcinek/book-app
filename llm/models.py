# PLIK: llm/models.py
from enum import Enum

class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

class Models:
    # OpenAI GPT-5 - latest reasoning models (August 2025)
    GPT_5 = "gpt-5"
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    
    # OpenAI GPT-4.1 - large context models
    GPT_4_1 = "gpt-4.1"
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
    
    # OpenAI GPT-4 legacy - emergency backup
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    
    # Anthropic - scenario powerhouse  
    CLAUDE_4_SONNET = "claude-4-sonnet"
    CLAUDE_4_OPUS = "claude-4-opus"
    CLAUDE_3_5_SONNET = "claude-3.5-sonnet"
    CLAUDE_3_5_HAIKU = "claude-3.5-haiku"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    
    # Ollama - coding beasts
    QWEN_CODER = "qwen2.5-coder"
    QWEN_CODER_32B = "qwen2.5-coder:32b" 
    CODESTRAL = "codestral"
    
    # Ollama - vision models
    LLAMA_VISION_11B = "llama3.2-vision:11b"
    LLAMA_VISION_90B = "llama3.2-vision:90b"
    QWEN_VISION_7B = "qwen2.5vl:7b"
    GEMMA3_12B = "gemma3:12b"

# Mapowanie modeli na providerów
MODEL_PROVIDERS = {
    # OpenAI GPT-5 models
    Models.GPT_5: ModelProvider.OPENAI,
    Models.GPT_5_MINI: ModelProvider.OPENAI,
    Models.GPT_5_NANO: ModelProvider.OPENAI,
    
    # OpenAI GPT-4.1 models
    Models.GPT_4_1: ModelProvider.OPENAI,
    Models.GPT_4_1_MINI: ModelProvider.OPENAI,
    Models.GPT_4_1_NANO: ModelProvider.OPENAI,
    
    # OpenAI GPT-4 legacy
    Models.GPT_4O: ModelProvider.OPENAI,
    Models.GPT_4O_MINI: ModelProvider.OPENAI,
    
    # Anthropic text models
    Models.CLAUDE_4_SONNET: ModelProvider.ANTHROPIC,
    Models.CLAUDE_4_OPUS: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_5_SONNET: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_5_HAIKU: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_HAIKU: ModelProvider.ANTHROPIC,
    
    # Ollama text models
    Models.QWEN_CODER: ModelProvider.OLLAMA,
    Models.QWEN_CODER_32B: ModelProvider.OLLAMA,
    Models.CODESTRAL: ModelProvider.OLLAMA,
    
    # Ollama vision models
    Models.LLAMA_VISION_11B: ModelProvider.OLLAMA,
    Models.LLAMA_VISION_90B: ModelProvider.OLLAMA,
    Models.QWEN_VISION_7B: ModelProvider.OLLAMA,
    Models.GEMMA3_12B: ModelProvider.OLLAMA,
}

# Vision models mapping - wszystkie OpenAI modele obsługują vision
VISION_MODELS = {
    # OpenAI vision - wszystkie GPT-5 i GPT-4.1 + legacy
    Models.GPT_5: ModelProvider.OPENAI,
    Models.GPT_5_MINI: ModelProvider.OPENAI,
    Models.GPT_5_NANO: ModelProvider.OPENAI,
    Models.GPT_4_1: ModelProvider.OPENAI,
    Models.GPT_4_1_MINI: ModelProvider.OPENAI,
    Models.GPT_4_1_NANO: ModelProvider.OPENAI,
    Models.GPT_4O: ModelProvider.OPENAI,
    Models.GPT_4O_MINI: ModelProvider.OPENAI,
    
    # Anthropic vision - wszystkie Claude modele obsługują vision
    Models.CLAUDE_4_SONNET: ModelProvider.ANTHROPIC,
    Models.CLAUDE_4_OPUS: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_5_SONNET: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_5_HAIKU: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_HAIKU: ModelProvider.ANTHROPIC,
    
    # Ollama vision
    Models.LLAMA_VISION_11B: ModelProvider.OLLAMA,
    Models.LLAMA_VISION_90B: ModelProvider.OLLAMA,
    Models.QWEN_VISION_7B: ModelProvider.OLLAMA,
    Models.GEMMA3_12B: ModelProvider.OLLAMA,
}

# Maksymalne limity OUTPUT tokenów
MODEL_MAX_TOKENS = {
    # OpenAI GPT-5 - reasoning models with 128K output limit
    Models.GPT_5: 128000,        # Full reasoning model
    Models.GPT_5_MINI: 128000,   # Mini reasoning model  
    Models.GPT_5_NANO: 128000,   # Nano reasoning model
    
    # OpenAI GPT-4.1 - large context models
    Models.GPT_4_1: 32768,       # Increased from 16K for GPT-4o
    Models.GPT_4_1_MINI: 16384,  # Standard limit
    Models.GPT_4_1_NANO: 16384,  # Standard limit
    
    # OpenAI GPT-4 legacy
    Models.GPT_4O: 16384,
    Models.GPT_4O_MINI: 16384,
    
    # Anthropic
    Models.CLAUDE_4_SONNET: 64000,
    Models.CLAUDE_4_OPUS: 32000,
    Models.CLAUDE_3_5_SONNET: 8192,
    Models.CLAUDE_3_5_HAIKU: 8192,
    Models.CLAUDE_3_HAIKU: 4096,
    
    # Ollama text
    Models.QWEN_CODER: 32768,
    Models.QWEN_CODER_32B: 32768,
    Models.CODESTRAL: 32768,
    Models.GEMMA3_12B: 8192,
    
    # Ollama vision
    Models.LLAMA_VISION_11B: 32768,
    Models.LLAMA_VISION_90B: 32768,
    Models.QWEN_VISION_7B: 128000,
}

# INPUT context window limits
MODEL_INPUT_CONTEXT = {
    # OpenAI GPT-5 - 400K total context window (official docs)
    Models.GPT_5: 400000,        # Flagship model: 400K context
    Models.GPT_5_MINI: 400000,   # Same context window  
    Models.GPT_5_NANO: 400000,   # Same context window
    
    # OpenAI GPT-4.1 - massive 1M context window
    Models.GPT_4_1: 1000000,     # 1 million tokens input
    Models.GPT_4_1_MINI: 1000000,
    Models.GPT_4_1_NANO: 1000000,
    
    # OpenAI GPT-4 legacy
    Models.GPT_4O: 128000,
    Models.GPT_4O_MINI: 128000,
    
    # Anthropic
    Models.CLAUDE_4_SONNET: 200000,
    Models.CLAUDE_4_OPUS: 200000,
    Models.CLAUDE_3_5_SONNET: 200000,
    Models.CLAUDE_3_5_HAIKU: 200000,
    Models.CLAUDE_3_HAIKU: 200000,
    
    # Ollama text
    Models.QWEN_CODER: 32768,
    Models.QWEN_CODER_32B: 32768,
    Models.CODESTRAL: 32768,
    
    # Ollama vision
    Models.LLAMA_VISION_11B: 128000,
    Models.LLAMA_VISION_90B: 128000,
    Models.QWEN_VISION_7B: 32768,
    Models.GEMMA3_12B: 128000,
}

def get_model_input_limit(model_name: str) -> int:
    """Get input context window limit for model"""
    return MODEL_INPUT_CONTEXT.get(model_name, 32768)  # safe fallback

def get_model_output_limit(model_name: str) -> int:
    """Get output tokens limit for model"""
    return MODEL_MAX_TOKENS.get(model_name, 8192)  # safe fallback

def supports_vision(model_name: str) -> bool:
    """Check if model supports vision"""
    return model_name in VISION_MODELS

def get_model_provider(model_name: str) -> ModelProvider:
    """Get provider for model"""
    return MODEL_PROVIDERS.get(model_name)