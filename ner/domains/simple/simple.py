from typing import List
from ..base import BaseNER, DomainConfig
from .simple_consts import (
    SIMPLE_ENTITY_TYPES_FLAT, 
    format_simple_entity_types, 
    SIMPLE_EXAMPLES,
)

import logging
logger = logging.getLogger(__name__)

class SimpleNER(BaseNER):
    def __init__(self):
        config = DomainConfig(
            name="simple",
            entity_types=SIMPLE_ENTITY_TYPES_FLAT,
            confidence_threshold=0.3
        )
        super().__init__(config)

    def get_entity_types(self) -> List[str]:
        return SIMPLE_ENTITY_TYPES_FLAT

    def get_meta_analysis_prompt(self, text: str) -> str:
        """META-PROMPT: Skrócony dla simple domain"""
        entity_types_str = ", ".join(SIMPLE_ENTITY_TYPES_FLAT)

        prompt = f"""Ekspert NER. Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT ekstrakcji.

TEKST: {text}

ANALIZA:
- Typy encji: osoby, miejsca, przedmioty, wydarzenia, czas, koncepcje
- Wyzwania: aliasy osób/rzeczy, niejednoznaczne nazwy
- MIEJSCE vs PRZEDMIOT: można tam być vs można dotknąć

TYPY: {entity_types_str}

PROMPT: Zacznij "Jesteś ekspertem NER. Zidentyfikuj encje..."
- Dopasuj do fragmentu
- Wymagaj aliases
- Agreguj duplikaty
"""
        return prompt

    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        logger.info(f"🧠 USING -- INTELIGENT -- META NER")
        entity_types_str = format_simple_entity_types()

        aliases_info = ""
        if known_aliases:
            aliases_lines = "\n".join(f"- {k}: {', '.join(v)}" for k, v in known_aliases.items())
            aliases_info = f"\n\nUWAGA: Zidentyfikowano następujące aliasy w analizie kontekstowej:\n{aliases_lines}\n"

        return f"""Jesteś agentem ai wyspecjalizowanym w Named Entity Recognition
{custom_instructions}
{aliases_info}
DOSTĘPNE TYPY ENCJI:
{entity_types_str}

TEKST:
{text}

ZASADY EKSTRAKCJI:
1. Tylko encje jawnie obecne lub logicznie implikowane w tekście
2. Forma podstawowa (mianownik, liczba pojedyncza)

INSTRUKCJE SPECJALNE:
- ALIASES: dodaj wszystkie warianty nazwy z tekstu (np. \"Jan Kowalski\" → aliases: [\"Jan\", \"Kowalski\", \"JK\"])
- bądź realistyczny
- agreguj rozpoznane encje w jedną jeśli są swoimi aliasami

FORMAT - TYLKO JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu otaczającego",
      "confidence": 0.X,
      "evidence": "entity_frame",
      "aliases": ["wszystkie_wariany_nazwy_znalezionej_encji"]
    }}
  ]
}}
JSON:"""

    def get_base_extraction_prompt(self, text: str) -> str:
        logger.info(f"🟡 USING -- PSEUDO -- FALLBACK")
        entity_types_str = ", ".join(SIMPLE_ENTITY_TYPES_FLAT)

        prompt = f"""Jesteś ekspertem od Named Entity Recognition - Zidentyfikuj konkretne encje w tekście według ścisłych kryteriów.
TEKST:
{text}

ZASADY EKSTRAKCJI:
1. Tylko encje jawnie obecne lub logicznie implikowane w tekście
2. Forma podstawowa (mianownik, liczba pojedyncza)

DOSTĘPNE TYPY ENCJI:
{entity_types_str}

SZACOWANIE CONFIDENCE - bądź realistyczny:

INSTRUKCJE SPECJALNE:
- ALIASES: dodaj wszystkie warianty nazwy z tekstu (np. \"Jan Kowalski\" → aliases: [\"Jan\", \"Kowalski\", \"JK\"])

PRZYKŁADY ALIASES:
- Osoba: \"Jan Kowalski\" → aliases: [\"Jan\", \"Kowalski\", \"JK\", \"Janek\"]
- Miejsce: \"Warszawa\" → aliases: [\"stolica\", \"WWA\", \"miasto\"]
- Obiekt: \"komputer\" → aliases: [\"laptop\", \"PC\", \"maszyna\"]

FORMAT - TYLKO JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu otaczającego",
      "confidence": 0.X, // 0.2=bardzo niepewne, 0.5=umiarkowane, 0.8=pewne, 0.95=oczywiste
      "evidence": "entity_frame",
      "aliases": ["wariant1", "wariant2", ...]
    }}
  ]
}}
JSON:"""
        return prompt

    def should_use_cleaning(self) -> bool:
        return False

    def _format_examples(self) -> str:
        """Format examples for prompts"""
        return f"""PRZYKŁADY:
- OSOBY: {', '.join(SIMPLE_EXAMPLES['OSOBA'])}
- MIEJSCA: {', '.join(SIMPLE_EXAMPLES['MIEJSCE'])}
- OBIEKTY: {', '.join(SIMPLE_EXAMPLES['OBIEKT'])}"""
