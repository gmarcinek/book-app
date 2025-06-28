#!/usr/bin/env python3
"""
Test chunker standalone - uruchamiany z root
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from ner.semantic.chunker import TextChunker
from ner.domains import DomainFactory

def test_chunker(file_path: str):
    """Test hierarchical chunker on file"""
    
    # Load text from file
    try:
        text_path = Path(file_path)
        if not text_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        
        # Handle different file types
        if text_path.suffix.lower() == '.pdf':
            from ner.loaders import DocumentLoader
            loader = DocumentLoader()
            document = loader.load_document(str(text_path))
            text = document.content
            print(f"📄 Loaded PDF: {len(text):,} chars from {text_path.name}")
        else:
            text = text_path.read_text(encoding='utf-8')
            print(f"📄 Loaded text: {len(text):,} chars from {text_path.name}")
        
    except Exception as e:
        print(f"❌ Failed to load file: {e}")
        return
    
    # Setup chunker with OWU domain (hierarchical)
    try:
        domains = DomainFactory.use(["owu"])
        chunker = TextChunker(
            model_name="gpt-4.1-nano",
            domains=domains,
            chunking_mode="semantic",
            document_source=str(text_path)
        )
        
        print(f"🔧 Chunker initialized: {chunker.chunking_mode} mode")
        
    except Exception as e:
        print(f"❌ Failed to initialize chunker: {e}")
        return
    
    # Run chunking
    try:
        chunks = chunker.chunk_text(text)
        
        print(f"✅ Chunking complete: {len(chunks)} chunks created")
        
        # Show chunk info
        for i, chunk in enumerate(chunks):
            print(f"📝 Chunk {i}: {len(chunk.text):,} chars ({chunk.start}-{chunk.end})")
            preview = chunk.text[:100].replace('\n', ' ')
            print(f"   Preview: {preview}...")
            
        print(f"\n📁 Check logs: semantic_store/logs/document_chunks/")
        
    except Exception as e:
        print(f"❌ Chunking failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_chunker.py <file_path>")
        print("Example: python test_chunker.py docs/owu.pdf")
        print("         python test_chunker.py docs/kamienica.txt")
        sys.exit(1)
    
    file_path = sys.argv[1]
    test_chunker(file_path)