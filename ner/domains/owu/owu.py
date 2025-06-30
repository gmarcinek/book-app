from typing import List

from .owu_consts import OWU_ENTITY_TYPES, format_owu_entity_types
from ...entity_config import DEFAULT_CONFIDENCE_THRESHOLDS
from ..base import BaseNER, DomainConfig

class OwuNER(BaseNER):
    def __init__(self):
        config = DomainConfig(
            name="owu",
            entity_types=OWU_ENTITY_TYPES,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLDS["entity_extraction"],
        )
        super().__init__(config)

    def get_entity_types(self) -> List[str]:
        return OWU_ENTITY_TYPES

    def get_meta_analysis_prompt(self, text: str, contextual_entities: List[dict] = None) -> str:
        """META-PROMPT: Skrócony o ~60% ale zachowuje kluczowe elementy"""
        
        # Dodaj sekcję contextual entities jeśli są (wzorowane na simple/literary)
        contextual_info = ""
        if contextual_entities:
            contextual_info = "\n\nKONTEKST Z POPRZEDNICH DOKUMENTÓW:\n"
            for entity_data in contextual_entities:
                name = entity_data.get('name', '')
                entity_id = entity_data.get('id', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')[:350]  # ← OGRANICZONE DO 350 ZNAKÓW
                aliases = entity_data.get('aliases', [])[:3]  # Pierwsze 3 aliases
                
                aliases_str = ", ".join(aliases) if aliases else "brak"
                contextual_info += f"- {entity_id} - {name} ({entity_type}): {description}...\n"
                contextual_info += f"  Aliases: [{aliases_str}]\n"
            
            contextual_info += "\nUwzględnij te znane encje w analizie OWU.\n"
        
        return f"""Ekspert NER dla OWU. Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT.
{contextual_info}
TEKST: {text}

ANALIZA:
- PRIORYTET 1: definicje terminów (wzorce: "oznacza", "rozumie się")
- PRIORYTET 2: wyłączenia z umowy (sekcje wyłączeń + listy punktów)
- Język formalno-prawny, precyzyjne definicje
- Struktury list: a), 1., -, • = osobne encje w wyłączeniach

DOSTĘPNE TYPY: {format_owu_entity_types()}

PROMPT: Zacznij "Zidentyfikuj encje OWU..." i uwzględnij:
1. Definicje terminów jako TERMIN_ZDEFINIOWANY
2. Każdy punkt listy wyłączeń jako WYŁĄCZENIE_Z_UMOWY
3. Kontekst ubezpieczeniowy + aliasy

JSON: {{"prompt": "Twój spersonalizowany prompt..."}}"""

    def get_base_extraction_prompt(self, text: str) -> str:
        """FALLBACK: Skrócony o ~50% z fokusem na wyłączenia"""
        return f"""Zidentyfikuj encje OWU w tekście. PRIORYTET: definicje i wyłączenia.

TEKST: {text}

**INSTRUKCJE SPECJALNE DLA WYŁĄCZEŃ:**
- W sekcjach "wyłączenia"/"nie obejmuje"/"odmowa" każdy punkt listy = osobna encja
- Formaty: a), b), 1., 2., -, •, lub inne - każdy punkt to WYŁĄCZENIE_Z_UMOWY
- Przykład: "a) choroby, b) wypadek" = 2 osobne encje wyłączeń

**PRIORYTET TYPÓW:**
1. TERMIN_ZDEFINIOWANY (wzorce: "oznacza", "rozumie się")
2. WYŁĄCZENIE_Z_UMOWY (listy + kontekst wyłączeń)
3. Inne typy OWU

TYPY: {format_owu_entity_types()}

ZASADY:
- Forma podstawowa, wysokie confidence dla definicji (0.8+)
- Każdy punkt listy wyłączeń = osobna encja
- EVIDENCE: lokalizacja + cytat (np. "art 9, pkt a")
- Aliases obowiązkowe

JSON:
{{
  "entities": [
    {{
      "name": "deskryptywna_nazwa_podstawowa",
      "type": "TYP_Z_LISTY",
      "description": "semantycznie użyteczny opis dla wyszukiwarki embedera, minimalna długość to 10 słów, spróbuj powiedzieć i ekstrapolować jak najwiecej można prawdziwych stwierdzeń na temat encji",
      "confidence": 0.X,
      "evidence": "lokalizacja + precyzyjny cytat",
      "aliases": ["alias1", "alias2"]
    }}
  ]
}}"""

    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        """CUSTOM: Skrócony z fokusem na wyłączenia"""
        aliases_info = ""
        if known_aliases:
            aliases_info = "\n\nZNANE ENCJE Z KONTEKSTEM (uwzględnij w ekstrakcji):\n"
            
            for entity_data in known_aliases:
                name = entity_data.get('name', '')
                entity_id = entity_data.get('id', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')[:350]  # ← OGRANICZONE DO 350 ZNAKÓW
                aliases = entity_data.get('aliases', [])
                confidence = entity_data.get('confidence', 0.0)
                
                aliases_str = ", ".join(aliases) if aliases else "brak"
                aliases_info += f"- {entity_id} - '{name}' ({entity_type}): {description}\n"
                aliases_info += f"  Aliases: [{aliases_str}] | Confidence: {confidence:.2f}\n\n"
            
            aliases_info += "UWAGA: Jeśli znajdziesz te encje lub ich aliases, użyj głównej nazwy jako 'name', zachowaj lub poszerz description, dodaj aliases.\n"

        return f"""{custom_instructions}

**WYŁĄCZENIA - INSTRUKCJA SPECJALNA:**
Każdy punkt w listach wyłączeń = osobna encja WYŁĄCZENIE_Z_UMOWY:
- a) choroba → encja: "wyłączenie_choroba"  
- b) wypadek → encja: "wyłączenie_wypadek"
- Format: a), 1., -, • - rozpoznaj wszystkie

{aliases_info}
TEKST: {text}

TYPY: {format_owu_entity_types()}

JSON (EVIDENCE obowiązkowy):
{{
  "entities": [
    {{
      "name": "deskryptywna_nazwa_podstawowa",
      "type": "TYP_Z_LISTY", 
      "description": "semantycznie użyteczny opis dla wyszukiwarki embedera, minimalna długość to 10 słów, spróbuj powiedzieć i ekstrapolować jak najwiecej można prawdziwych stwierdzeń na temat encji",
      "confidence": 0.X,
      "evidence": "art X, pkt Y + cytat",
      "aliases": ["alias1"]
    }}
  ]
}}"""

    def should_use_cleaning(self) -> bool:
        return False