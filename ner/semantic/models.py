"""
Embedding Models Configuration and Domain Mapping - Polish MVP
"""

from typing import Dict, Any, List
from .base import SemanticChunkingConfig, ChunkingStrategy


# MVP: Single multilingual model for all domains (Polish-friendly)
# DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FALLBACK_MODEL = "allegro/herbert-base-cased"  # Polish-specific fallback


# Domain-specific configurations (same model, different parameters)
DOMAIN_EMBEDDING_CONFIGS = {
    "literary": {
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 92.0,  # Less aggressive - preserve narrative flow
        "threshold": 0.12,   # For gradient fallback
        "description": "Multilingual model for Polish literary texts"
    },
    
    "owu": {
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 97.0,  # Very precise - separate legal sections
        "threshold": 0.18,   # Sharp boundaries
        "description": "Multilingual model for Polish legal documents"
    },
    
    "liric": {
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 99.0,  # Almost no cutting - preserve poetic structure
        "threshold": 0.05,   # Very subtle
        "description": "Multilingual model for Polish poetry"
    },
    
    "simple": {
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.GRADIENT,  # Simple texts work well with gradient
        "percentile": 88.0,  # More aggressive
        "threshold": 0.10,   # Lower threshold
        "description": "Multilingual model for simple Polish content"
    },
    
    "auto": {   
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 90.0,  # Standard default
        "threshold": 0.15,   # Standard default
        "description": "Default multilingual model for Polish texts"
    }
}


def get_domain_config(domain_name: str) -> Dict[str, Any]:
    """
    Get configuration for specific domain
    
    Args:
        domain_name: Name of the domain (literary, legal, etc.)
        
    Returns:
        Domain configuration dictionary
    """
    return DOMAIN_EMBEDDING_CONFIGS.get(domain_name, DOMAIN_EMBEDDING_CONFIGS["auto"])


def create_semantic_config(domain_name: str, available_ram_mb: int = None) -> SemanticChunkingConfig:
    domain_config = get_domain_config(domain_name)
    model_name = domain_config["model_name"]
    
    return SemanticChunkingConfig(
        strategy=domain_config["strategy"],
        model_name=model_name,
        threshold=domain_config["threshold"],
        percentile=domain_config["percentile"],
        min_chunk_size=2000,
        max_chunk_size=10000
    )


def get_available_domains() -> List[str]:
    """Get list of available domain names"""
    return list(DOMAIN_EMBEDDING_CONFIGS.keys())


def check_model_availability(model_name: str = None) -> bool:
    """
    Check if default model is available
    
    Args:
        model_name: Optional model name to check, defaults to DEFAULT_MODEL
        
    Returns:
        True if model is available
    """
    test_model = model_name or DEFAULT_MODEL
    
    try:
        from sentence_transformers import SentenceTransformer
        # Attempt to load the model
        SentenceTransformer(test_model)
        return True
    except Exception as e:
        print(f"⚠️ Model {test_model} not available: {e}")
        return False
