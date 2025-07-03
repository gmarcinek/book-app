"""
financial Domain Implementation - Clean and simplified
"""

from typing import List
from ner.domains.base import BaseNER, DomainConfig
from ner.types import DEFAULT_ENTITY_TYPES, DEFAULT_CONFIDENCE_THRESHOLDS

class FinancialNER(BaseNER):
    """FinancialNER Domain with clean entity types and relationship extraction"""
    
    def __init__(self):
        config = DomainConfig(
            name="financial",
            entity_types=DEFAULT_ENTITY_TYPES,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLDS["entity_extraction"],
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        return DEFAULT_ENTITY_TYPES
    
    def get_meta_analysis_prompt(self, text: str, contextual_entities: List[dict] = None) -> str:
        """META-PROMPT: Clean and focused"""
        prompt = f"""Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT NER.
TEKST:
{text}

ANALIZA:
- Każda linia tekstu to encja skutecznego przejścia sportowej drogi wspinaczkowej. Drogę pokonał KAŻDORAZOWO Grzegorz Marcinek 

DOSTĘPNE TYPY ENCJI:
(LEAD)

ZWRÓĆ GOTOWY PROMPT BEZ JSON WRAPPERA:"""
           
        return prompt

    def get_base_extraction_prompt(self, text: str) -> str:
        """FALLBACK: Simple and direct"""

        prompt = f"""Jesteś agentem AI wyspecjalizowanym w Named Entity Recognition.

DANE:
{text}

DOSTĘPNE TYPY ENCJI:
- LEAD

ZWRÓĆ TYLKO JSON:
{{
    "entities": [
        {{
            "name": "Nazwa Drogi Wspinaczkowej",
            "type": "LEAD", 
            "description": "(wycena) - data przejscia - miejsce  - poprawiony stylistycznie opis przejścia występujący w treści",
            "grade": "wycena drogi wspinaczkowej w skali francuskiej",
            "date": "data przejscia",
            "confidence": 0.85
        }}
    ]
}}"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        """Ekstrakcja danych o przejściach dróg wspinaczkowych"""
        
        final_prompt = f"""{custom_instructions}

DANE - PRZEJŚCIA DRÓG WSPINACZKOWYCH:
{text}

INSTRUKCJE:
- Każda linia to jedno przejście drogi wspinaczkowej przez Grzegorza Marcinka
- Format linii: "Nazwa Drogi (wycena) - Lokalizacja - Komentarz - Styl przejścia - Data"
- Wyciągnij dla każdej linii wszystkie informacje

DOSTĘPNE TYPY ENCJI:
- LEAD (przejście drogi wspinaczkowej)

ZWRÓĆ TYLKO JSON:
{{
    "entities": [
        {{
            "name": "nazwa drogi z linii",
            "type": "LEAD",
            "description": "pełny komentarz/opis przejścia z linii", 
            "grade": "wycena w nawiasach (np. 6b+, 7a)",
            "location": "pełna lokalizacja (kraj, region, sektor)",
            "style": "styl przejścia (2nd Go, Hard, itp.)",
            "date": "data przejścia",
            "confidence": 0.9
        }}
    ]
}}

PRZYKŁAD dla linii "Rysa Kozickiego (6b+) - Poland, Jura Krakowsko - Częstochowska, Dolina Będkowska - Skurwiałe jurajskie gowno - 2nd Go - 12 Apr 2025":
{{
    "entities": [
        {{
            "name": "Rysa Kozickiego",
            "type": "LEAD",
            "description": "Skurwiałe jurajskie gowno",
            "grade": "6b+",
            "location": "Poland, Jura Krakowsko - Częstochowska, Dolina Będkowska", 
            "style": "2nd Go",
            "date": "12 Apr 2025",
            "confidence": 0.9
        }}
    ]
}}"""
        
        return final_prompt
    
    def should_use_cleaning(self) -> bool:
        return False