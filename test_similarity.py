#!/usr/bin/env python3
"""
Simple Similarity Test - KISS version
"""

import re
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ner.loaders import DocumentLoader

def test_simple(document_path: str, query: str):
    # Load model
    # model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    # model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    model = SentenceTransformer("allegro/herbert-base-cased")
    
    # Load document
    loader = DocumentLoader()
    document = loader.load_document(document_path)
    
    # Extract sentences
    sentences = re.split(r'(?<=\.)\s+|(?<=\n)[a-z]\)\s+|(?<=\n)\d+\)\s+', document.content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    # Calculate similarities
    all_texts = [query] + sentences
    embeddings = model.encode(all_texts)
    
    query_embedding = embeddings[0].reshape(1, -1)
    sentence_embeddings = embeddings[1:]
    similarities = cosine_similarity(query_embedding, sentence_embeddings)[0]
    
    normalized_similarities = ((similarities - similarities.min()) / 
                          (similarities.max() - similarities.min())) * 1
    
    # Sort by similarity
    results = list(zip(normalized_similarities, sentences))
    results.sort(reverse=True)
    results = results[:20]
    
    
    # Print results
    print(f"QUERY: {query}\n")
    for score, content in results:
        short_content = content[:150] + "..." if len(content) > 40 else content
        short_content = short_content.replace('\n', ' ')
        print(f"[{score:.3f}] - {short_content}")

if __name__ == "__main__":
    test_simple("docs/owu.pdf", "żebra")