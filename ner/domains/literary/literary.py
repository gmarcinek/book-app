"""
Literary Domain Implementation - 1:1 Legacy Prompts
"""

from typing import List, Dict, Any

from .literary_consts import LITERARY_PHENOMENON_STRUCTURE, LITERARY_PHENOMENON_TYPES, LITERARY_ENTITY_TYPES_FLAT
from ..base import BaseNER, DomainConfig


class LiteraryNER(BaseNER):
    """Literary Domain with exact legacy prompts"""
    
    def __init__(self):
        config = DomainConfig(
            name="literary",
            entity_types=LITERARY_ENTITY_TYPES_FLAT,
            confidence_threshold=0.3,
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        return LITERARY_ENTITY_TYPES_FLAT
    
    def get_meta_analysis_prompt(self, text: str) -> str:
        """META-PROMPT: 1:1 copy from legacy meta_analysis.py"""
        entity_types_str = ", ".join(LITERARY_ENTITY_TYPES_FLAT)
        
        prompt = f"""Jesteś ekspertem od Named Entity Recognition. Twoim zadaniem jest przeanalizować podany fragment tekstu i utworzyć SPERSONALIZOWANY PROMPT do ekstrakcji encji specjalnie dopasowany do tego konkretnego fragmentu.

FRAGMENT TEKSTU DO ANALIZY:
{text}

TWOJE ZADANIA:
1. PRZEANALIZUJ treść fragmentu pod kątem:
   - Głównych tematów i kontekstu (np. autobiografia, wspomnienia, tech, biznes, itp.)
   - Typów encji które prawdopodobnie wystąpią (osoby, miejsca, objekty, fenomeny psychiczne)
   - Specyficznych wzorców językowych (pierwszy/trzecia osoba, czas przeszły/teraźniejszy)
   - Poziomu szczegółowości i stylu narracji
   - Obecności stanów psychicznych, emocji, myśli
   - SCEN - spójnych fragmentów akcji z własną lokacją, postaciami i tematyką
   - DIALOGÓW - rozmów między postaciami jako obiektywnych faktów

2. ZIDENTYFIKUJ WYZWANIA dla ekstrakcji NER w tym fragmencie:
   - Niejednoznaczne nazwy (np. "dom" jako obiekt vs miejsce)
   - Metafory i abstrakcje
   - Fenomeny psychiczne wymagające specjalnej uwagi
   - Braki i nieobecności jako encje
   - Przejścia między scenami - zmiany kontekstu, lokacji, focus
   - Identyfikacja granic dialogów i uczestników rozmów

3. STWÓRZ SPERSONALIZOWANY PROMPT NER który:
    - Jest dopasowany do stylu i treści tego konkretnego fragmentu
    - Zawiera konkretne instrukcje dla znalezionych wzorców
    - Uwzględnia zidentyfikowane wyzwania
    - Zawiera odpowiednie przykłady z podobnego kontekstu
    - WYMAGAJ ALIASES dla wszystkich encji (warianty nazw, skróty, formy odmienione)
    - Instruuje jak identyfikować SCENY jako całościowe konteksty sytuacyjne
    - Instruuje jak identyfikować DIALOGI jako obiektywne fakty rozmów

DOSTĘPNE TYPY ENCJI: {entity_types_str}

WYMAGANIA DO CUSTOM PROMPTU:
- Zaczynaj od "Zidentyfikuj encje w poniższym fragmencie..."
- Uwzględnij specyfikę tego fragmentu w instrukcjach
- Dodaj konkretne przykłady z podobnego kontekstu
- Instrukcje dla SCEN: lokacja + postacie + tematyka + detale
- Instrukcje dla DIALOGÓW: uczestnicy + temat + kontekst rozmowy
- Zakończ wymaganiem formatu JSON

FORMAT ODPOWIEDZI - ZWRÓĆ JSON:
{{
  "prompt": "Twój spersonalizowany prompt do ekstrakcji NER tutaj..."
}}

WYGENERUJ TERAZ SPERSONALIZOWANY PROMPT:"""
        
        return prompt
    
    def get_base_extraction_prompt(self, text: str) -> str:
        """FALLBACK: 1:1 copy from legacy entity_extraction.py"""
        entity_types_str = ", ".join(LITERARY_ENTITY_TYPES_FLAT)
        phenomenon_examples = self._format_phenomenon_lines()
        
        prompt = f"""Zidentyfikuj konkretne encje w tekście według ścisłych kryteriów.

TEKST:
{text}

ZASADY EKSTRAKCJI:
1. Tylko encje jawnie obecne lub logicznie implikowane w tekście
2. Forma podstawowa (mianownik, liczba pojedyncza)
3. Uwzględnij BRAKI jako pełnoprawne encje
4. FENOMENY psychiczne ze strukturą "TYP: podtyp -> treść" jako typ "FENOMENON"
5. SCENY jako spójne fragmenty akcji z lokacją, postaciami i tematyką
6. DIALOGI jako rozmowy między postaciami (obiektywne fakty)

DOSTĘPNE TYPY ENCJI:
{entity_types_str}

SZACOWANIE CONFIDENCE - bądź realistyczny:
- 0.9+ = wyraźnie nazwane, jednoznaczne (Jan Kowalski, konkretne przedmioty)
- 0.7-0.9 = jasne z kontekstu, opisane szczegółowo
- 0.5-0.7 = domniemane, wywnioskowane pośrednio  
- 0.3-0.5 = abstrakcyjne, metaforyczne, fenomeny psychiczne
- 0.1-0.3 = bardzo niepewne, wymagające weryfikacji

STRUKTURA FENOMENÓW:
{phenomenon_examples}

ENCJE STRUKTURALNE:
- SCENA: spójny fragment akcji z określoną lokacją, uczestnikami i tematyką
  Przykład: "rozmowa_w_kuchni_o_planach" (lokacja: kuchnia, uczestnicy: narrator+matka, temat: planowanie)
- DIALOG: rozmowa między postaciami jako obiektywny fakt
  Przykład: "dialog_narratora_z_matką_o_jutrzejszych_planach"

INSTRUKCJE SPECJALNE:
- "brak piekarnika" → encja: "piekarnik" (typ: PRZEDMIOT) + "brak" (typ: BRAK)
- "MYŚL: retrospekcja -> nie miałem czasu" → encja: "myśl_retrospektywna_braku_czasu" (typ: FENOMENON)
- "zimny posiłek" → encja: "posiłek" (typ: JEDZENIE) z właściwością "zimny"
- ALIASES: dodaj wszystkie warianty nazwy z tekstu (np. "Jan Kowalski" → aliases: ["Jan", "Kowalski", "JK"])

PRZYKŁADY ALIASES:
- Osoba: "Jan Kowalski" → aliases: ["Jan", "Kowalski", "JK", "Janek"]
- Miejsce: "Warszawa" → aliases: ["stolica", "WWA", "miasto"]
- Organizacja: "Uniwersytet Warszawski" → aliases: ["UW", "uniwersytet", "uczelnia"]
- Przedmiot: "komputer" → aliases: ["laptop", "PC", "maszyna"]
- Scena: "rozmowa_w_ogrodzie" → aliases: ["scena_w_ogrodzie", "dialog_na_zewnątrz"]
- Dialog: "rozmowa_z_sąsiadem" → aliases: ["dialog_z_sąsiadem", "konwersacja"]

FORMAT - TYLKO JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu otaczającego",
      "confidence": 0.X, // 0.2=bardzo niepewne, 0.5=umiarkowane, 0.8=pewne, 0.95=oczywiste
      "aliases": ["wariant1", "wariant2", "skrót"],
      "phenomenon_structure": {{
        "main_type": "MYŚL",
        "subtype": "retrospekcja", 
      }} // tylko dla typu FENOMENON
    }}
  ]
}}
JSON:"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
        """Custom extraction: 1:1 copy from legacy custom_extraction.py"""
        entity_types_str = ", ".join(LITERARY_ENTITY_TYPES_FLAT)
        
        final_prompt = f"""{custom_instructions}

TEKST DO ANALIZY:
{text}

DOSTĘPNE TYPY ENCJI (użyj tylko z tej listy):
{entity_types_str}

WYMAGANY FORMAT JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu",
      "confidence": 0.85,
      "aliases": ["wariant1", "wariant2", "skrót"],
      "phenomenon_structure": {{
        "main_type": "MYŚL",
        "subtype": "retrospekcja", 
        "content": "szczegóły fenomenu"
      }} // tylko dla typu FENOMENON
    }}
  ]
}}

WYKONAJ EKSTRAKCJĘ - ZWRÓĆ TYLKO JSON:"""
        
        return final_prompt
    
    def should_use_cleaning(self) -> bool:
        return False
    
    def get_cleaning_prompt(self, text: str) -> str:
        """Semantic cleaning: 1:1 copy from legacy semantic_cleaning.py"""
        phenomenon_examples = self._format_phenomenon_lines()
        
        prompt = f"""Przekształć poniższy fragment wspomnieniowego tekstu autobiograficznego
w sformalizowaną scenę nadającą się do ekstrakcji encji i fenomenów.

TEKST DO ANALIZY:
{text}

ZASADY PRZETWARZANIA:
1. bądź wnikliwy
2. Zachowaj konkretne obiekty, miejsca, osoby, wydarzenia, BRAKI, myśli i stany psychiczne
3. Zidentyfikuj fenomeny psychiczne i oznacz je strukturalnie:
{phenomenon_examples}
4. Używaj formatu: TYP_FENOMENU: podtyp -> konkretna treść
5. Każde oznaczenie fenomenu jako osobne zdanie
6. Język neutralny, bez metafor i poetyckości
7. Nie dodawaj faktów - tylko parafrazuj istniejące
8. Czas bezczasowy (prezentacyjny) zamiast przeszłego

FORMAT: czysty tekst z oznaczeniami fenomenów

PRZYKŁAD TRANSFORMACJI:
Input: "Nie miałem piekarnika. Zresztą i tak nie miałbym czasu. Zjadłem coś na zimno."
Output: Brak piekarnika w mieszkaniu. MYŚL: retrospekcja -> wtedy nie miałem czasu na gotowanie. Zjedzenie zimnego posiłku zamiast gotowania.

TWOJA TRANSFORMACJA:"""
        return prompt
    
    def _format_phenomenon_lines(self):
        """Format structured phenomenon types for prompt - legacy format_phenomenon_lines()"""
        lines = [
            f"FORMATY FENOMENÓW:",
            f"- Bez podmiotu: {LITERARY_PHENOMENON_STRUCTURE['format']}",
            f"- Z podmiotem: {LITERARY_PHENOMENON_STRUCTURE['format_with_subject']}",
            "",
            "PRZYKŁADY Z PODMIOTAMI:",
            "- MYŚL: retrospekcja -> [narrator] nie miałem wtedy czasu na gotowanie",
            "- EMOCJA: podstawowa -> [mieszkańcy] cieszenie się z prądu", 
            "- KOMPENSACJA: -> [narrator] zjedzenie tortu w cukierni",
            "",
            "ROZPOZNAWANIE PODMIOTÓW Z TEKSTU:",
            "- 'ja', 'nie mam', 'myślę' → [narrator]",
            "- 'my', 'mamy', 'cieszmy się' → [mieszkańcy]", 
            "- konkretne imiona/role → [imię/rola]",
            "- gdy nieznany podmiot → brak nawiasów lub [narrator]",
            "",
            "DOSTĘPNE TYPY I PODTYPY:"
        ]
        
        for category, phenomena in list(LITERARY_PHENOMENON_TYPES.items())[:2]:  # Limit for prompt
            lines.append(f"• {category.upper()}:")
            for phenom_type, subtypes in phenomena.items():
                subtypes_str = ", ".join(subtypes[:3])  # Limit subtypes
                lines.append(f"  - {phenom_type}: {subtypes_str}")
        
        return "\n".join(lines)