"""
Simple test for Intelligent HierarchicalChunker
FILE: test_simple_hierarchical.py
"""

import json
from pathlib import Path
from datetime import datetime

from ner.loaders import DocumentLoader
from ner.semantic.hierarchical_strategy import HierarchicalChunker
from ner.semantic.base import SemanticChunkingConfig
from ner.config import ChunkingStrategy
from llm import LLMClient, Models

def test_simple():
    # Load document
    loader = DocumentLoader()
    document = loader.load_document("docs/owu.pdf")
    print(f"Loaded: {len(document.content):,} chars")
    
    # Config
    config = SemanticChunkingConfig(
        strategy=ChunkingStrategy.HIERARCHICAL,
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        threshold=0.15,
        percentile=95.0,
        min_chunk_size=100,
        max_chunk_size=100000
    )
    
    # Chunker + LLM
    chunker = HierarchicalChunker(config)
    llm_client = LLMClient(Models.GPT_4_1_NANO)
    chunker.set_llm_client(llm_client)
    
    # Output dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("tests") / f"simple_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Chunk
    print("Chunking...")
    chunks = chunker.chunk(document.content)
    print(f"Got {len(chunks)} chunks")
    
    # Save LLM response
    if hasattr(chunker, '_last_llm_response'):
        llm_file = output_dir / "llm_response.txt"
        with open(llm_file, "w", encoding="utf-8") as f:
            f.write(chunker._last_llm_response)
        print(f"Saved LLM response: {llm_file}")
    
    # Save chunks
    for i, chunk in enumerate(chunks):
        metadata = getattr(chunk, 'metadata', {})
        is_attachment = metadata.get('is_attachment', False)
        
        prefix = "attachment" if is_attachment else "chunk"
        chunk_file = output_dir / f"{prefix}_{i:02d}.txt"
        
        with open(chunk_file, "w", encoding="utf-8") as f:
            f.write(f"CHUNK {i} - {len(chunk.text)} chars\n")
            f.write(f"Type: {metadata.get('section_type', 'unknown')}\n")
            f.write("=" * 50 + "\n")
            f.write(chunk.text)
    
    print(f"Saved to: {output_dir}")
    
    # Quick stats
    attachments = sum(1 for c in chunks if getattr(c, 'metadata', {}).get('is_attachment'))
    avg_size = sum(len(c.text) for c in chunks) / len(chunks)
    print(f"Stats: {len(chunks)} chunks, {attachments} attachments, avg {avg_size:.0f} chars")

if __name__ == "__main__":
    test_simple()