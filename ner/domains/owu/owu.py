from typing import List
from ..base import BaseNER, DomainConfig
from .owu_consts import OWU_ENTITY_TYPES, format_owu_entity_types

class OWUNER(BaseNER):
    def __init__(self):
        config = DomainConfig(
            name="owu",
            entity_types=OWU_ENTITY_TYPES,
            confidence_threshold=0.4
        )
        super().__init__(config)

    def get_entity_types(self) -> List[str]:
        return OWU_ENTITY_TYPES

    def extract_definitions_only(self, text: str) -> str:
        """Specjalna metoda do ekstrakcji tylko definicji z sekcji DEFINICJE."""
        return f"""Jesteś ekspertem NER specjalizującym się w ekstrakcji DEFINICJI z tekstów OWU.

ZADANIE: Znajdź wszystkie zdefiniowane terminy i ich definicje w poniższym tekście.

TEKST:
{text}

PRIORYTET: DEFINICJE
- Szukaj wzorców: "oznacza", "rozumie się", "przez ... rozumie się"
- Każdy zdefiniowany termin to encja typu TERMIN_ZDEFINIOWANY
- Definicja to opis kontekstowy encji

DODATKOWE TYPY ENCJI (poza definicjami):
{format_owu_entity_types()}

ZASADY:
1. GŁÓWNY PRIORYTET: definicje terminów
2. Forma podstawowa terminów
3. Pełny opis definicji w "description"
4. Wysoką pewność (0.8+) dla jasnych definicji

FORMAT JSON:
{{
  "entities": [
    {{
      "name": "termin_w_formie_podstawowej",
      "type": "TERMIN_ZDEFINIOWANY",
      "description": "pełna definicja z tekstu",
      "confidence": 0.X,
      "evidence": "DOKŁADNA LOKALIZACJA w tekście (np. 'rozdz 1, art 9, p 13') + krótki cytat",
      "aliases": ["możliwe inne nazwy"]
    }}
  ]
}}"""

    def get_meta_analysis_prompt(self, text: str) -> str:
        entity_types_str = ", ".join(OWU_ENTITY_TYPES)
        return f"""Ekspert NER. Przeanalizuj tekst OWU i stwórz SPERSONALIZOWANY PROMPT ekstrakcji.

TEKST: {text}

ANALIZA:
- PRIORYTET: definicje terminów (TERMIN_ZDEFINIOWANY)
- Typy encji: {entity_types_str}
- Język formalno-prawny, sformalizowane definicje
- Wzorce definicji: "oznacza", "rozumie się", "przez ... rozumie się"
- Duża liczba nazw własnych i abstrakcji

PROMPT: Zacznij 'Jesteś ekspertem NER...' i skoncentruj się na:
1. GŁÓWNIE na definicjach terminów
2. Kontekście ubezpieczeniowym
3. Zachowaniu aliasów i opisu kontekstowego każdej encji"""

    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        entity_types_str = format_owu_entity_types()
        aliases_info = ""
        if known_aliases:
            aliases_lines = "\n".join(f"- {k}: {', '.join(v)}" for k, v in known_aliases.items())
            aliases_info = f"\n\nUWAGA: Znalezione aliasy:\n{aliases_lines}\n"

        return f"""Jesteś ekspertem NER specjalizującym się w tekstach OWU.

GŁÓWNY PRIORYTET: DEFINICJE TERMINÓW
- Szukaj wzorców definicji: "oznacza", "rozumie się", "przez ... rozumie się"
- Każdy zdefiniowany termin = TERMIN_ZDEFINIOWANY
- Wysoka pewność (0.8+) dla jasnych definicji

{custom_instructions}
{aliases_info}
DOSTĘPNE TYPY ENCJI:
{entity_types_str}

TEKST:
{text}

ZASADY:
1. **PRIORYTET: definicje terminów** (TERMIN_ZDEFINIOWANY)
2. Tylko jawne lub jednoznacznie implikowane encje
3. Forma podstawowa
4. Uwzględnij aliasy (np. "Ubezpieczyciel" = "Towarzystwo", "Firma")
5. **EVIDENCE: lokalizacja + cytat** - podaj adres paragrafu (np. "rozdz 1, art 9, p 13") + krótki cytat

FORMAT JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ", 
      "description": "opis 3-5 zdań (pełna definicja dla TERMIN_ZDEFINIOWANY)",
      "confidence": 0.X,
      "evidence": "LOKALIZACJA w dokumencie (rozdz X, art Y, p Z) + fragment tekstu uzasadniający istnienie tej encji",
      "aliases": ["alias1", "alias2"]
    }}
  ]
}}"""

    def get_base_extraction_prompt(self, text: str) -> str:
        entity_types_str = ", ".join(OWU_ENTITY_TYPES)
        return f"""Jesteś ekspertem NER. Wykonaj ekstrakcję encji OWU z poniższego tekstu.

**GŁÓWNY PRIORYTET: DEFINICJE TERMINÓW**
- Wzorce: "oznacza", "rozumie się", "przez ... rozumie się"
- Typ: TERMIN_ZDEFINIOWANY
- Wysoką pewność dla jasnych definicji

TEKST:
{text}

TYPY ENCJI:
{entity_types_str}

ZASADY:
- **PRIORYTET: definicje terminów**
- **PRIORYTET: wyłączenia z umowy**
- Tylko encje obecne lub implikowane  
- Wymagaj aliasów i kontekstu
- **EVIDENCE: adres paragrafu + cytat**
- JSON zgodnie ze wzorem z dokumentacji"""

    def is_definition_section(self, text: str) -> bool:
        """Sprawdza czy tekst to sekcja definicji."""
        definition_markers = [
            "definicje", "definicji", "pojęcia użyte", "znaczenie pojęć",
            "oznacza", "rozumie się", "przez", "należy przez to rozumieć"
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in definition_markers)

    def should_use_cleaning(self) -> bool:
        return False