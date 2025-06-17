"""
API Server Launcher
"""

import uvicorn
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

def main():
    """Main entry point for poetry script"""
    print("🚀 Starting NER Knowledge API")
    print("📊 Server: http://localhost:8000")
    print("📖 Docs: http://localhost:8000/docs") 
    print("🔍 Interactive: http://localhost:8000/redoc")
    print()
    
    uvicorn.run(
        "api.server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=[str(Path(__file__).parent)]
    )

if __name__ == "__main__":
    main()