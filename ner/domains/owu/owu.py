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

    def get_meta_analysis_prompt(self, text: str) -> str:
        """META-PROMPT: Skrócony o ~60% ale zachowuje kluczowe elementy"""
        return f"""Ekspert NER dla OWU. Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT.

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
      "name": "nazwa_podstawowa",
      "type": "TYP_Z_LISTY",
      "description": "pełny opis lub treść",
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
            aliases_lines = "\n".join(f"- {k}: {', '.join(v)}" for k, v in known_aliases.items())
            aliases_info = f"\nZnane aliasy: {aliases_lines}\n"

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
      "name": "nazwa_podstawowa",
      "type": "TYP_Z_LISTY", 
      "description": "pełny opis",
      "confidence": 0.X,
      "evidence": "art X, pkt Y + cytat",
      "aliases": ["alias1"]
    }}
  ]
}}"""

    def should_use_cleaning(self) -> bool:
        return False