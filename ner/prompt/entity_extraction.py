"""
Standard entity extraction prompt
"""
from .prompt_utils import format_entity_types, format_phenomenon_lines

def get_entity_extraction_prompt(text: str) -> str:
    """Prompt do ekstrakcji encji - bez relacji (FALLBACK - używany gdy meta-prompt nie działa)"""
    
    entity_types_str = format_entity_types()
    phenomenon_examples = format_phenomenon_lines()
    
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
- Miejsce: "Warszawa" → aliases: ["stolica", "WSZ", "miasto"]
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
      "confidence": 0.85, # od 0 do 1
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