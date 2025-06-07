#!/usr/bin/env python3
"""
Knowledge Graph Agent - Main Orchestrator

Transforms text files into structured knowledge graphs through:
1. Entity extraction (distributed files)
2. Relationship resolution 
3. Graph aggregation (unified knowledge.json)

Usage:
    python agent/main.py <text_file> [options]
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# NER modules
from ner.knowledge import KnowledgeGraphBuilder
from ner.aggregator import GraphAggregator  
from ner.resolver import EntityResolver

# LLM support
from llm import Models

def setup_args() -> argparse.ArgumentParser:
    """Configure command line arguments"""
    parser = argparse.ArgumentParser(
        description="Knowledge Graph Agent - Extract entities and build knowledge graphs from text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python agent/main.py samples/kamienica.txt
    
    # Custom model and output
    python agent/main.py samples/story.txt --model qwen2.5-coder:32b --output story_knowledge.json
    
    # Existing entities directory (incremental)
    python agent/main.py samples/chapter2.txt --entities-dir existing_entities/
    
    # Debug mode with intermediate files
    python agent/main.py samples/test.txt --debug --keep-temp
        """
    )
    
    # Required arguments
    parser.add_argument(
        "text_file",
        help="Input text file to process"
    )
    
    # Model selection
    parser.add_argument(
        "--model", "-m",
        default=Models.QWEN_CODER,
        choices=[Models.QWEN_CODER, Models.QWEN_CODER_32B, Models.CODESTRAL],
        help="LLM model to use for entity extraction (default: %(default)s)"
    )
    
    # Output configuration
    parser.add_argument(
        "--output", "-o",
        default="knowledge.json",
        help="Output knowledge graph file (default: %(default)s)"
    )
    
    parser.add_argument(
        "--entities-dir",
        default="entities",
        help="Directory for entity files (default: %(default)s)"
    )
    
    # Processing options
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=2000,
        help="Text chunk size for processing (default: %(default)s)"
    )
    
    parser.add_argument(
        "--max-entities",
        type=int,
        default=10,
        help="Maximum entities per chunk (default: %(default)s)"
    )
    
    # Debug and development
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    
    parser.add_argument(
        "--keep-temp",
        action="store_true", 
        help="Keep intermediate entity files after aggregation"
    )
    
    parser.add_argument(
        "--skip-resolution",
        action="store_true",
        help="Skip entity resolution phase (faster, less accurate)"
    )
    
    parser.add_argument(
        "--memory-monitor",
        action="store_true",
        help="Enable memory usage monitoring"
    )
    
    return parser

def validate_inputs(args) -> None:
    """Validate input files and arguments"""
    # Check input file exists
    text_file = Path(args.text_file)
    if not text_file.exists():
        print(f"Error: Input file '{args.text_file}' not found")
        sys.exit(1)
    
    if not text_file.suffix.lower() in ['.txt', '.md']:
        print(f"Warning: File '{args.text_file}' may not be a text file")
    
    # Check file size
    file_size = text_file.stat().st_size
    if file_size > 10 * 1024 * 1024:  # 10MB
        print(f"Warning: Large file ({file_size // 1024 // 1024}MB) - processing may take time")
    
    # Validate chunk size
    if args.chunk_size < 500:
        print("Warning: Very small chunk size may result in poor entity extraction")
    
    if args.chunk_size > 5000:
        print("Warning: Very large chunk size may hit LLM token limits")

def load_text_file(file_path: str) -> str:
    """Load and validate text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            raise ValueError("File is empty")
        
        return text
    
    except UnicodeDecodeError:
        print(f"Error: Cannot decode file '{file_path}' as UTF-8")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)

def print_phase_header(phase: str, description: str) -> None:
    """Print formatted phase header"""
    print(f"\n{'='*60}")
    print(f"PHASE {phase}: {description}")
    print(f"{'='*60}")

def print_summary(result: Dict[str, Any], output_file: str, processing_time: float) -> None:
    """Print final processing summary"""
    print(f"\n{'='*60}")
    print("KNOWLEDGE GRAPH EXTRACTION COMPLETE")
    print(f"{'='*60}")
    
    print(f"📄 Source: {result.get('source', 'unknown')}")
    print(f"📊 Text length: {result.get('text_length', 0):,} characters")
    print(f"🧩 Chunks processed: {result.get('chunks_processed', 0)}")
    print(f"🏷️  Entities found: {result.get('entities_found', 0)}")
    print(f"💾 Entity files created: {result.get('entities_created', 0)}")
    print(f"🔗 Relationships resolved: {result.get('relationships_resolved', 0)}")
    print(f"📈 Graph nodes: {result.get('graph_nodes', 0)}")
    print(f"📊 Graph edges: {result.get('graph_edges', 0)}")
    print(f"⏱️  Processing time: {processing_time:.1f} seconds")
    print(f"📁 Output file: {output_file}")
    
    if result.get('entities_dir'):
        print(f"📂 Entities directory: {result['entities_dir']}")

def main():
    """Main orchestrator for knowledge graph extraction"""
    start_time = time.time()
    
    # Parse arguments
    parser = setup_args()
    args = parser.parse_args()
    
    # Validate inputs
    validate_inputs(args)
    
    # Load text
    print("Loading text file...")
    text = load_text_file(args.text_file)
    print(f"Loaded {len(text):,} characters from {args.text_file}")
    
    # Initialize result tracking
    result = {
        "source": args.text_file,
        "text_length": len(text),
        "model_used": args.model,
        "timestamp": datetime.now().isoformat(),
        "entities_dir": args.entities_dir
    }
    
    try:
        # =============================================
        # PHASE 1: Entity Extraction
        # =============================================
        print_phase_header("1", "Entity Extraction")
        
        builder = KnowledgeGraphBuilder(
            entities_dir=args.entities_dir,
            model=args.model,
            chunk_size=args.chunk_size,
            max_entities=args.max_entities,
            debug=args.debug,
            memory_monitor=args.memory_monitor
        )
        
        extraction_result = builder.process_text(text, args.text_file)
        result.update(extraction_result)
        
        print(f"✅ Entity extraction complete:")
        print(f"   - {extraction_result['chunks_processed']} chunks processed")
        print(f"   - {extraction_result['entities_found']} entities extracted")
        print(f"   - {extraction_result['entities_created']} entity files created")
        
        # =============================================
        # PHASE 2: Entity Resolution
        # =============================================
        if not args.skip_resolution:
            print_phase_header("2", "Entity Resolution & Linking")
            
            resolver = EntityResolver(
                entities_dir=args.entities_dir,
                debug=args.debug
            )
            
            resolution_result = resolver.resolve_all_entities()
            result.update(resolution_result)
            
            print(f"✅ Entity resolution complete:")
            print(f"   - {resolution_result.get('entities_processed', 0)} entities processed")
            print(f"   - {resolution_result.get('relationships_resolved', 0)} relationships resolved")
            print(f"   - {resolution_result.get('cross_references_created', 0)} cross-references created")
        else:
            print("⏭️  Skipping entity resolution phase")
            result['relationships_resolved'] = 0
        
        # =============================================
        # PHASE 3: Graph Aggregation
        # =============================================
        print_phase_header("3", "Graph Aggregation")
        
        aggregator = GraphAggregator(
            entities_dir=args.entities_dir,
            debug=args.debug
        )
        
        knowledge_graph = aggregator.create_unified_graph()
        aggregation_result = aggregator.save_graph(knowledge_graph, args.output)
        result.update(aggregation_result)
        
        print(f"✅ Graph aggregation complete:")
        print(f"   - {aggregation_result.get('graph_nodes', 0)} nodes in final graph")
        print(f"   - {aggregation_result.get('graph_edges', 0)} edges in final graph")
        print(f"   - Saved to: {args.output}")
        
        # =============================================
        # CLEANUP
        # =============================================
        if not args.keep_temp:
            print("\n🧹 Cleaning up intermediate files...")
            # Optional: remove individual entity files
            # aggregator.cleanup_temp_files()
            print("   (Entity files preserved for debugging)")
        
        # =============================================
        # SUMMARY
        # =============================================
        processing_time = time.time() - start_time
        print_summary(result, args.output, processing_time)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Processing interrupted by user")
        return 1
    
    except Exception as e:
        print(f"\n\n❌ Error during processing: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())