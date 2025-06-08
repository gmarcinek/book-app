"""
NER Constants - Uproszczone typy encji bez relacji
"""

# Podstawowe typy encji - znacznie uproszczone
ENTITY_TYPES = {
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

# Flatten dla backward compatibility
ENTITY_TYPES_FLAT = []
for category in ENTITY_TYPES.values():
    ENTITY_TYPES_FLAT.extend(category)

# Uproszczone prefiksy fenomenów - tylko najważniejsze
PHENOMENON_PREFIXES = {
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

# Flatten phenomenon prefixes
PHENOMENON_PREFIXES_FLAT = []
for category in PHENOMENON_PREFIXES.values():
    PHENOMENON_PREFIXES_FLAT.extend(category)

# Struktura fenomenów - uproszczona
PHENOMENON_STRUCTURE = {
    "format": "{PHENOMENON_TYPE}: {subtype} -> {content}",
    "format_with_subject": "{PHENOMENON_TYPE}: {subtype} -> [{subject}] {content}"
}

# Podstawowe typy fenomenów - znacznie skrócone
PHENOMENON_TYPES = {
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