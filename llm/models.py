from enum import Enum

class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

class Models:
    # OpenAI - emergency backup
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    
    # Anthropic - scenario powerhouse  
    CLAUDE_4_SONNET = "claude-4-sonnet"
    
    # Ollama - coding beasts
    QWEN_CODER = "qwen2.5-coder"
    QWEN_CODER_32B = "qwen2.5-coder:32b" 
    CODESTRAL = "codestral"


# Mapowanie modeli na providerów
MODEL_PROVIDERS = {
    Models.GPT_4_1_MINI: ModelProvider.OPENAI,
    Models.GPT_4O: ModelProvider.OPENAI,
    Models.GPT_4O_MINI: ModelProvider.OPENAI,
    Models.CLAUDE_4_SONNET: ModelProvider.ANTHROPIC,
    Models.QWEN_CODER: ModelProvider.OLLAMA,
    Models.QWEN_CODER_32B: ModelProvider.OLLAMA,
    Models.CODESTRAL: ModelProvider.OLLAMA,
}

# Maksymalne limity OUTPUT tokenów
MODEL_MAX_TOKENS = {
    Models.GPT_4_1_MINI: 32768,
    Models.GPT_4O: 16384,
    Models.GPT_4O_MINI: 16384,
    Models.CLAUDE_4_SONNET: 7000,
    Models.QWEN_CODER: 32768,
    Models.QWEN_CODER_32B: 32768,
    Models.CODESTRAL: 32768,
}