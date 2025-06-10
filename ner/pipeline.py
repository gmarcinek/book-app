"""
NER Pipeline - Skompresowany text-to-knowledge processing
"""

from pathlib import Path
from typing import Dict, Any, Union
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from llm import Models
from .loaders import DocumentLoader, LoadedDocument
from .chunker import TextChunker
from .extractor import EntityExtractor
from .aggregation import GraphAggregator

class NERProcessingError(Exception):
    pass

def process_text_to_knowledge(
    input_source: Union[str, LoadedDocument],
    entities_dir: str = "entities",
    model: str = Models.QWEN_CODER,
    config_path: str = "ner/ner_config.json",
    output_aggregated: bool = True,
) -> Dict[str, Any]:
    """Process text to entities"""
    try:
        # Load
        document = DocumentLoader().load_document(input_source) if isinstance(input_source, str) else input_source
        print(f"Loaded: {len(document.content):,} chars from {Path(document.source_file).name}")

        # Chunk
        chunks = TextChunker(config_path).chunk_text(document.content)
        print(f"Created {len(chunks)} chunks")
        
        # Init aggregator
        aggregator = GraphAggregator(entities_dir, config_path)
        aggregator.load_entity_index()

        # Extract
        extractor = EntityExtractor(model, config_path)
        extractor.aggregator = aggregator
        entities = extractor.extract_entities(chunks)
        print(f"Extracted {len(entities)} entities")
        
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
                    'evidence': entity.context or '',
                    'chunk_references': [f"chunk_{entity.chunk_id}"] if entity.chunk_id is not None else [],
                    'source_document': document.source_file
                },
                'metadata': {'model_used': model, 'extraction_method': 'llm'}
            }

            chunk_refs = [f"chunk_{entity.chunk_id}"] if entity.chunk_id is not None else []
            entity_id = aggregator.create_entity_file(entity_dict, chunk_refs)
            if entity_id:
                created_ids.append(entity_id)
        
        print(f"Created {len(created_ids)} entity files")
        
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
            "entities_created": len(created_ids),
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
            "source_file": getattr(input_source, 'source_file', str(input_source))
        }


def process_file(file_path: str, **kwargs) -> Dict[str, Any]:
    return process_text_to_knowledge(file_path, **kwargs)

def process_directory(directory_path: str, file_pattern: str = "*", **kwargs) -> Dict[str, Any]:
    directory = Path(directory_path)
    if not directory.exists():
        raise NERProcessingError(f"Directory not found: {directory_path}")
    
    files = [f for f in directory.glob(file_pattern) if f.suffix.lower() in {'.txt', '.md', '.pdf', '.docx', '.rtf'}]
    if not files:
        return {"status": "no_files", "message": f"No files found in {directory_path}"}
    
    print(f"Processing {len(files)} files")
    results = []
    for file_path in files:
        print(f"Processing: {file_path.name}")
        try:
            results.append(process_text_to_knowledge(str(file_path), **kwargs))
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

def _save_cleaned_text(document, entities_dir: str):
    out_path = Path(entities_dir) / f"{Path(document.source_file).stem}_cleaned.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(document.content, encoding="utf-8")
    print(f"📄 Zapisano oczyszczony tekst do: {out_path}")

def validate_configuration(config_path: str = "ner/ner_config.json") -> Dict[str, Any]:
    try:
        from .utils import load_ner_config
        config = load_ner_config(config_path)
        try:
            from llm import LLMClient
            llm_available = True
        except ImportError:
            llm_available = False
        return {"status": "valid", "config": config, "llm_available": llm_available}
    except Exception as e:
        return {"status": "invalid", "error": str(e)}