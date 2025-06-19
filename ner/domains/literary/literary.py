"""
Literary Domain Implementation - Clean and simplified
"""

from typing import List
from ..base import BaseNER, DomainConfig

class LiteraryNER(BaseNER):
   """Literary Domain with clean entity types and relationship extraction"""
   
   ENTITY_TYPES = [
       "CHARACTER",      # Playable character, NPC, człowiek z imienia, "jakiś typ", niedźwiedź w lesie
       "EMOTIONAL_STATE", # Stan emocjonalny wyrażony w tekście lub ekstrapolowany  
       "LOCATION",       # Miejsce gdzie podmiot jest i operuje, nie tylko wspomina
       "OBJECT",         # Istotne przedmioty: narzędzia, meble, coś do dotknięcia
       "EVENT",          # Wydarzenie z akcją i zmianą: wejście mamy, zatrzymanie zegara
       "DIALOG"          # Wymiana zdań, monolog, dialog wewnętrzny
   ]
   
   RELATIONSHIP_PATTERNS = [
       "IS_IN",          # CHARACTER/OBJECT IS_IN LOCATION
       "HAS",            # CHARACTER HAS OBJECT/EMOTIONAL_STATE
       "OWNS",           # CHARACTER OWNS OBJECT
       "IS",             # CHARACTER IS CHARACTER (rodzic/dziecko/małżonek)
       "PERFORMS",       # CHARACTER PERFORMS EVENT
       "PARTICIPATES",   # CHARACTER PARTICIPATES EVENT/DIALOG
       "LIVES_IN",       # CHARACTER LIVES_IN LOCATION
       "BEFORE",         # EVENT BEFORE EVENT
       "AFTER",          # EVENT AFTER EVENT
       "WITH"            # CHARACTER WITH CHARACTER (razem w scenie)
   ]
   
   def __init__(self):
       config = DomainConfig(
           name="literary",
           entity_types=self.ENTITY_TYPES,
           confidence_threshold=0.3,
       )
       super().__init__(config)
   
   def get_entity_types(self) -> List[str]:
       return self.ENTITY_TYPES
   
   def get_meta_analysis_prompt(self, text: str) -> str:
       """META-PROMPT: Clean and focused"""
       
       prompt = f"""Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT NER.

TEKST: {text}

ANALIZA:
- Bohaterowie/postacie (CHARACTER)
- Stany emocjonalne (EMOTIONAL_STATE)  
- Lokacje gdzie działają (LOCATION)
- Istotne przedmioty (OBJECT)
- Wydarzenia z akcją (EVENT)
- Dialogi/monologi (DIALOG)

RELACJE (tylko te patterns):
{', '.join(self.RELATIONSHIP_PATTERNS)}

PRZYKŁADY:
- "Jan IS_IN kuchnia"
- "matka HAS smutek" 
- "rozmowa AFTER obiad"

ZWRÓĆ GOTOWY PROMPT BEZ JSON WRAPPERA:"""
       
       return prompt
   
   def get_base_extraction_prompt(self, text: str) -> str:
       """FALLBACK: Simple and direct"""
       
       prompt = f"""Zidentyfikuj encje i relacje w tekście.

TEKST: {text}

TYPY ENCJI:
{', '.join(self.ENTITY_TYPES)}

PATTERNS:
{', '.join(self.RELATIONSHIP_PATTERNS)}

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
     "description": "semantycznie użyteczny opis dla wyszukiwarki embedera",
     "aliases": ["Janek", "Johnny"],
     "confidence": 0.85,
     "evidence": "entity_frame",
   }}
 ],
 "relationships": [
   {{
     "source": "Jan",
     "pattern": "IS_IN",
     "target": "dom",
     "evidence": "Jan jest w domu"
   }}
 ]
}}"""
       return prompt
   
   def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
       """Custom extraction: Enhanced with relationship constraints"""
       
       final_prompt = f"""{custom_instructions}

TEKST: {text}

TYPY: {', '.join(self.ENTITY_TYPES)}
PATTERNS: {', '.join(self.RELATIONSHIP_PATTERNS)}

ZASADY RELATIONSHIPS:
- source/target MUSZĄ być IDENTYCZNE z nazwami entities
- Jeśli entity nazywa się "Kamienica 59" to użyj "Kamienica 59", NIE "kamienica"
- Jeśli entity nazywa się "nasze mieszkanie" to użyj "nasze mieszkanie", NIE "mieszkanie"
- Sprawdź dwukrotnie że nazwy w relationships matchują entities

ZASADY ENTITIES:
- Dodaj generyczne formy jako aliases (np. "kamienica" dla "Kamienica 59")
- Dodaj wszystkie warianty nazwy z tekstu

JSON:
{{
 "entities": [
   {{
     "name": "pełna nazwa z tekstu",
     "type": "TYP",
     "description": "semantycznie użyteczny opis dla wyszukiwarki embedera",
     "aliases": ["krótsza forma", "generyczna nazwa", "inne warianty"],
     "confidence": 0.85,
     "evidence": "entity_frame",
   }}
 ],
 "relationships": [
   {{
     "source": "DOKŁADNA_NAZWA_Z_ENTITIES_WYŻEJ",
     "pattern": "PATTERN",
     "target": "DOKŁADNA_NAZWA_Z_ENTITIES_WYŻEJ",
     "evidence": "cytat z tekstu"
   }}
 ]
}}

ZWRÓĆ TYLKO JSON:"""
       
       return final_prompt
   
   def should_use_cleaning(self) -> bool:
       return False