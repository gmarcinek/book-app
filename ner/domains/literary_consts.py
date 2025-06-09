"""
Literary Domain Constants - Backup/Fallback obecnego prompter systemu
Wszystkie konstanty specyficzne dla domeny literackiej/autobiograficznej
"""

from enum import Enum
from typing import List, Dict, Any

# === ENTITY TYPES - kopia z consts.py ===
LITERARY_ENTITY_TYPES = {
    "core": [
        "OSOBA", "MIEJSCE", "ORGANIZACJA", "PRZEDMIOT", 
        "WYDARZENIE", "USŁUGA", "KONCEPCJA"
    ],
    "structural": [
        "SCENA", "DIALOG"
    ],
    "psychological": [
        "FENOMENON", "EMOCJA", "MYŚL"
    ],
    "temporal": [
        "CZAS", "OKRES"
    ],
    "abstract": [
        "WARTOŚĆ", "PROBLEM", "ROZWIĄZANIE", "CEL"
    ],
    "physical": [
        "MATERIAŁ", "NARZĘDZIE", "BUDYNEK", "JEDZENIE"
    ],
    "absence": [
        "BRAK", "NIEOBECNOŚĆ"
    ]
}

# Flatten dla prompt formatowania
LITERARY_ENTITY_TYPES_FLAT = []
for category in LITERARY_ENTITY_TYPES.values():
    LITERARY_ENTITY_TYPES_FLAT.extend(category)

# === PHENOMENON STRUCTURES - kopia z consts.py ===
LITERARY_PHENOMENON_PREFIXES = {
    "cognitive": [
        "MYŚL:", "WSPOMNIENIE:", "PLAN:", "ANALIZA:"
    ],
    "emotional": [
        "EMOCJA:", "UCZUCIE:", "STRACH:", "RADOŚĆ:"
    ],
    "motivational": [
        "INTENCJA:", "PRAGNIENIE:", "POTRZEBA:", "CEL:"
    ],
    "behavioral": [
        "KOMPENSACJA:", "UNIKANIE:", "REAKCJA:"
    ]
}

LITERARY_PHENOMENON_STRUCTURE = {
    "format": "{PHENOMENON_TYPE}: {subtype} -> {content}",
    "format_with_subject": "{PHENOMENON_TYPE}: {subtype} -> [{subject}] {content}"
}

LITERARY_PHENOMENON_TYPES = {
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

# === CONFIDENCE THRESHOLDS - specyficzne dla literatury ===
LITERARY_CONFIDENCE_THRESHOLDS = {
    "explicit_names": 0.9,        # "Jan Kowalski", konkretne przedmioty
    "clear_context": 0.8,         # jasne z kontekstu, opisane szczegółowo  
    "inferred": 0.6,               # domniemane, wywnioskowane pośrednio
    "psychological": 0.4,          # abstrakcyjne, fenomeny psychiczne
    "metaphorical": 0.3,           # metaforyczne, bardzo niepewne
    "uncertain": 0.2               # wymagające weryfikacji
}

# === PROMPT TEMPLATES - bazowe wzorce ===
LITERARY_META_ANALYSIS_CONTEXT = """Jesteś ekspertem od Named Entity Recognition dla tekstów literackich i autobiograficznych. 
Analizujesz fragment tekstu pod kątem:
- Głównych tematów (autobiografia, wspomnienia, psychologia)
- Typów encji (osoby, miejsca, fenomeny psychiczne, sceny, dialogi)
- Wzorców językowych (pierwsza osoba, czas przeszły, retrospekcje)
- Stanów psychicznych, emocji, wspomnień
- Scen jako spójnych kontekstów sytuacyjnych
- Dialogów jako obiektywnych faktów rozmów"""

LITERARY_EXTRACTION_RULES = """ZASADY EKSTRAKCJI:
1. Tylko encje jawnie obecne lub logicznie implikowane w tekście
2. Forma podstawowa (mianownik, liczba pojedyncza)
3. Uwzględnij BRAKI jako pełnoprawne encje
4. FENOMENY psychiczne ze strukturą "TYP: podtyp -> treść" jako typ "FENOMENON"
5. SCENY jako spójne fragmenty akcji z lokacją, postaciami i tematyką
6. DIALOGI jako rozmowy między postaciami (obiektywne fakty)"""

LITERARY_CONFIDENCE_GUIDE = """SZACOWANIE CONFIDENCE - bądź realistyczny:
- 0.9+ = wyraźnie nazwane, jednoznaczne (Jan Kowalski, konkretne przedmioty)
- 0.7-0.9 = jasne z kontekstu, opisane szczegółowo
- 0.5-0.7 = domniemane, wywnioskowane pośrednio  
- 0.3-0.5 = abstrakcyjne, metaforyczne, fenomeny psychiczne
- 0.1-0.3 = bardzo niepewne, wymagające weryfikacji"""

LITERARY_SPECIAL_INSTRUCTIONS = """INSTRUKCJE SPECJALNE:
- "brak piekarnika" → encja: "piekarnik" (typ: PRZEDMIOT) + "brak" (typ: BRAK)
- "MYŚL: retrospekcja -> nie miałem czasu" → encja: "myśl_retrospektywna_braku_czasu" (typ: FENOMENON)
- "zimny posiłek" → encja: "posiłek" (typ: JEDZENIE) z właściwością "zimny"
- ALIASES: dodaj wszystkie warianty nazwy z tekstu"""

LITERARY_ALIASES_EXAMPLES = """PRZYKŁADY ALIASES:
- Osoba: "Jan Kowalski" → aliases: ["Jan", "Kowalski", "JK", "Janek"]
- Miejsce: "Warszawa" → aliases: ["stolica", "WWA", "miasto"]
- Scena: "rozmowa_w_ogrodzie" → aliases: ["scena_w_ogrodzie", "dialog_na_zewnątrz"]
- Dialog: "rozmowa_z_sąsiadem" → aliases: ["dialog_z_sąsiadem", "konwersacja"]"""

# === JSON TEMPLATES ===
LITERARY_JSON_TEMPLATE = """{
  "entities": [
    {
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu",
      "confidence": 0.85,
      "context": "fragment_tekstu_gdzie_wystepuje",
      "aliases": ["wariant1", "wariant2", "skrót"],
      "phenomenon_structure": {
        "main_type": "MYŚL",
        "subtype": "retrospekcja", 
        "content": "szczegóły fenomenu"
      } // tylko dla typu FENOMENON
    }
  ]
}"""

# === UTILITY FUNCTIONS ===
def format_literary_entity_types() -> str:
    """Format entity types for prompt"""
    return ", ".join(LITERARY_ENTITY_TYPES_FLAT)

def format_literary_phenomenon_lines() -> str:
    """Format structured phenomenon types for prompt"""
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

def get_literary_confidence_threshold(entity_type: str) -> float:
    """Get confidence threshold based on entity type"""
    if entity_type in ["OSOBA", "MIEJSCE", "PRZEDMIOT"]:
        return LITERARY_CONFIDENCE_THRESHOLDS["explicit_names"]
    elif entity_type in ["FENOMENON", "EMOCJA", "MYŚL"]:
        return LITERARY_CONFIDENCE_THRESHOLDS["psychological"]
    elif entity_type in ["SCENA", "DIALOG"]:
        return LITERARY_CONFIDENCE_THRESHOLDS["inferred"]
    else:
        return LITERARY_CONFIDENCE_THRESHOLDS["uncertain"]