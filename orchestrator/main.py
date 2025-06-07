"""
Book Agent - Main Entry Point
NER-powered knowledge graph builder from documents

Usage:
    python main.py <file_path> [options]
    python main.py --help
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any

# Import NER module (relative path from orchestrator/)
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from ner import process_text_to_knowledge, process_file, process_directory, NERProcessingError
from llm import Models


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="Book Agent - Build knowledge graphs from documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py document.pdf
    python main.py folder/ --batch --model claude-4-sonnet
    python main.py text.txt --no-relationships --entities-dir my_entities
    python main.py book.docx --model qwen2.5-coder:32b --verbose
        """
    )
    
    # Positional argument
    parser.add_argument(
        "input",
        help="File path or directory to process"
    )
    
    # Model selection
    parser.add_argument(
        "--model", "-m",
        choices=[
            Models.QWEN_CODER,
            Models.QWEN_CODER_32B, 
            Models.CODESTRAL,
            Models.CLAUDE_4_SONNET,
            Models.GPT_4O,
            Models.GPT_4O_MINI,
            Models.GPT_4_1_MINI
        ],
        default=Models.QWEN_CODER,
        help="LLM model to use (default: qwen2.5-coder)"
    )
    
    # Processing options
    parser.add_argument(
        "--entities-dir", "-e",
        default="entities",
        help="Directory to store entity files (default: entities)"
    )
    
    parser.add_argument(
        "--config",
        default="ner/ner_config.json",
        help="Path to NER config file (default: ner/ner_config.json)"
    )
    
    # Feature toggles
    parser.add_argument(
        "--no-relationships",
        action="store_true",
        help="Skip relationship extraction (faster processing)"
    )
    
    parser.add_argument(
        "--no-aggregation",
        action="store_true",
        help="Skip creating aggregated graph file"
    )
    
    # Batch processing
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process directory (input must be directory)"
    )
    
    parser.add_argument(
        "--pattern",
        default="*",
        help="File pattern for batch processing (default: *)"
    )
    
    # Output options
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with detailed stats"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
    "--clean",
        action="store_true",
        help="Enable semantic cleaning before chunking"
    )
    
    return parser


def validate_arguments(args) -> bool:
    """Validate command line arguments"""
    input_path = Path(args.input)
    
    # Check if input exists
    if not input_path.exists():
        print(f"❌ Error: Input path does not exist: {args.input}")
        return False
    
    # Validate batch mode
    if args.batch and not input_path.is_dir():
        print(f"❌ Error: --batch requires a directory, got file: {args.input}")
        return False
    
    if not args.batch and input_path.is_dir():
        print(f"❌ Error: Input is directory, use --batch flag: {args.input}")
        return False
    
    # Check config file
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"⚠️  Warning: Config file not found, using defaults: {args.config}")
    
    return True


def print_results(result: Dict[str, Any], args) -> None:
    """Print processing results based on verbosity level"""
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    
    if args.quiet:
        if result["status"] == "success":
            print(f"✅ Created {result.get('entities_created', 0)} entities")
        elif result.get("status") == "batch_complete":
            print(f"✅ Processed {result.get('files_successful', 0)}/{result.get('files_processed', 0)} files")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        return
    
    # Normal/verbose output
    if result["status"] == "success":
        print(f"\n🎉 Processing completed successfully!")
        
        # Single file results
        print(f"📄 Source: {Path(result.get('source_file', 'unknown')).name}")
        print(f"🔍 Entities created: {result.get('entities_created', 0)}")
        print(f"🔗 Relationships: {'enabled' if result.get('relationships_processed', False) else 'disabled'}")
        print(f"📁 Entities directory: {result.get('output', {}).get('entities_dir', 'entities')}")
        
        if result.get('output', {}).get('aggregated_graph'):
            print(f"📊 Aggregated graph: {result['output']['aggregated_graph']}")
        
        if args.verbose:
            print(f"📋 Entity IDs: {len(result.get('output', {}).get('entity_ids', []))} files")
    
    elif result.get("status") == "batch_complete":
        print(f"\n🎉 Batch processing completed!")
        print(f"📊 Files processed: {result.get('files_processed', 0)}")
        print(f"✅ Successful: {result.get('files_successful', 0)}")
        print(f"❌ Failed: {result.get('files_failed', 0)}")
        
        if args.verbose and result.get('files_failed', 0) > 0:
            print("\n❌ Failed files:")
            for file_result in result.get('results', []):
                if file_result.get('status') == 'error':
                    file_name = Path(file_result.get('file', 'unknown')).name
                    print(f"  • {file_name}: {file_result.get('error', 'unknown error')}")
    
    else:
        # Error results
        print(f"\n❌ Processing failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        if args.verbose:
            print(f"File: {result.get('source_file', 'unknown')}")
            print(f"Timestamp: {result.get('timestamp', 'unknown')}")


def main():
    """Main entry point"""
    parser = create_parser()
    
    # Handle no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Validate arguments
    if not validate_arguments(args):
        sys.exit(1)
    
    # Print startup info
    if not args.quiet:
        print("🚀 Book Agent - Knowledge Graph Builder")
        print(f"📝 Input: {args.input}")
        print(f"🤖 Model: {args.model}")
        if args.batch:
            print(f"📂 Batch mode: {args.pattern}")
        print()
    
    try:
        # Process based on mode
        if args.batch:
            # Batch processing
            result = process_directory(
                args.input,
                file_pattern=args.pattern,
                entities_dir=args.entities_dir,
                model=args.model,
                config_path=args.config,
                enable_relationships=not args.no_relationships,
                output_aggregated=not args.no_aggregation,
                clean_semantically=args.clean,
            )
        else:
            # Single file processing
            result = process_file(
                args.input,
                entities_dir=args.entities_dir,
                model=args.model,
                config_path=args.config,
                enable_relationships=not args.no_relationships,
                output_aggregated=not args.no_aggregation,
                clean_semantically=args.clean,
            )
        
        # Print results
        print_results(result, args)
        
        # Exit with appropriate code
        if result["status"] == "success":
            sys.exit(0)
        elif result.get("status") == "batch_complete":
            # Exit 0 if any files processed successfully
            sys.exit(0 if result.get("files_successful", 0) > 0 else 1)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(130)
    
    except NERProcessingError as e:
        print(f"\n❌ NER processing error: {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()