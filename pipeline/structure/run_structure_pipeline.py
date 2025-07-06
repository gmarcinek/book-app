from dotenv import load_dotenv
load_dotenv()

import luigi
import sys
from pathlib import Path

# Add parent directories for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_structure_pipeline.py <pdf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    print(f"🚀 Starting structure pipeline for: {Path(file_path).name}")
    
    # Run Luigi pipeline - StructureSplitter will automatically require StructureDetector
    luigi.run([
        "StructureSplitter",
        "--file-path", file_path,
        "--local-scheduler"
    ])

if __name__ == "__main__":
    main()