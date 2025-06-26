"""
Entity embedding generation using OpenAI embeddings with disk cache
"""

import logging
import numpy as np
from typing import Dict, Tuple, Optional, List

from .models import StoredEntity, StoredChunk

logger = logging.getLogger(__name__)


class EntityEmbedder:
   """Generates embeddings for entities and chunks using OpenAI API with caching"""
   
   def __init__(self, model_name: str = "text-embedding-3-small"):
       # Initialize OpenAI embeddings client with cache
       from llm.embeddings_client import OpenAIEmbeddingsClient
       from llm.embeddings_cache import EmbeddingsCache
       
       self.model_name = model_name
       self.client = OpenAIEmbeddingsClient(model_name)
       self.cache = EmbeddingsCache(model=model_name)
       self.embedding_dim = self.client.embedding_dim
       
       print(f"🧠 EntityEmbedder initialized: {model_name} ({self.embedding_dim}D)")
       logger.info(f"🧠 EntityEmbedder initialized: {model_name} ({self.embedding_dim}D)")
   
   def generate_entity_embeddings(self, entity: StoredEntity) -> Tuple[np.ndarray, np.ndarray]:
       # Generate dual embeddings for entity (name + context)
       name_text = entity.get_semantic_text_for_name()
       context_text = entity.get_semantic_text_for_context()
       
       name_embedding = self._get_embedding_with_cache(name_text)
       context_embedding = self._get_embedding_with_cache(context_text)
       
       return name_embedding, context_embedding
   
   def generate_chunk_embedding(self, chunk: StoredChunk) -> np.ndarray:
       # Generate embedding for chunk text
       text_for_embedding = self._prepare_chunk_text(chunk.text)
       return self._get_embedding_with_cache(text_for_embedding)
   
   def update_entity_embeddings(self, entity: StoredEntity) -> bool:
       # Update entity embeddings in-place
       try:
           name_embedding, context_embedding = self.generate_entity_embeddings(entity)
           
           entity.name_embedding = name_embedding
           entity.context_embedding = context_embedding
           entity.update_timestamp()
           
           return True
           
       except Exception as e:
           logger.error(f"❌ Failed to update embeddings for entity {entity.id}: {e}")
           return False
   
   def update_chunk_embedding(self, chunk: StoredChunk) -> bool:
       # Update chunk embedding in-place
       try:
           text_embedding = self.generate_chunk_embedding(chunk)
           chunk.text_embedding = text_embedding
           return True
           
       except Exception as e:
           logger.error(f"❌ Failed to update embedding for chunk {chunk.id}: {e}")
           return False
   
   def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
       # Compute cosine similarity between embeddings
       return self.client.compute_similarity(embedding1, embedding2)
   
   def batch_generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
       # Generate embeddings for multiple texts with caching
       text_hashes = [self.client.get_text_hash(text) for text in texts]
       
       # Check cache first
       cached_results = self.cache.get_batch(text_hashes)
       
       # Find texts that need embedding
       texts_to_embed = []
       hash_to_index = {}
       
       for i, (text, text_hash) in enumerate(zip(texts, text_hashes)):
           if cached_results[text_hash] is None:
               hash_to_index[text_hash] = len(texts_to_embed)
               texts_to_embed.append(text)
       
       # Generate missing embeddings
       new_embeddings = []
       if texts_to_embed:
           print(f"🧠 Generating {len(texts_to_embed)} new embeddings from {len(texts)} total")
           new_embeddings = self.client.embed_batch(texts_to_embed)
           
           # Cache new embeddings
           cache_data = {}
           for i, text in enumerate(texts_to_embed):
               text_hash = self.client.get_text_hash(text)
               text_preview = text[:50] + "..." if len(text) > 50 else text
               cache_data[text_hash] = (new_embeddings[i], text_preview)
           
           self.cache.put_batch(cache_data)
       
       # Combine cached and new embeddings
       final_embeddings = []
       for text, text_hash in zip(texts, text_hashes):
           cached_embedding = cached_results[text_hash]
           if cached_embedding is not None:
               final_embeddings.append(cached_embedding)
           else:
               # Get from new embeddings
               new_index = hash_to_index[text_hash]
               final_embeddings.append(new_embeddings[new_index])
       
       return final_embeddings
   
   def _get_embedding_with_cache(self, text: str) -> np.ndarray:
       # Get single embedding with cache check
       text_hash = self.client.get_text_hash(text)
       
       # Check cache first
       cached_embedding = self.cache.get(text_hash)
       if cached_embedding is not None:
           return cached_embedding
       
       # Generate new embedding
       embedding = self.client.embed_single(text)
       
       # Cache it
       text_preview = text[:50] + "..." if len(text) > 50 else text
       self.cache.put(text_hash, embedding, text_preview)
       
       return embedding
   
   def _prepare_chunk_text(self, text: str, max_length: int = 1000) -> str:
       # Prepare chunk text for embedding (handle long texts)
       if len(text) <= max_length:
           return text.strip()
       
       # For long texts, take beginning + end
       half_length = max_length // 2 - 50
       beginning = text[:half_length].strip()
       ending = text[-half_length:].strip()
       
       return f"{beginning} ... {ending}"
   
   def clear_cache(self):
       # Clear embedding cache
       self.cache.clear_cache()
       print("🧹 Embedding cache cleared")
   
   def get_cache_stats(self) -> Dict[str, any]:
       # Get cache statistics
       cache_stats = self.cache.get_cache_stats()
       return {
           'embedding_dimension': self.embedding_dim,
           'model_name': self.model_name,
           **cache_stats
       }