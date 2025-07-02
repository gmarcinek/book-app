from typing import List

from .financial import FinancialNER
from .owu import OwuNER
from .base import BaseNER
from .literary import LiteraryNER
from .simple import SimpleNER


class DomainFactory:
    
    @staticmethod
    def use(domain_names: List[str]) -> List[BaseNER]:
        domains = []
        
        for name in domain_names:
            if name == "literary":
                domains.append(LiteraryNER())
            elif name == "simple":
                domains.append(SimpleNER())
            elif name == "financial":
                domains.append(FinancialNER())
            elif name == "owu":
                domains.append(OwuNER())
            else:
                raise ValueError(f"Unknown domain: '{name}'. Available domains: {DomainFactory.get_available_domains()}")
        
        return domains
    
    @staticmethod
    def get_available_domains() -> List[str]:
        return ["literary", "simple", "owu", "financial"]