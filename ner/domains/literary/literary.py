"""
Literary Domain Implementation - Clean and simplified
"""

from typing import List
from ..base import BaseNER, DomainConfig
from ...entity_config import DEFAULT_ENTITY_TYPES, DEFAULT_RELATIONSHIP_PATTERNS

class LiteraryNER(BaseNER):
   """Literary Domain with clean entity types and relationship extraction"""
   
   def __init__(self):
       config = DomainConfig(
           name="literary",
           entity_types=DEFAULT_ENTITY_TYPES,
           confidence_threshold=0.3,
       )
       super().__init__(config)
   
   def get_entity_types(self) -> List[str]:
       return DEFAULT_ENTITY_TYPES
   
   def get_meta_analysis_prompt(self, text: str) -> str:
       """META-PROMPT: Clean and focused"""
       
       prompt = f"""Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT NER.

TEKST: {text}

ANALIZA:
- Bohaterowie/postacie (CHARACTER)
- Stany emocjonalne (EMOTIONAL_STATE)
- Stan fizyczne (PHISICAL_STATE)
- Sumaryczny opis encji nazwyający posiadane cechy (DESCRIPTION)
- Lokacje (LOCATION)
- Konkretne adresy (ADDRESS)
- Istotne przedmioty (OBJECT)
- Wydarzenia z akcją (EVENT)
- Dialogi/monologi (DIALOG)
- Narzędzia (TOOL)
- Wyzwania/kłopoty/problemy stojące przed bohaterami (PROBLEM)
- Idee, abstrakcyjne koncepcje (CONCEPT)
- Nazwane organizacje / Firmy (INSTITUTION)
- Określone daty / godziny(DATE)

RELACJE (tylko te patterns):
{', '.join(DEFAULT_RELATIONSHIP_PATTERNS)}

PRZYKŁADY:
- "Jan IS_IN kuchnia"
- "pies HAS smutek" 
- "rozmowa AFTER obiad"
- "mama IS_PARENT dziecko"

ZWRÓĆ GOTOWY PROMPT BEZ JSON WRAPPERA:"""
       
       return prompt
   
   def get_base_extraction_prompt(self, text: str) -> str:
       """FALLBACK: Simple and direct"""
       
       prompt = f"""Zidentyfikuj encje i relacje w tekście.

TEKST: {text}

TYPY ENCJI:
{', '.join(DEFAULT_ENTITY_TYPES)}

PATTERNS:
{', '.join(DEFAULT_RELATIONSHIP_PATTERNS)}

ZASADY:
- Forma podstawowa
- Tylko encje jawnie obecne
- Aliases: wszystkie warianty nazwy

JSON:
{{
 "entities": [
   {{
     "name": "Jan",
     "type": "CHARACTER", 
     "description": "minimum 20 adekwatnych sółw, semantycznie użyteczny opis dla wyszukiwarki embedera, używaj wiedzy z tekstu i wiedzy ogólnej o świecie",
     "aliases": ["Janek", "Johnny"],
     "confidence": 0.85
   }}
 ],
 "relationships": [
   {{
     "source": "Jan",
     "pattern": "IS_IN",
     "target": "dom"
   }}
 ]
}}"""
       return prompt
   
   def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
       """Custom extraction: Enhanced with relationship constraints"""
       
       final_prompt = f"""{custom_instructions}

TEKST: {text}

TYPY: {', '.join(DEFAULT_ENTITY_TYPES)}
PATTERNS: {', '.join(DEFAULT_RELATIONSHIP_PATTERNS)}

ZASADY RELATIONSHIPS:
- source/target MUSZĄ być IDENTYCZNE z nazwami entities
- Jeśli entity nazywa się "Bagna topiące" to użyj "Bagna topiące", NIE "Bagna"
- Jeśli entity nazywa się "nasze mieszkanie" to użyj "nasze mieszkanie", NIE "mieszkanie"
- Sprawdź dwukrotnie że nazwy w relationships matchują entities

ZASADY ENTITIES:
- Dodaj generyczne formy jako aliases (np. "szkoła" dla "podstawówka")
- Dodaj wszystkie warianty nazwy z tekstu

JSON:
{{
 "entities": [
   {{
     "name": "pełna nazwa z tekstu",
     "type": "TYP",
     "description": "semantycznie użyteczny opis dla wyszukiwarki embedera, minimalna długość to 20 słów, spróbuj powiedzieć i ekstrapolować jak najwiecej można prawdziwych stwierdzeń na temat encji",
     "aliases": ["ulica Krawiecka", "Krawiecka", ...],
     "confidence": 0.85
   }}
 ],
 "relationships": [
   {{
     "source": "DOKŁADNA_NAZWA_Z_ENTITIES_WYŻEJ",
     "pattern": "PATTERN",
     "target": "DOKŁADNA_NAZWA_Z_ENTITIES_WYŻEJ"
   }}
 ]
}}

ZWRÓĆ TYLKO JSON:"""
       
       return final_prompt
   
   def should_use_cleaning(self) -> bool:
       return False