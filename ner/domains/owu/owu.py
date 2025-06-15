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
        return f"""Jesteś ekspertem NER specjalizującym się w analizie PRAWNYCH tekstów OWU (Ogólnych Warunków Ubezpieczenia).

ZADANIE: Przeprowadź kompleksową analizę prawną poniższego tekstu, identyfikując wszystkie istotne encje prawne.

TEKST:
{text}

PRIORYTETY EKSTRAKCJI (w kolejności):
1. **DEFINICJE PRAWNE** - Szukaj wzorców: "oznacza", "rozumie się", "przez ... rozumie się"
2. **ZOBOWIĄZANIA PRAWNE** - obowiązki stron, warunki umowne
3. **WYŁĄCZENIA I OGRANICZENIA** - przypadki wyłączenia odpowiedzialności
4. **PROCEDURY PRAWNE** - procesy, terminy, wymagania formalne
5. **PODMIOTY PRAWNE** - strony umowy, instytucje, organy

WSZYSTKIE DOSTĘPNE TYPY ENCJI:
{format_owu_entity_types()}

ZASADY ANALIZY PRAWNEJ:
1. Każdy zdefiniowany termin prawny = TERMIN_ZDEFINIOWANY (confidence 0.8+)
2. Identyfikuj zobowiązania prawne i ich zakres
3. Wychwytuj wyłączenia odpowiedzialności
4. Zwracaj uwagę na terminy procesowe i procedury
5. Forma podstawowa terminów prawnych
6. Pełny opis prawny w "description"

FORMAT JSON:
{{
  "entities": [
    {{
      "name": "termin_prawny_w_formie_podstawowej",
      "type": "ODPOWIEDNI_TYP_PRAWNY",
      "description": "szczegółowy opis prawny z kontekstem zastosowania",
      "confidence": 0.X,
      "evidence": "DOKŁADNA LOKALIZACJA prawna (np. 'rozdz 1, art 9, p 13') + cytat prawny",
      "aliases": ["alternatywne nazwy prawne"],
      "legal_context": "kontekst prawny i skutki"
    }}
  ]
}}"""

    def get_meta_analysis_prompt(self, text: str) -> str:
        entity_types_str = ", ".join(OWU_ENTITY_TYPES)
        return f"""Ekspert NER w analizie PRAWNYCH dokumentów ubezpieczeniowych. 
Przeanalizuj prawny tekst OWU i stwórz SPERSONALIZOWANY PROMPT prawnej ekstrakcji encji.

TEKST PRAWNY: {text}

ANALIZA PRAWNA:
- **CHARAKTER**: Dokument prawny - umowa ubezpieczenia
- **JĘZYK**: Formalno-prawny, terminologia specjalistyczna
- **STRUKTURA**: Hierarchiczna (rozdziały, artykuły, paragrafy)
- **KLUCZOWE ELEMENTY PRAWNE**:
  * Definicje terminów prawnych (TERMIN_ZDEFINIOWANY)
  * Zobowiązania stron (ZOBOWIAZANIE, WARUNEK)
  * Wyłączenia odpowiedzialności (WYLACZENIE)
  * Procedury prawne (PROCEDURA, TERMIN)
  * Podmioty prawne (PODMIOT, ORGAN)

DOSTĘPNE TYPY ENCJI PRAWNYCH: {entity_types_str}

PROMPT: Zacznij 'Jesteś ekspertem analizy PRAWNYCH tekstów ubezpieczeniowych...' i skoncentruj się na:
1. Identyfikacji wszystkich typów encji prawnych (nie tylko definicji)
2. Prawnych konsekwencjach i zobowiązaniach
3. Hierarchii prawnej dokumentu
4. Precyzyjnej lokalizacji prawnej każdej encji
5. Kontekście prawnym i skutkach dla stron umowy"""

    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        entity_types_str = format_owu_entity_types()
        aliases_info = ""
        if known_aliases:
            aliases_lines = "\n".join(f"- {k}: {', '.join(v)}" for k, v in known_aliases.items())
            aliases_info = f"\n\nUWAGA: Znane aliasy prawne:\n{aliases_lines}\n"

        return f"""Jesteś ekspertem NER specjalizującym się w analizie PRAWNYCH tekstów OWU (Ogólnych Warunków Ubezpieczenia).

DOKUMENT PRAWNY - ANALIZA KOMPLEKSOWA:

PRIORYTETY PRAWNE (zrównoważone):
1. **DEFINICJE PRAWNE** (30%) - Wzorce: "oznacza", "rozumie się", "przez ... rozumie się"
2. **ZOBOWIĄZANIA I WARUNKI** (25%) - obowiązki stron, warunki umowne
3. **WYŁĄCZENIA ODPOWIEDZIALNOŚCI** (20%) - ograniczenia, wyłączenia
4. **PROCEDURY I TERMINY** (15%) - procesy prawne, terminy
5. **PODMIOTY I ORGANY** (10%) - strony, instytucje, organy

{custom_instructions}
{aliases_info}

PRAWNE TYPY ENCJI:
{entity_types_str}

TEKST PRAWNY:
{text}

ZASADY ANALIZY PRAWNEJ:
1. **RÓWNOWAGA TYPÓW**: Nie skupiaj się tylko na definicjach - identyfikuj wszystkie typy encji prawnych
2. **ZOBOWIĄZANIA**: Wychwytuj obowiązki, warunki, ograniczenia
3. **WYŁĄCZENIA**: Szczególna uwaga na wyłączenia odpowiedzialności  
4. **PROCEDURY**: Terminy, procesy, wymagania formalne
5. **PODMIOTY**: Strony umowy, instytucje, organy nadzoru
6. **EVIDENCE**: Dokładna lokalizacja prawna (rozdz, art, par) + cytat
7. **KONTEKST PRAWNY**: Skutki dla stron umowy

FORMAT JSON:
{{
  "entities": [
    {{
      "name": "nazwa_prawna_w_formie_podstawowej",
      "type": "TYP_PRAWNY_Z_LISTY", 
      "description": "szczegółowy opis prawny z kontekstem i skutkami (3-5 zdań)",
      "confidence": 0.X,
      "evidence": "LOKALIZACJA prawna (rozdz X, art Y, p Z) + fragment tekstu prawnego",
      "aliases": ["alternatywne nazwy prawne"],
      "legal_context": "kontekst prawny i skutki dla stron"
    }}
  ]
}}"""

    def get_base_extraction_prompt(self, text: str) -> str:
        entity_types_str = ", ".join(OWU_ENTITY_TYPES)
        return f"""Jesteś ekspertem NER w analizie PRAWNYCH dokumentów ubezpieczeniowych.
Wykonaj kompleksową prawną analizę poniższego tekstu OWU.

**DOKUMENT PRAWNY - ZRÓWNOWAŻONA ANALIZA:**

PRIORYTETY PRAWNE:
1. **DEFINICJE PRAWNE** (30%) - "oznacza", "rozumie się", "przez ... rozumie się"
2. **ZOBOWIĄZANIA PRAWNE** (25%) - obowiązki, warunki, ograniczenia
3. **WYŁĄCZENIA ODPOWIEDZIALNOŚCI** (20%) - przypadki wyłączenia
4. **PROCEDURY PRAWNE** (15%) - terminy, procesy, wymagania
5. **PODMIOTY PRAWNE** (10%) - strony, instytucje, organy

TEKST PRAWNY:
{text}

TYPY ENCJI PRAWNYCH:
{entity_types_str}

ZASADY PRAWNEJ ANALIZY:
- **RÓWNOWAGA**: Nie tylko definicje - wszystkie typy encji prawnych
- **ZOBOWIĄZANIA**: Szczególna uwaga na obowiązki stron
- **WYŁĄCZENIA**: Kluczowe dla odpowiedzialności ubezpieczyciela
- **PROCEDURY**: Terminy i procesy prawne
- **EVIDENCE**: Dokładna lokalizacja prawna + cytat
- **KONTEKST**: Skutki prawne dla stron umowy
- JSON zgodnie ze wzorem prawnym z dokumentacji"""

    def is_definition_section(self, text: str) -> bool:
        """Sprawdza czy tekst to sekcja definicji."""
        definition_markers = [
            "definicje", "definicji", "pojęcia użyte", "znaczenie pojęć",
            "oznacza", "rozumie się", "przez", "należy przez to rozumieć"
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in definition_markers)

    def is_legal_obligations_section(self, text: str) -> bool:
        """Sprawdza czy tekst zawiera zobowiązania prawne."""
        obligation_markers = [
            "zobowiązuje się", "obowiązek", "zobowiązanie", "warunek",
            "musi", "powinien", "jest zobowiązany", "ma obowiązek"
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in obligation_markers)

    def is_exclusions_section(self, text: str) -> bool:
        """Sprawdza czy tekst zawiera wyłączenia odpowiedzialności."""
        exclusion_markers = [
            "wyłącza się", "nie obejmuje", "nie odpowiada", "z wyłączeniem",
            "nie podlega", "ograniczenie odpowiedzialności", "wyłączenie"
        ]
        text_lower = text.lower()
        return any(marker in text_lower for marker in exclusion_markers)

    def should_use_cleaning(self) -> bool:
        return False

    def get_section_specific_prompt(self, text: str) -> str:
        """Zwraca prompt dostosowany do typu sekcji prawnej."""
        if self.is_definition_section(text):
            return self.extract_definitions_only(text)
        elif self.is_legal_obligations_section(text):
            return self._get_obligations_prompt(text)
        elif self.is_exclusions_section(text):
            return self._get_exclusions_prompt(text)
        else:
            return self.get_base_extraction_prompt(text)

    def _get_obligations_prompt(self, text: str) -> str:
        """Prompt specjalnie dla sekcji zobowiązań prawnych."""
        return f"""Jesteś ekspertem prawnym analizującym ZOBOWIĄZANIA w tekście OWU.

PRIORYTET: ZOBOWIĄZANIA PRAWNE I WARUNKI

TEKST PRAWNY:
{text}

SZUKAJ SZCZEGÓLNIE:
- Zobowiązań ubezpieczyciela i ubezpieczonego
- Warunków umownych
- Obowiązków procesowych
- Ograniczeń czasowych

TYPY ENCJI:
{format_owu_entity_types()}

ZASADY:
1. **ZOBOWIĄZANIA** = wysoka pewność (0.8+)
2. **WARUNKI** = średnia pewność (0.6+)  
3. Precyzyjna lokalizacja prawna
4. Skutki prawne niespełnienia

FORMAT JSON jak w dokumentacji."""

    def _get_exclusions_prompt(self, text: str) -> str:
        """Prompt specjalnie dla sekcji wyłączeń odpowiedzialności."""
        return f"""Jesteś ekspertem prawnym analizującym WYŁĄCZENIA ODPOWIEDZIALNOŚCI w tekście OWU.

PRIORYTET: WYŁĄCZENIA I OGRANICZENIA ODPOWIEDZIALNOŚCI

TEKST PRAWNY:
{text}

SZUKAJ SZCZEGÓLNIE:
- Wyłączeń odpowiedzialności ubezpieczyciela
- Ograniczeń terytorialnych/czasowych
- Przypadków niepokrywanych przez ubezpieczenie
- Warunków utraty ochrony

TYPY ENCJI:
{format_owu_entity_types()}

ZASADY:
1. **WYŁĄCZENIA** = wysoka pewność (0.8+)
2. **OGRANICZENIA** = wysoka pewność (0.7+)
3. Precyzyjna lokalizacja prawna
4. Skutki prawne dla ubezpieczonego

FORMAT JSON jak w dokumentacji."""