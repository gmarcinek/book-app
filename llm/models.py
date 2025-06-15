from enum import Enum

class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

class Models:
    # OpenAI - emergency backup
    GPT_4_1_MINI = "gpt-4.1-mini"
    GPT_4_1_NANO = "gpt-4.1-nano"
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

# Mapowanie modeli na providerów
MODEL_PROVIDERS = {
    Models.GPT_4_1_MINI: ModelProvider.OPENAI,
    Models.GPT_4_1_NANO: ModelProvider.OPENAI,
    Models.GPT_4O: ModelProvider.OPENAI,
    Models.GPT_4O_MINI: ModelProvider.OPENAI,
    Models.CLAUDE_4_SONNET: ModelProvider.ANTHROPIC,
    Models.CLAUDE_4_OPUS: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_5_SONNET: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_5_HAIKU: ModelProvider.ANTHROPIC,
    Models.CLAUDE_3_HAIKU: ModelProvider.ANTHROPIC,
    Models.QWEN_CODER: ModelProvider.OLLAMA,
    Models.QWEN_CODER_32B: ModelProvider.OLLAMA,
    Models.CODESTRAL: ModelProvider.OLLAMA,
}

# Maksymalne limity OUTPUT tokenów
MODEL_MAX_TOKENS = {
    Models.GPT_4_1_MINI: 32768,
    Models.GPT_4_1_NANO: 32768,
    Models.GPT_4O: 16384,
    Models.GPT_4O_MINI: 16384,
    Models.CLAUDE_4_SONNET: 64000,  # Updated from research: 64K output tokens
    Models.CLAUDE_4_OPUS: 32000,    # Updated from research: 32K output tokens
    Models.CLAUDE_3_5_SONNET: 8192,
    Models.CLAUDE_3_5_HAIKU: 8192,
    Models.CLAUDE_3_HAIKU: 8192,
    Models.QWEN_CODER: 32768,
    Models.QWEN_CODER_32B: 32768,
    Models.CODESTRAL: 32768,
}

# INPUT context window limits - rzeczywiste specyfikacje z dokumentacji
MODEL_INPUT_CONTEXT = {
    Models.GPT_4_1_MINI: 1000000,      # 1M tokens context window
    Models.GPT_4_1_NANO: 1047576,      # ~1.047M tokens context window
    Models.GPT_4O: 128000,             # 128K tokens context window  
    Models.GPT_4O_MINI: 128000,        # 128K tokens context window
    Models.CLAUDE_4_SONNET: 200000,    # 200K tokens context window
    Models.CLAUDE_4_OPUS: 200000,      # 200K tokens context window
    Models.CLAUDE_3_5_SONNET: 200000,  # 200K tokens context window
    Models.CLAUDE_3_5_HAIKU: 200000,   # 200K tokens context window
    Models.CLAUDE_3_HAIKU: 200000,     # 200K tokens context window
    Models.QWEN_CODER: 32768,          # 32K estimated for local models
    Models.QWEN_CODER_32B: 32768,      # 32K estimated for local models  
    Models.CODESTRAL: 32768,           # 32K estimated for local models
}

def get_model_input_limit(model_name: str) -> int:
    """Get input context window limit for model"""
    return MODEL_INPUT_CONTEXT.get(model_name, 32768)  # safe fallback

def get_model_output_limit(model_name: str) -> int:
    """Get output tokens limit for model"""
    return MODEL_MAX_TOKENS.get(model_name, 8192)  # safe fallback