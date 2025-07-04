"""
TOC processing tasks
"""

from luigi_toc_pipeline.tasks.toc_heuristic_detector.toc_heuristic_detector import TOCHeuristicDetector
from .toc_fallback_llm_strategy.toc_fallback_llm_strategy import TOCFallbackLLMStrategy
from .toc_orchestrator import TOCOrchestrator

__all__ = [
    'TOCHeuristicDetector',
    'TOCFallbackLLMStrategy',
    'TOCHeuristicDetector',
    'TOCOrchestrator'
]