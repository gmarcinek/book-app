"""
Domain factory - creates domain instances from names
"""

from typing import List
from .base import BaseNER
from .literary import LiteraryNER
from .liric import LiricNER


class DomainFactory:
    """Factory for creating domain instances from names"""
    
    @staticmethod
    def use(domain_names: List[str]) -> List[BaseNER]:
        """
        Create domain instances from list of domain names
        
        Args:
            domain_names: List of domain names (e.g. ["literary", "liric"])
            
        Returns:
            List of domain instances
            
        Raises:
            ValueError: If unknown domain name provided
        """
        domains = []
        
        for name in domain_names:
            if name == "literary":
                domains.append(LiteraryNER())
            elif name == "liric":
                domains.append(LiricNER())
            # elif name == "legal":
            #     domains.append(LegalNER())
            # elif name == "medical":
            #     domains.append(MedicalNER())
            else:
                raise ValueError(f"Unknown domain: '{name}'. Available domains: {DomainFactory.get_available_domains()}")
        
        return domains
    
    @staticmethod
    def get_available_domains() -> List[str]:
        """Get list of available domain names"""
        return ["literary", "liric"]