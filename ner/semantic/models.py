"""
Embedding Models Configuration and Domain Mapping - OpenAI embeddings
"""

from typing import Dict, Any, List
from .base import SemanticChunkingConfig, ChunkingStrategy


# OpenAI embeddings model - consistent across all domains
DEFAULT_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small dimensions


# Domain-specific configurations (same OpenAI model, different parameters)
DOMAIN_EMBEDDING_CONFIGS = {
   "literary": {
       "model_name": DEFAULT_MODEL,
       "strategy": ChunkingStrategy.PERCENTILE,
       "percentile": 92.0,  # Less aggressive - preserve narrative flow
       "description": "OpenAI embeddings for Polish literary texts"
   },
   
   "simple": {
       "model_name": DEFAULT_MODEL,
       "strategy": ChunkingStrategy.PERCENTILE,
       "percentile": 88.0,  # More aggressive
       "description": "OpenAI embeddings for simple Polish content"
   },
   
   "auto": {   
       "model_name": DEFAULT_MODEL,
       "strategy": ChunkingStrategy.PERCENTILE,
       "percentile": 90.0,  # Standard default
       "description": "Default OpenAI embeddings for Polish texts"
   }
}

def get_domain_config(domain_name: str) -> Dict[str, Any]:
   """Get domain configuration"""
   return DOMAIN_EMBEDDING_CONFIGS.get(domain_name, DOMAIN_EMBEDDING_CONFIGS["auto"])


def create_semantic_config(domain_name: str, available_ram_mb: int = None) -> SemanticChunkingConfig:
   """Create semantic chunking config for domain using OpenAI embeddings"""
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
   """Check if OpenAI embeddings model is available"""
   test_model = model_name or DEFAULT_MODEL
   
   try:
       from llm.embeddings_client import OpenAIEmbeddingsClient
       # Attempt to initialize the client
       client = OpenAIEmbeddingsClient(test_model)
       print(f"✅ OpenAI embeddings model {test_model} available")
       return True
   except Exception as e:
       print(f"⚠️ OpenAI embeddings model {test_model} not available: {e}")
       return False


def get_embedding_dimensions() -> int:
   """Get embedding dimensions for OpenAI model"""
   return EMBEDDING_DIMENSIONS