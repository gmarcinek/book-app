"""
TOC processing tasks
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from luigi_pipeline.tasks.base.structured_task import StructuredTask
from .toc_heuristic_detector import TOCHeuristicDetector
from .toc_llm_detector import TOCLLMDetector
from .toc_merger import TOCMerger
from .toc_orchestrator import TOCOrchestrator

__all__ = [
    'StructuredTask',
    'TOCHeuristicDetector',
    'TOCLLMDetector', 
    'TOCMerger',
    'TOCOrchestrator'
]