"""
NER Pipeline - Streamlined text-to-knowledge processing with SemanticStore only
"""

from pathlib import Path
from typing import Dict, Any, Union, List
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from llm import Models
from .loaders import DocumentLoader, LoadedDocument
from .semantic import TextChunker
from .extractor import EntityExtractor
from .storage import SemanticStore
from .config import NERConfig, create_default_ner_config
from .domains import DomainFactory

class NERProcessingError(Exception):
    pass

def process_text_to_knowledge(
    input_source: Union[str, LoadedDocument],
    entities_dir: str = "semantic_store",
    model: str = None,
    config: NERConfig = None,
    output_aggregated: bool = True,
    domain_names: List[str] = None,
) -> Dict[str, Any]:
    """Process text to entities using SemanticStore with model-aware chunking"""
    try:
        # Use provided config or create default
        ner_config = config if config is not None else create_default_ner_config()
        
        # Use provided model or get default from config
        model = model or ner_config.get_default_model()
        
        # Load document
        document = DocumentLoader().load_document(input_source) if isinstance(input_source, str) else input_source
        print(f"📄 Loaded: {len(document.content):,} chars from {Path(document.source_file).name}")

        # Set up domains for chunker overhead calculation
        if domain_names is None:
            domain_names = ["auto"]
        
        # Create domains for overhead calculation (except for auto mode)
        domains_for_chunker = []
        if domain_names != ["auto"]:
            try:
                domains_for_chunker = DomainFactory.use(domain_names)
            except Exception as e:
                print(f"⚠️ Failed to load domains for chunker: {e}, using fallback")
                domains_for_chunker = []
        
        # Chunk with model-aware sizing and real overhead calculation
        chunker = TextChunker(
            config=ner_config,
            model_name=model,
            domains=domains_for_chunker,
            chunking_mode="semantic"
        )
        chunks = chunker.chunk_text(document.content)
        print(f"✂️ Created {len(chunks)} chunks (avg: {sum(len(c.text) for c in chunks)//len(chunks) if chunks else 0} chars)")
        
        # Create timestamp-based storage directory
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        storage_dir = entities_dir
        
        # Extract with SemanticStore
        extractor = EntityExtractor(
            model=model, 
            config=ner_config, 
            domain_names=domain_names,
            storage_dir=storage_dir,
            enable_semantic_store=True
        )
        
        entities = extractor.extract_entities(chunks)
        print(f"🎯 Extracted {len(entities)} entities")
        
        # Get final results from SemanticStore
        semantic_store = extractor.get_semantic_store()
        if not semantic_store:
            raise NERProcessingError("SemanticStore not available")
        
        # Generate aggregated output if requested
        aggregated_file = None
        if output_aggregated:
            timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = Path(document.source_file).stem[:20]
            aggregated_file = Path(storage_dir) / f"knowledge_graph_{safe_name}_{timestamp_file}.json"
            
            # Export knowledge graph
            graph_data = semantic_store.relationship_manager.export_graph_data()
            
            # Create comprehensive output
            output_data = {
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "source_file": document.source_file,
                    "model_used": model,
                    "domains_used": domain_names,
                    "entities_count": len(entities),
                    "chunks_processed": len(chunks)
                },
                "entities": [entity_dict for entity_dict in semantic_store.entities.values()],
                "chunks": [chunk_dict for chunk_dict in semantic_store.chunks.values()],
                "knowledge_graph": graph_data,
                "statistics": semantic_store.get_stats()
            }
            
            # Save to file
            aggregated_file.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(aggregated_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        # Get chunker stats for reporting
        chunk_stats = chunker.get_chunk_stats(chunks)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source_file": document.source_file,
            "model_used": model,
            "domains_used": domain_names,
            "entities_created": len(entities),
            "processing_stats": {
                "document_chars": len(document.content),
                "chunks_created": len(chunks),
                "avg_chunk_size": chunk_stats.get("avg_chunk_size", 0),
                "model_config": chunk_stats.get("model_config", {}),
                "extraction_stats": extractor.get_extraction_stats(),
                "semantic_store_stats": semantic_store.get_stats()
            },
            "output": {
                "storage_dir": storage_dir,
                "entities_count": len(semantic_store.entities),
                "chunks_count": len(semantic_store.chunks),
                "aggregated_graph": str(aggregated_file) if aggregated_file else None
            }
        }
    
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "model_used": model,
            "domains_used": domain_names,
            "source_file": getattr(input_source, 'source_file', str(input_source))
        }


def process_file(file_path: str, config: NERConfig = None, **kwargs) -> Dict[str, Any]:
    """Process single file with SemanticStore"""
    return process_text_to_knowledge(file_path, config=config, **kwargs)


def process_directory(directory_path: str, file_pattern: str = "*", config: NERConfig = None, **kwargs) -> Dict[str, Any]:
    """Process directory of files with SemanticStore"""
    directory = Path(directory_path)
    if not directory.exists():
        raise NERProcessingError(f"Directory not found: {directory_path}")
    
    files = [f for f in directory.glob(file_pattern) if f.suffix.lower() in {'.txt', '.md', '.pdf', '.docx', '.rtf'}]
    if not files:
        return {"status": "no_files", "message": f"No files found in {directory_path}"}
    
    print(f"📂 Processing {len(files)} files")
    results = []
    for file_path in files:
        print(f"🔄 Processing: {file_path.name}")
        try:
            results.append(process_text_to_knowledge(str(file_path), config=config, **kwargs))
        except Exception as e:
            results.append({"status": "error", "file": str(file_path), "error": str(e)})
    
    successful = sum(1 for r in results if r.get("status") == "success")
    return {
        "status": "batch_complete",
        "files_processed": len(results),
        "files_successful": successful,
        "files_failed": len(results) - successful,
        "results": results
    }