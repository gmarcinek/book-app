"""
NER (Named Entity Recognition) Module

Main API for knowledge graph extraction from text.
"""

from .loaders import load_text_file
from .extractor import KnowledgeGraphBuilder
from .resolver import EntityResolver
from .aggregation import GraphAggregator
from .utils import log_memory_usage

__version__ = "0.1.0"

def process_text_to_knowledge(
    text_file: str,
    model: str = "qwen2.5-coder", 
    output_file: str = "knowledge.json"
) -> dict:
    """
    Main function: Text -> Knowledge Graph
    
    Args:
        text_file: Input text file path
        model: LLM model for extraction
        output_file: Output JSON file
        
    Returns:
        Processing results and stats
    """
    print(f"🚀 Processing: {text_file}")
    
    # Phase 1: Load text
    text = load_text_file(text_file)
    print(f"📄 Loaded {len(text):,} characters")
    
    # Phase 2: Extract entities
    builder = KnowledgeGraphBuilder(model=model)
    extraction_result = builder.process_text(text, text_file)
    print(f"🏷️  Found {extraction_result['entities_found']} entities")
    
    # Phase 3: Resolve relationships
    resolver = EntityResolver()
    resolution_result = resolver.resolve_all_entities()
    print(f"🔗 Resolved {resolution_result.get('relationships_resolved', 0)} relationships")
    
    # Phase 4: Aggregate graph
    aggregator = GraphAggregator()
    knowledge_graph = aggregator.create_unified_graph()
    aggregator.save_graph(knowledge_graph, output_file)
    print(f"📊 Saved graph to: {output_file}")
    
    return {
        "output_file": output_file,
        "entities_count": knowledge_graph.get('stats', {}).get('nodes', 0),
        "relationships_count": knowledge_graph.get('stats', {}).get('edges', 0)
    }