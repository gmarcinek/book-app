"""
NER Pipeline - Simple text-to-knowledge processing
"""

from pathlib import Path
from typing import Dict, List, Any, Union
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from llm import Models
from .loaders import DocumentLoader, LoadedDocument
from .chunker import TextChunker
from .extractor import EntityExtractor
from .relationships import RelationshipExtractor
from .aggregator import GraphAggregator
from .utils import load_ner_config
from .llm_utils import call_llm_semantic_cleaning

class NERProcessingError(Exception):
    """Pipeline error"""
    pass


def process_text_to_knowledge(
    input_source: Union[str, LoadedDocument],
    entities_dir: str = "entities",
    model: str = Models.QWEN_CODER,
    config_path: str = "ner/ner_config.json",
    enable_relationships: bool = True,
    output_aggregated: bool = True,
    clean_semantically: bool = False
) -> Dict[str, Any]:
    """
    Process text to knowledge graph
    
    Args:
        input_source: File path or LoadedDocument
        entities_dir: Output directory for entity files
        model: LLM model to use
        config_path: Path to NER configuration
        enable_relationships: Extract relationships between entities
        output_aggregated: Create aggregated knowledge graph
    
    Returns:
        Processing results
    """
    try:
        # 1. Load document
        if isinstance(input_source, str):
            loader = DocumentLoader()
            document = loader.load_document(input_source)
        else:
            document = input_source
        
        print(f"Loaded: {len(document.content):,} chars from {Path(document.source_file).name}")
        if clean_semantically:
            print("🔍 Czyszczenie semantyczne tekstu...")
            cleaned = call_llm_semantic_cleaning(document.content, model)
            print(f"✅ Po czyszczeniu: {len(cleaned):,} znaków")
            save_cleaned_text(document, cleaned, entities_dir)
            document.content = cleaned

        # 2. Chunk text
        chunker = TextChunker(config_path)
        chunks = chunker.chunk_text(document.content)
        print(f"Created {len(chunks)} chunks")
        
        # 3. Extract entities
        extractor = EntityExtractor(model, config_path)
        entities = extractor.extract_entities(chunks)
        print(f"Extracted {len(entities)} entities")
        
        # 4. Process relationships (optional)
        if enable_relationships and entities:
            rel_extractor = RelationshipExtractor(model, config_path)
            entity_dicts = [
                {
                    'name': e.name,
                    'type': e.type,
                    'description': e.description,
                    'confidence': e.confidence
                }
                for e in entities
            ]
            relationships_data = rel_extractor.extract_relationships(entity_dicts, document.content)
        else:
            relationships_data = []
        
        # 5. Create entity files
        aggregator = GraphAggregator(entities_dir, config_path)
        aggregator.load_entity_index()
        
        created_ids = []
        for i, entity in enumerate(entities):
            entity_dict = {
                'name': entity.name,
                'type': entity.type,
                'description': entity.description,
                'confidence': entity.confidence,
                'source_info': {
                    'evidence': entity.context or '',
                    'chunk_references': [f"chunk_{entity.chunk_id}"] if entity.chunk_id is not None else [],
                    'source_document': document.source_file
                },
                'metadata': {
                    'model_used': model,
                    'extraction_method': 'llm'
                }
            }
            
            # Add relationships if available
            if enable_relationships and i < len(relationships_data):
                rel_data = relationships_data[i]
                entity_dict['relationships'] = {
                    'internal': rel_data.get('internal_relationships', []),
                    'external': rel_data.get('external_relationships', []),
                    'pending': rel_data.get('missing_entities', [])
                }
            
            # Create file
            chunk_refs = [f"chunk_{entity.chunk_id}"] if entity.chunk_id is not None else []
            entity_id = aggregator.create_entity_file(entity_dict, chunk_refs)
            if entity_id:
                created_ids.append(entity_id)
        
        print(f"Created {len(created_ids)} entity files")
        
        # 6. Create aggregated graph (optional)
        aggregation_result = None
        if output_aggregated:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = Path(document.source_file).stem[:20]
            output_file = f"knowledge_graph_{safe_name}_{timestamp}.json"
            aggregation_result = aggregator.create_aggregated_graph(output_file)
        
        # Return simple results
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "source_file": document.source_file,
            "entities_created": len(created_ids),
            "relationships_processed": enable_relationships,
            "output": {
                "entities_dir": entities_dir,
                "entity_ids": created_ids,
                "aggregated_graph": aggregation_result["output_file"] if aggregation_result else None
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
    """Process single file"""
    return process_text_to_knowledge(file_path, **kwargs)


def process_directory(directory_path: str, file_pattern: str = "*", **kwargs) -> Dict[str, Any]:
    """Process directory of files"""
    directory = Path(directory_path)
    if not directory.exists():
        raise NERProcessingError(f"Directory not found: {directory_path}")
    
    files = list(directory.glob(file_pattern))
    supported_exts = {'.txt', '.md', '.pdf', '.docx', '.rtf'}
    valid_files = [f for f in files if f.suffix.lower() in supported_exts]
    
    if not valid_files:
        return {"status": "no_files", "message": f"No files found in {directory_path}"}
    
    print(f"Processing {len(valid_files)} files")
    
    results = []
    for file_path in valid_files:
        print(f"Processing: {file_path.name}")
        try:
            result = process_text_to_knowledge(str(file_path), **kwargs)
            results.append(result)
        except Exception as e:
            results.append({
                "status": "error",
                "file": str(file_path),
                "error": str(e)
            })
    
    successful = sum(1 for r in results if r.get("status") == "success")
    
    return {
        "status": "batch_complete",
        "files_processed": len(results),
        "files_successful": successful,
        "files_failed": len(results) - successful,
        "results": results
    }

def save_cleaned_text(document, cleaned_text: str, entities_dir: str):
    out_path = Path(entities_dir) / f"{Path(document.source_file).stem}_cleaned.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cleaned_text, encoding="utf-8")
    print(f"📄 Zapisano oczyszczony tekst do: {out_path}")

def validate_configuration(config_path: str = "ner/ner_config.json") -> Dict[str, Any]:
    """Validate NER configuration"""
    try:
        config = load_ner_config(config_path)
        
        # Check LLM availability
        try:
            from llm import LLMClient
            llm_available = True
        except ImportError:
            llm_available = False
        
        return {
            "status": "valid",
            "config": config,
            "llm_available": llm_available
        }
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e)
        }