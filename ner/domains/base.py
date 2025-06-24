"""
Base NER interface for domain-specific extraction strategies
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseNER(ABC):
    """Abstract base class for domain-specific NER implementations"""
    def __init__(self, config: DomainConfig):
        """Initialize domain with configuration"""
        self.config = config
        
    @abstractmethod
    def get_entity_types(self) -> List[str]:
        """Returns available entity types for this domain"""
        pass
    
    @abstractmethod
    def get_meta_analysis_prompt(self, text: str, contextual_entities: List[dict] = None) -> str:
        """
        Generates domain-specific meta-prompt that analyzes text 
        and creates custom extraction instructions
        
        Args:
            text: Text to analyze
            contextual_entities: Optional list of known entities from previous processing
            
        Returns:
            Domain-specific meta-analysis prompt
        """
        pass
    
    @abstractmethod
    def get_base_extraction_prompt(self, text: str) -> str:
        """
        Fallback extraction prompt when meta-analysis fails
        Domain-specific but doesn't use meta-prompt
        """
        pass
    
    @abstractmethod
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
        """
        Injects meta-prompt results into base extraction template
        This is the winning combo that gives 0.88+ confidence
        """
        pass
    
    @abstractmethod
    def should_use_cleaning(self) -> bool:
        return False  # DEFAULT = False dla wszystkich domen
    
    def get_cleaning_prompt(self, text: str) -> Optional[str]:
        """
        Optional semantic cleaning prompt - only if should_use_cleaning() == True
        Default implementation returns None
        """
        return None
    
    # Utility methods that can be overridden
    def format_entity_types(self) -> str:
        """Format entity types for prompts - can be customized per domain"""
        return ", ".join(self.get_entity_types())
    
    def get_confidence_threshold(self, entity_type: str = None) -> float:
        """Minimum confidence threshold for this domain - can be customized"""
        return 0.5


class DomainConfig:
    """Configuration for domain-specific NER behavior"""
    
    def __init__(self, 
                 name: str,
                 entity_types: List[str],
                 use_cleaning: bool = False,
                 confidence_threshold: float = 0.5,
                 custom_params: Optional[dict] = None):
        self.name = name
        self.entity_types = entity_types
        self.use_cleaning = use_cleaning
        self.confidence_threshold = confidence_threshold
        self.custom_params = custom_params or {}
