"""
NER Pipeline - Streamlined text-to-knowledge processing with model-aware chunking
"""

from pathlib import Path
from typing import Dict, Any, Union, List
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from llm import Models
from .loaders import DocumentLoader, LoadedDocument
from .chunker import TextChunker
from .extractor import EntityExtractor
from .aggregation import GraphAggregator
from .config import NERConfig, create_default_ner_config
from .domains import DomainFactory

class NERProcessingError(Exception):
    pass

def process_text_to_knowledge(
    input_source: Union[str, LoadedDocument],
    entities_dir: str = "entities",
    model: str = None,
    config: NERConfig = None,
    output_aggregated: bool = True,
    domain_names: List[str] = None,
) -> Dict[str, Any]:
    """Process text to entities using model-aware chunking and unified NER configuration"""
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
            domains=domains_for_chunker  # Pass domains for real overhead calculation
        )
        chunks = chunker.chunk_text(document.content)
        print(f"✂️ Created {len(chunks)} chunks (avg: {sum(len(c.text) for c in chunks)//len(chunks) if chunks else 0} chars)")
        
        # Init aggregator
        aggregator = GraphAggregator(entities_dir)
        aggregator.load_entity_index()

        # Extract with model-aware extractor
        extractor = EntityExtractor(model, ner_config, domain_names)
        extractor.aggregator = aggregator
        entities = extractor.extract_entities(chunks)
        print(f"🎯 Extracted {len(entities)} entities")
        
        # Save entities
        created_ids = []
        for entity in entities:
            entity_dict = {
                'name': entity.name,
                'type': entity.type,
                'description': entity.description,
                'confidence': entity.confidence,
                'aliases': entity.aliases,
                'source_info': {
                    'chunk_references': [f"chunk_{entity.chunk_id}"] if entity.chunk_id is not None else [],
                    'source_document': document.source_file
                },
                'metadata': {
                    'model_used': model, 
                    'extraction_method': 'llm',
                    'domain_used': getattr(entity, 'domain', 'unknown')
                }
            }

            chunk_refs = [f"chunk_{entity.chunk_id}"] if entity.chunk_id is not None else []
            entity_id = aggregator.create_entity_file(entity_dict, chunk_refs)
            if entity_id:
                created_ids.append(entity_id)
        
        print(f"💾 Created {len(created_ids)} entity files")
        
        # Get chunker stats for reporting
        chunk_stats = chunker.get_chunk_stats(chunks)
        
        # Aggregate
        aggregation_result = None
        if output_aggregated:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = Path(document.source_file).stem[:20]
            output_file = aggregator.entities_dir / f"knowledge_graph_{safe_name}_{timestamp}.json"
            aggregation_result = aggregator.create_aggregated_graph(output_file)
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source_file": document.source_file,
            "model_used": model,
            "domains_used": domain_names,
            "entities_created": len(created_ids),
            "processing_stats": {
                "document_chars": len(document.content),
                "chunks_created": len(chunks),
                "avg_chunk_size": chunk_stats.get("avg_chunk_size", 0),
                "model_config": chunk_stats.get("model_config", {}),
                "extraction_stats": extractor.get_extraction_stats() if hasattr(extractor, 'get_extraction_stats') else {}
            },
            "output": {
                "entities_dir": entities_dir,
                "entity_ids": created_ids,
                "aggregated_graph": str(output_file) if aggregation_result else None
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
    """Process single file with optional config override"""
    return process_text_to_knowledge(file_path, config=config, **kwargs)


def process_directory(directory_path: str, file_pattern: str = "*", config: NERConfig = None, **kwargs) -> Dict[str, Any]:
    """Process directory of files with unified config"""
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