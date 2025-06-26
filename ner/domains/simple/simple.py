"""
Literary Domain Implementation - Clean and simplified
"""

from typing import List
from ..base import BaseNER, DomainConfig
from ...entity_config import DEFAULT_ENTITY_TYPES, DEFAULT_CONFIDENCE_THRESHOLDS

class SimpleNER(BaseNER):
    """Literary Domain with clean entity types and relationship extraction"""
    
    def __init__(self):
        config = DomainConfig(
            name="literary",
            entity_types=DEFAULT_ENTITY_TYPES,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLDS["entity_extraction"],
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        return DEFAULT_ENTITY_TYPES
    
    def get_meta_analysis_prompt(self, text: str, contextual_entities: List[dict] = None) -> str:
        """META-PROMPT: Clean and focused"""
        
        # Dodaj sekcję contextual entities jeśli są
        contextual_info = ""
        if contextual_entities:
            contextual_info = "\n\nKONTEKST Z POPRZEDNICH DOKUMENTÓW:\n"
            for entity_data in contextual_entities:
                name = entity_data.get('name', '')
                entity_id = entity_data.get('id', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')
                aliases = entity_data.get('aliases', [])[:3]  # Pierwsze 3 aliases
                
                aliases_str = ", ".join(aliases) if aliases else "brak"
                contextual_info += f"- id: {entity_id}, {name} ({entity_type}): {description}...\n"
                contextual_info += f"  Aliases: [{aliases_str}]\n"
            
            contextual_info += "\nUwzględnij te znane encje w analizie.\n"
        
        prompt = f"""Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT NER.
{contextual_info}
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

ZWRÓĆ GOTOWY PROMPT BEZ JSON WRAPPERA:"""
           
        return prompt
    
    def get_base_extraction_prompt(self, text: str) -> str:
        """FALLBACK: Simple and direct"""

        prompt = f"""Jesteś agentem AI wyspecjalizowanym w Named Entity Recognition.

TEKST: {text}

TYPY ENCJI:
{', '.join(DEFAULT_ENTITY_TYPES)}

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
            "description": "minimum 20 adekwatnych sółw, semantycznie użyteczny opis dla wyszukiwarki embedera, używaj wiedzy z tekstu i wiedzy ogólnej o świecie jednocześnie bądź precyzyjny jak matematyk opisujacy to co widzi",
            "aliases": ["Janek", "Johnny"],
            "confidence": 0.85
        }}
    ]
 ]
}}"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        """Custom extraction: Enhanced with relationship constraints"""

        aliases_info = ""
        if known_aliases:
            aliases_info = "\n\nZNANE ENCJE Z KONTEKSTEM (uwzględnij w ekstrakcji):\n"
            
            for entity_data in known_aliases:
                name = entity_data.get('name', '')
                entity_id = entity_data.get('id', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')
                aliases = entity_data.get('aliases', [])
                confidence = entity_data.get('confidence', 0.0)
                
                aliases_str = ", ".join(aliases) if aliases else "brak"
                aliases_info += f"- id: {entity_id}, '{name}' ({entity_type}): {description}\n"
                aliases_info += f"  Aliases: [{aliases_str}] | Confidence: {confidence:.2f}\n\n"
            
            aliases_info += "UWAGA: Jeśli znajdziesz te encje lub ich aliases, użyj głównej nazwy jako 'name', zachowaj lub poszerz description, dodaj aliases.\n"

        final_prompt = f"""Jesteś agentem AI wyspecjalizowanym w Named Entity Recognition.

INSTRUKCJE SPECYFICZNE DLA TEGO TEKSTU:
{custom_instructions}

{aliases_info}

TEKST DO ANALIZY:
{text}

DOSTĘPNE TYPY: {', '.join(DEFAULT_ENTITY_TYPES)}

ZASADY ENTITIES:
- Forma podstawowa (mianownik, liczba pojedyncza)
- Dodaj wszystkie warianty nazwy jako aliases
- Description minimum 20 słów, semantycznie użyteczny dla embedera

ZWRÓĆ TYLKO JSON:
{{
    "entities": [
        {{
            "name": "pełna nazwa z tekstu",
            "type": "TYP_Z_LISTY",
            "description": "semantycznie użyteczny opis dla wyszukiwarki embedera, minimalna długość to 20 słów, spróbuj powiedzieć i ekstrapolować jak najwiecej można prawdziwych stwierdzeń na temat encji",
            "aliases": ["ulica Krawiecka", "Krawiecka", ...],
            "confidence": 0.85
        }}
    ]
}}"""
        
        return final_prompt
    
    def should_use_cleaning(self) -> bool:
        return False