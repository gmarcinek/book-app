"""
Embedding Models Configuration and Domain Mapping - Polish MVP
"""

from typing import Dict, Any, List
from .base import SemanticChunkingConfig, ChunkingStrategy


# MVP: Single multilingual model for all domains (Polish-friendly)
# DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# DEFAULT_MODEL = "allegro/herbert-base-cased"
FALLBACK_MODEL = "allegro/herbert-base-cased"  # Polish-specific fallback


# Domain-specific configurations (same model, different parameters)
DOMAIN_EMBEDDING_CONFIGS = {
    "literary": {
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 92.0,  # Less aggressive - preserve narrative flow
        "description": "Multilingual model for Polish literary texts"
    },
    
    "simple": {
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 88.0,  # More aggressive
        "description": "Multilingual model for simple Polish content"
    },
    
    "auto": {   
        "model_name": DEFAULT_MODEL,
        "strategy": ChunkingStrategy.PERCENTILE,
        "percentile": 90.0,  # Standard default
        "description": "Default multilingual model for Polish texts"
    }
}

def get_domain_confidence_threshold(domain_name: str) -> float:
    """Get confidence threshold for domain validation"""
    domain_config = get_domain_config(domain_name)
    return domain_config.get("confidence_threshold", 0.3)

def get_domain_config(domain_name: str) -> Dict[str, Any]:
    return DOMAIN_EMBEDDING_CONFIGS.get(domain_name, DOMAIN_EMBEDDING_CONFIGS["auto"])


def create_semantic_config(domain_name: str, available_ram_mb: int = None) -> SemanticChunkingConfig:
    domain_config = get_domain_config(domain_name)
    model_name = domain_config["model_name"]
    
    return SemanticChunkingConfig(
        strategy=domain_config["strategy"],
        model_name=model_name,
        percentile=domain_config["percentile"],
        min_chunk_size=500,
        max_chunk_size=10000
    )


def get_available_domains() -> List[str]:
    """Get list of available domain names"""
    return list(DOMAIN_EMBEDDING_CONFIGS.keys())


def check_model_availability(model_name: str = None) -> bool:
    test_model = model_name or DEFAULT_MODEL
    
    try:
        from sentence_transformers import SentenceTransformer
        # Attempt to load the model
        SentenceTransformer(test_model)
        return True
    except Exception as e:
        print(f"⚠️ Model {test_model} not available: {e}")
        return False
