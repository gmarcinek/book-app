"""
OpenAI Embeddings Client with batching and error handling
"""

import os
import hashlib
import logging
from typing import List, Union, Dict, Any
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbeddingsClient:
    """
    OpenAI embeddings client with batching support
    Uses text-embedding-3-small model (1536 dimensions)
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_dim = 1536  # text-embedding-3-small dimensions
        
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not found in environment")
        
        print(f"🔌 OpenAI Embeddings initialized: {model} ({self.embedding_dim}D)")
        logger.info(f"🔌 OpenAI Embeddings initialized: {model} ({self.embedding_dim}D)")
    
    def embed_single(self, text: str) -> np.ndarray:
        if not text.strip():
            print(f"⚪ Empty text, returning zero embedding")
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        text_preview = text[:50] + "..." if len(text) > 50 else text
        print(f"🧠 Generating embedding for: '{text_preview}'")
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                encoding_format="float"
            )
            
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Normalize embedding
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            print(f"✅ Embedding generated successfully (norm: {norm:.3f})")
            return embedding
            
        except Exception as e:
            print(f"❌ OpenAI embeddings API failed: {e}")
            logger.error(f"❌ OpenAI embeddings API failed: {e}")
            raise RuntimeError(f"Sorry, OpenAI embeddings service is down: {e}")
    
    def embed_batch(self, texts: List[str], batch_size: int = 2048) -> List[np.ndarray]:
        if not texts:
            print(f"⚪ No texts to embed")
            return []
        
        total_batches = (len(texts) - 1) // batch_size + 1
        print(f"🚀 Starting batch embedding: {len(texts)} texts in {total_batches} batches")
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_num = i // batch_size + 1
            batch = texts[i:i + batch_size]
            
            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} texts)")
            
            # Filter empty texts and keep track of indices
            non_empty_texts = []
            empty_indices = []
            
            for j, text in enumerate(batch):
                if text.strip():
                    non_empty_texts.append(text.strip())
                else:
                    empty_indices.append(j)
            
            if empty_indices:
                print(f"⚪ Found {len(empty_indices)} empty texts in batch")
            
            if not non_empty_texts:
                # All texts empty
                print(f"⚠️ All texts in batch are empty, using zero embeddings")
                batch_embeddings = [np.zeros(self.embedding_dim, dtype=np.float32) for _ in batch]
            else:
                try:
                    print(f"🧠 Calling OpenAI API for {len(non_empty_texts)} texts...")
                    
                    response = self.client.embeddings.create(
                        model=self.model,
                        input=non_empty_texts,
                        encoding_format="float"
                    )
                    
                    print(f"📡 OpenAI API response received")
                    
                    # Extract embeddings and normalize
                    batch_embeddings = []
                    non_empty_idx = 0
                    
                    for j in range(len(batch)):
                        if j in empty_indices:
                            batch_embeddings.append(np.zeros(self.embedding_dim, dtype=np.float32))
                        else:
                            embedding = np.array(
                                response.data[non_empty_idx].embedding, 
                                dtype=np.float32
                            )
                            
                            # Normalize
                            norm = np.linalg.norm(embedding)
                            if norm > 0:
                                embedding = embedding / norm
                            
                            batch_embeddings.append(embedding)
                            non_empty_idx += 1
                    
                    print(f"✅ Batch {batch_num} processed successfully")
                
                except Exception as e:
                    print(f"❌ OpenAI batch embeddings failed: {e}")
                    logger.error(f"❌ OpenAI batch embeddings failed: {e}")
                    raise RuntimeError(f"Sorry, OpenAI embeddings service is down: {e}")
            
            embeddings.extend(batch_embeddings)
            
            if total_batches > 1:
                print(f"📊 Progress: {len(embeddings)}/{len(texts)} embeddings generated")
        
        print(f"🎉 Batch embedding complete: {len(embeddings)} embeddings generated")
        return embeddings
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        if embedding1 is None or embedding2 is None:
            print(f"⚠️ Cannot compute similarity: one embedding is None")
            return 0.0
        
        # Since embeddings are normalized, dot product = cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        # Clamp to [0, 1] range
        similarity_clamped = max(0.0, min(1.0, float(similarity)))
        
        if similarity != similarity_clamped:
            print(f"⚠️ Similarity clamped: {similarity:.3f} → {similarity_clamped:.3f}")
        
        return similarity_clamped
    
    def get_text_hash(self, text: str) -> str:
        """Generate cache key for text"""
        hash_value = hashlib.sha256(text.encode('utf-8')).hexdigest()
        text_preview = text[:30] + "..." if len(text) > 30 else text
        print(f"🔑 Generated hash for '{text_preview}': {hash_value[:12]}...")
        return hash_value
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        info = {
            "model": self.model,
            "embedding_dim": self.embedding_dim,
            "provider": "openai",
            "max_batch_size": 2048
        }
        print(f"ℹ️ Model info: {info}")
        return info