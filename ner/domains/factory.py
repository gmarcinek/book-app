from typing import List
from .base import BaseNER
from .literary import LiteraryNER
from .liric import LiricNER
from .simple import SimpleNER
from .owu import OWUNER


class DomainFactory:
    
    @staticmethod
    def use(domain_names: List[str]) -> List[BaseNER]:
        domains = []
        
        for name in domain_names:
            if name == "literary":
                domains.append(LiteraryNER())
            elif name == "liric":
                domains.append(LiricNER())
            elif name == "simple":
                domains.append(SimpleNER())
            elif name == "owu":
                domains.append(OWUNER())
            else:
                raise ValueError(f"Unknown domain: '{name}'. Available domains: {DomainFactory.get_available_domains()}")
        
        return domains
    
    @staticmethod
    def get_available_domains() -> List[str]:
        return ["literary", "liric", "simple", "owu"]