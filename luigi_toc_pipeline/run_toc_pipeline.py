from dotenv import load_dotenv
load_dotenv()

import luigi
import sys
from pathlib import Path

# Add parent directory for imports BEFORE importing TOCOrchestrator
sys.path.append(str(Path(__file__).parent.parent))

from tasks.toc_orchestrator import TOCOrchestrator

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_toc_pipeline.py <pdf_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    print(f"🚀 Starting TOC pipeline for: {Path(file_path).name}")
    
    # Run Luigi pipeline using luigi.build() with task instance
    result = luigi.build([
        TOCOrchestrator(file_path=file_path)
    ], local_scheduler=True)
    
    if result:
        print("✅ Pipeline completed successfully")
    else:
        print("❌ Pipeline failed")
        sys.exit(1)

if __name__ == "__main__":
    main()