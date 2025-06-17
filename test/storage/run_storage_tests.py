#!/usr/bin/env python3
"""
test/run_storage_tests.py

Simple test runner for storage components
Run specific test suites or all tests with verbose output
"""

import sys
import subprocess
import argparse
from pathlib import Path

# Add root to path
sys.path.append(str(Path(__file__).parent.parent))

def run_tests(test_type=None, verbose=True):
    """Run storage tests with specified options"""
    
    test_dir = Path(__file__).parent
    
    if test_type == "basic":
        print("🧪 Running basic storage tests...")
        cmd = ["python", "-m", "pytest", "-v" if verbose else "-q", str(test_dir / "test_storage_basic.py")]
    
    elif test_type == "integration":
        print("🧪 Running integration tests...")
        cmd = ["python", "-m", "pytest", "-v" if verbose else "-q", str(test_dir / "test_storage_integration.py")]
    
    elif test_type == "embedder":
        print("🧪 Testing EntityEmbedder...")
        cmd = ["python", "-m", "pytest", "-v", str(test_dir / "test_storage_basic.py::TestEntityEmbedder")]
    
    elif test_type == "faiss":
        print("🧪 Testing FAISS Manager...")
        cmd = ["python", "-m", "pytest", "-v", str(test_dir / "test_storage_basic.py::TestFAISSManager")]
    
    elif test_type == "store":
        print("🧪 Testing SemanticStore...")
        cmd = ["python", "-m", "pytest", "-v", str(test_dir / "test_storage_basic.py::TestSemanticStore")]
    
    elif test_type == "workflow":
        print("🧪 Testing enhanced extraction workflow...")
        cmd = ["python", "-m", "pytest", "-v", str(test_dir / "test_storage_integration.py::TestSemanticStoreIntegration::test_enhanced_entity_extraction_workflow")]
    
    elif test_type == "performance":
        print("🧪 Running performance tests...")
        cmd = ["python", "-m", "pytest", "-v", str(test_dir / "test_storage_integration.py::TestStoragePerformance")]
    
    else:
        print("🧪 Running ALL storage tests...")
        cmd = ["python", "-m", "pytest", "-v" if verbose else "-q", 
               str(test_dir / "test_storage_basic.py"),
               str(test_dir / "test_storage_integration.py")]
    
    try:
        result = subprocess.run(cmd, cwd=test_dir.parent, capture_output=False)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Run storage tests")
    parser.add_argument("test_type", nargs="?", default="all",
                       choices=["all", "basic", "integration", "embedder", "faiss", "store", "workflow", "performance"],
                       help="Type of tests to run")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")
    
    args = parser.parse_args()
    
    print("🏗️ Storage Tests Runner")
    print("=" * 50)
    
    # Check dependencies
    try:
        import pytest
        import numpy as np
        import faiss
        import networkx as nx
        print("✅ All test dependencies available")
    except ImportError as e:
        print(f"❌ Missing test dependency: {e}")
        print("Install with: pip install pytest numpy faiss-cpu networkx")
        return False
    
    # Run tests
    success = run_tests(
        test_type=args.test_type if args.test_type != "all" else None,
        verbose=not args.quiet
    )
    
    if success:
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)