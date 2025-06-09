"""
Literary domain NER implementation - migrated from existing working code
"""

from typing import List, Optional
from .base import BaseNER, DomainFactory


class LiteraryNER(BaseNER):
    """NER implementation specialized for literary texts and narratives"""
    
    def __init__(self):
        # Literary-specific entity types (from your consts.py)
        self._entity_types = [
            # Core universal types
            "OSOBA", "MIEJSCE", "ORGANIZACJA", "PRZEDMIOT", 
            "WYDARZENIE", "USŁUGA", "KONCEPCJA",
            # Literary structural types
            "SCENA", "DIALOG",
            # Literary psychological types
            "FENOMENON", "EMOCJA", "MYŚL",
            # Temporal
            "CZAS", "OKRES",
            # Abstract
            "WARTOŚĆ", "PROBLEM", "ROZWIĄZANIE", "CEL",
            # Physical
            "MATERIAŁ", "NARZĘDZIE", "BUDYNEK", "JEDZENIE",
            # Absence (literary concept)
            "BRAK", "NIEOBECNOŚĆ"
        ]
        
        # Literary phenomenon structure (from your consts.py)
        self._phenomenon_types = {
            "cognitive": {
                "MYŚL": ["retrospekcja", "analityczna", "obsesyjna"],
                "WSPOMNIENIE": ["autobiograficzne", "traumatyczne"],
                "ANALIZA": ["sytuacyjna", "krytyczna"]
            },
            "emotional": {
                "EMOCJA": ["podstawowa", "złożona"],
                "UCZUCIE": ["pozytywne", "negatywne"],
                "STRACH": ["konkretny", "egzystencjalny"]
            },
            "motivational": {
                "INTENCJA": ["świadoma", "nieświadoma"],
                "PRAGNIENIE": ["spełnione", "niespełnione"],
                "POTRZEBA": ["podstawowa", "psychologiczna"]
            }
        }
    
    def get_entity_types(self) -> List[str]:
        """Returns literary-specific entity types"""
        return self._entity_types.copy()
    
    def get_meta_analysis_prompt(self, text: str) -> str:
        """
        Literary meta-prompt - migrated from your meta_analysis.py
        Analyzes literary content and generates custom extraction instructions
        """
        entity_types_str = self.format_entity_types()
        
        prompt = f"""Jesteś ekspertem od Named Entity Recognition dla tekstów literackich i narracyjnych. Twoim zadaniem jest przeanalizować podany fragment tekstu i utworzyć SPERSONALIZOWANY PROMPT do ekstrakcji encji specjalnie dopasowany do tego konkretnego fragmentu literackiego.

FRAGMENT TEKSTU DO ANALIZY:
{text}

TWOJE ZADANIA:
1. PRZEANALIZUJ treść fragmentu pod kątem:
   - Głównych tematów i kontekstu literackiego (autobiografia, wspomnienia, narracja, dialog)
   - Typów encji charakterystycznych dla literatury (postacie, miejsca, obiekty, fenomeny psychiczne)
   - Specyficznych wzorców narracyjnych (pierwszy/trzecia osoba, czas, perspektywa)
   - Poziomu szczegółowości i stylu literackiego
   - Obecności stanów psychicznych, emocji, myśli, wspomnień
   - SCEN - spójnych fragmentów akcji z własną lokacją, postaciami i tematyką
   - DIALOGÓW - rozmów między postaciami jako obiektywnych faktów literackich
   - Struktur narracyjnych i technik literackich

2. ZIDENTYFIKUJ WYZWANIA dla ekstrakcji NER w tym fragmencie literackim:
   - Niejednoznaczne nazwy (np. "dom" jako obiekt vs miejsce w kontekście narracji)
   - Metafory i abstrakcje literackie
   - Fenomeny psychiczne postaci wymagające specjalnej uwagi
   - Braki i nieobecności jako elementy znaczące w narracji
   - Przejścia między scenami - zmiany kontekstu, lokacji, perspektywy narracyjnej
   - Identyfikacja granic dialogów i uczestników rozmów literackich
   - Elementy symboliczne i alegoryczne

3. STWÓRZ SPERSONALIZOWANY PROMPT NER który:
    - Jest dopasowany do stylu i treści tego konkretnego fragmentu literackiego
    - Zawiera konkretne instrukcje dla znalezionych wzorców narracyjnych
    - Uwzględnia zidentyfikowane wyzwania literackie
    - Zawiera odpowiednie przykłady z podobnego kontekstu literackiego
    - WYMAGAJ ALIASES dla wszystkich encji (warianty nazw, skróty, formy odmienione)
    - Instruuje jak identyfikować SCENY jako całościowe konteksty sytuacyjne w narracji
    - Instruuje jak identyfikować DIALOGI jako obiektywne fakty rozmów literackich
    - Uwzględnia fenomeny psychiczne charakterystyczne dla literatury

DOSTĘPNE TYPY ENCJI: {entity_types_str}

WYMAGANIA DO CUSTOM PROMPTU:
- Zaczynaj od "Zidentyfikuj encje w poniższym fragmencie literackim..."
- Uwzględnij specyfikę tego fragmentu w instrukcjach
- Dodaj konkretne przykłady z podobnego kontekstu literackiego
- Instrukcje dla SCEN: lokacja + postacie + tematyka + detale narracyjne
- Instrukcje dla DIALOGÓW: uczesznicy + temat + kontekst rozmowy + techniki literackie
- Instrukcje dla FENOMENÓW: typy psychologiczne + struktura + kontekst postaci
- Zakończ wymaganiem formatu JSON

FORMAT ODPOWIEDZI - ZWRÓĆ JSON:
{{
  "prompt": "Twój spersonalizowany prompt do ekstrakcji NER dla literatury tutaj..."
}}

WYGENERUJ TERAZ SPERSONALIZOWANY PROMPT LITERACKI:"""
        
        return prompt
    
    def get_base_extraction_prompt(self, text: str) -> str:
        """
        Literary fallback prompt - migrated from your entity_extraction.py
        Used when meta-analysis fails
        """
        entity_types_str = self.format_entity_types()
        phenomenon_examples = self._format_phenomenon_lines()
        
        prompt = f"""Zidentyfikuj konkretne encje w tekście literackim według ścisłych kryteriów narracyjnych.

TEKST LITERACKI:
{text}

ZASADY EKSTRAKCJI LITERACKIEJ:
1. Tylko encje jawnie obecne lub logicznie implikowane w narracji
2. Forma podstawowa (mianownik, liczba pojedyncza)
3. Uwzględnij BRAKI jako pełnoprawne encje narracyjne
4. FENOMENY psychiczne ze strukturą "TYP: podtyp -> treść" jako typ "FENOMENON"
5. SCENY jako spójne fragmenty akcji z lokacją, postaciami i tematyką literacką
6. DIALOGI jako rozmowy między postaciami (obiektywne fakty narracyjne)
7. Kontekst literacki - uwzględnij techniki narracyjne i styl

DOSTĘPNE TYPY ENCJI:
{entity_types_str}

SZACOWANIE CONFIDENCE - realistyczne dla literatury:
- 0.9+ = wyraźnie nazwane w narracji, jednoznaczne (postacie, miejsca)
- 0.7-0.9 = jasne z kontekstu literackiego, opisane szczegółowo
- 0.5-0.7 = domniemane, wywnioskowane z narracji pośrednio  
- 0.3-0.5 = abstrakcyjne, metaforyczne, fenomeny psychiczne postaci
- 0.1-0.3 = bardzo niepewne, wymagające weryfikacji literackiej

STRUKTURA FENOMENÓW LITERACKICH:
{phenomenon_examples}

ENCJE STRUKTURALNE W LITERATURZE:
- SCENA: spójny fragment akcji z określoną lokacją, uczestnikami i tematyką narracyjną
  Przykład: "rozmowa_w_kuchni_o_planach" (lokacja: kuchnia, uczestnicy: narrator+matka, temat: planowanie)
- DIALOG: rozmowa między postaciami jako obiektywny fakt literacki
  Przykład: "dialog_narratora_z_matką_o_jutrzejszych_planach"

INSTRUKCJE SPECJALNE DLA LITERATURY:
- "brak piekarnika" → encja: "piekarnik" (typ: PRZEDMIOT) + "brak" (typ: BRAK)
- "MYŚL: retrospekcja -> nie miałem czasu" → encja: "myśl_retrospektywna_braku_czasu" (typ: FENOMENON)
- "zimny posiłek" → encja: "posiłek" (typ: JEDZENIE) z właściwością "zimny"
- ALIASES: dodaj wszystkie warianty nazwy z tekstu narracyjnego

FORMAT - TYLKO JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu literackiego",
      "confidence": 0.X,
      "context": "fragment_tekstu_gdzie_wystepuje",
      "aliases": ["wariant1", "wariant2", "skrót"],
      "phenomenon_structure": {{
        "main_type": "MYŚL",
        "subtype": "retrospekcja", 
        "content": "nie miałem wtedy czasu"
      }} // tylko dla typu FENOMENON
    }}
  ]
}}

JSON:"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
        """
        Literary custom extraction builder - migrated from your custom_extraction.py
        This is the winning combo that gives 0.88+ confidence
        """
        entity_types_str = self.format_entity_types()
        
        final_prompt = f"""{custom_instructions}

TEKST LITERACKI DO ANALIZY:
{text}

DOSTĘPNE TYPY ENCJI (użyj tylko z tej listy):
{entity_types_str}

WYMAGANY FORMAT JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu literackiego",
      "confidence": 0.85,
      "context": "fragment_tekstu_gdzie_wystepuje",
      "aliases": ["wariant1", "wariant2", "skrót"],
      "phenomenon_structure": {{
        "main_type": "MYŚL",
        "subtype": "retrospekcja", 
        "content": "szczegóły fenomenu"
      }} // tylko dla typu FENOMENON
    }}
  ]
}}

WYKONAJ EKSTRAKCJĘ LITERACKĄ - ZWRÓĆ TYLKO JSON:"""
        
        return final_prompt
    
    def should_use_cleaning(self) -> bool:
        """Literary domain currently doesn't use semantic cleaning effectively"""
        return False
    
    def get_cleaning_prompt(self, text: str) -> Optional[str]:
        """
        Literary cleaning prompt - currently not used but kept for potential future use
        Migrated from your semantic_cleaning.py
        """
        if not self.should_use_cleaning():
            return None
            
        phenomenon_examples = self._format_phenomenon_lines()
        
        prompt = f"""Przekształć poniższy fragment wspomnieniowego tekstu autobiograficznego
w sformalizowaną scenę nadającą się do ekstrakcji encji i fenomenów literackich.

TEKST DO ANALIZY:
{text}

ZASADY PRZETWARZANIA LITERACKIEGO:
1. Bądź wnikliwy w analizie narracyjnej
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
    
    def get_confidence_threshold(self) -> float:
        """Literary domain uses higher confidence threshold due to complexity"""
        return 0.6
    
    def _format_phenomenon_lines(self) -> str:
        """Format literary phenomenon types for prompts - migrated from prompt_utils.py"""
        lines = [
            f"FORMATY FENOMENÓW LITERACKICH:",
            f"- Bez podmiotu: {{PHENOMENON_TYPE}}: {{subtype}} -> {{content}}",
            f"- Z podmiotem: {{PHENOMENON_TYPE}}: {{subtype}} -> [{{subject}}] {{content}}",
            "",
            "PRZYKŁADY Z PODMIOTAMI W LITERATURZE:",
            "- MYŚL: retrospekcja -> [narrator] nie miałem wtedy czasu na gotowanie",
            "- EMOCJA: podstawowa -> [mieszkańcy] cieszenie się z prądu", 
            "- KOMPENSACJA: -> [narrator] zjedzenie tortu w cukierni",
            "",
            "ROZPOZNAWANIE PODMIOTÓW Z TEKSTU LITERACKIEGO:",
            "- 'ja', 'nie mam', 'myślę' → [narrator]",
            "- 'my', 'mamy', 'cieszmy się' → [mieszkańcy]", 
            "- konkretne imiona/role → [imię/rola]",
            "- gdy nieznany podmiot → brak nawiasów lub [narrator]",
            "",
            "DOSTĘPNE TYPY I PODTYPY W LITERATURZE:"
        ]
        
        for category, phenomena in list(self._phenomenon_types.items())[:2]:  # Limit for prompt
            lines.append(f"• {category.upper()}:")
            for phenom_type, subtypes in phenomena.items():
                subtypes_str = ", ".join(subtypes[:3])  # Limit subtypes
                lines.append(f"  - {phenom_type}: {subtypes_str}")
        
        return "\n".join(lines)


# Register literary domain in factory
DomainFactory.register_domain("literary", LiteraryNER)