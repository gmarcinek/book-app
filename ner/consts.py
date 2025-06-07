"""
NER Constants - Comprehensive relationship types and entity categories
"""

RELATIONSHIP_TYPES = {
    "spatial": [
        "contains", "located_in", "adjacent_to", "surrounds", 
        "above", "below", "inside", "outside", "near", "far_from"
    ],
    "structural": [
        "is_a", "part_of", "composed_of", "made_of",
        "belongs_to", "owns", "has_property"
    ],
    "functional": [
        "uses", "requires", "depends_on", "serves",
        "creates", "produces", "consumes", "operates_on",
        "enables", "prevents", "blocks"
    ],
    "causal": [
        "causes", "caused_by", "leads_to", "results_from",
        "triggers", "triggered_by", "influences", "affected_by"
    ],
    "temporal": [
        "before", "after", "during", "simultaneous_with",
        "replaces", "replaced_by", "precedes", "follows"
    ],
    "psychological": [
        "experiences", "feels", "thinks_about", "remembers",
        "imagines", "fears", "desires", "avoids",
        "compensates_for", "projects_onto", "compares_to"
    ],
    "social": [
        "knows", "related_to", "friend_of", "enemy_of",
        "works_with", "lives_with", "married_to", "child_of"
    ],
    "semantic": [
        "similar_to", "opposite_of", "synonym_of", "example_of",
        "category_of", "instance_of", "represents", "symbolizes"
    ],
    "quantitative": [
        "more_than", "less_than", "equal_to", "approximately",
        "higher_than", "lower_than", "faster_than", "slower_than"
    ],
    "absence": [
        "lacks", "missing", "without", "deprived_of",
        "absent_from", "excluded_from", "denied"
    ]
}

ENTITY_TYPES = {
    "core": [
        "OSOBA", "MIEJSCE", "ORGANIZACJA", "PRZEDMIOT", 
        "WYDARZENIE", "USŁUGA", "KONCEPCJA"
    ],
    "psychological": [
        "FENOMENON", "EMOCJA", "MYŚL", "WSPOMNIENIE",
        "SEN", "LĘKI", "PRAGNIENIE", "INTENCJA"
    ],
    "temporal": [
        "CZAS", "OKRES", "MOMENT", "ETAP", "FAZA"
    ],
    "abstract": [
        "WARTOŚĆ", "ZASADA", "REGUŁA", "NORMA",
        "PROBLEM", "ROZWIĄZANIE", "PLAN", "CEL"
    ],
    "physical": [
        "SUBSTANCJA", "MATERIAŁ", "NARZĘDZIE", "URZĄDZENIE",
        "BUDYNEK", "POJAZD", "JEDZENIE", "UBRANIE"
    ],
    "absence": [
        "BRAK", "NIEOBECNOŚĆ", "PUSTKA", "DEFICYT"
    ]
}

# Flatten for backward compatibility
ENTITY_TYPES_FLAT = []
for category in ENTITY_TYPES.values():
    ENTITY_TYPES_FLAT.extend(category)

PHENOMENON_PREFIXES = {
    "cognitive": [
        "MYŚL:", "WSPOMNIENIE:", "WYOBRAŻENIE:", "PLAN:",
        "ANALIZA:", "OCENA:", "WNIOSEK:", "PRZYPUSZCZENIE:"
    ],
    "emotional": [
        "EMOCJA:", "UCZUCIE:", "NASTRÓJ:", "AFEKT:",
        "RADOŚĆ:", "SMUTEK:", "ZŁOŚĆ:", "STRACH:", "WSTYD:"
    ],
    "motivational": [
        "INTENCJA:", "PRAGNIENIE:", "POTRZEBA:", "CEL:",
        "MOTYW:", "DĄŻENIE:", "AMBICJA:", "CHĘĆ:"
    ],
    "behavioral": [
        "KOMPENSACJA:", "UNIKANIE:", "PRZYSTOSOWANIE:", "OBRONA:",
        "STRATEGIA:", "TAKTYKA:", "ZACHOWANIE:", "REAKCJA:"
    ],
    "social": [
        "PROJEKCJA:", "IDENTYFIKACJA:", "PORÓWNANIE:", "OCENA_SPOŁECZNA:",
        "OCZEKIWANIE:", "ZAŁOŻENIE:", "STEREOTYP:", "UPRZEDZENIE:"
    ],
    "existential": [
        "SENS:", "WARTOŚĆ:", "ZNACZENIE:", "PRZEZNACZENIE:",
        "MISJA:", "ROLA:", "TOŻSAMOŚĆ:", "SAMOOCENA:"
    ]
}

# Flatten phenomenon prefixes for backward compatibility
PHENOMENON_PREFIXES_FLAT = []
for category in PHENOMENON_PREFIXES.values():
    PHENOMENON_PREFIXES_FLAT.extend(category)

# Relationship validation - which entity types can participate in which relationships
RELATIONSHIP_ENTITY_CONSTRAINTS = {
    "spatial": {
        "allowed_subjects": ["PRZEDMIOT", "OSOBA", "MIEJSCE", "BUDYNEK"],
        "allowed_objects": ["PRZEDMIOT", "MIEJSCE", "BUDYNEK"]
    },
    "psychological": {
        "allowed_subjects": ["OSOBA"],
        "allowed_objects": ["FENOMENON", "EMOCJA", "MYŚL", "OSOBA", "WYDARZENIE"]
    },
    "absence": {
        "allowed_subjects": ["OSOBA", "MIEJSCE", "ORGANIZACJA"],
        "allowed_objects": ["PRZEDMIOT", "USŁUGA", "KONCEPCJA", "OSOBA"]
    },
    "functional": {
        "allowed_subjects": ["OSOBA", "URZĄDZENIE", "NARZĘDZIE"],
        "allowed_objects": ["PRZEDMIOT", "USŁUGA", "MATERIAŁ"]
    }
}

# Common relationship patterns for autobiographical texts
AUTOBIOGRAPHICAL_PATTERNS = {
    "lack_patterns": [
        ("OSOBA", "lacks", "PRZEDMIOT"),
        ("MIEJSCE", "lacks", "PRZEDMIOT"),
        ("OSOBA", "lacks", "USŁUGA"),
        ("OSOBA", "lacks", "CZAS")
    ],
    "compensation_patterns": [
        ("OSOBA", "compensates_for", "BRAK"),
        ("KOMPENSACJA", "results_from", "BRAK"),
        ("OSOBA", "uses", "PRZEDMIOT") # jako kompensacja
    ],
    "emotional_patterns": [
        ("OSOBA", "experiences", "EMOCJA"),
        ("WYDARZENIE", "causes", "EMOCJA"),
        ("MYŚL", "triggers", "EMOCJA")
    ]
}

# Quality scoring weights for relationships
RELATIONSHIP_QUALITY_WEIGHTS = {
    "text_evidence": 0.4,      # Czy relacja jest wprost w tekście
    "logical_consistency": 0.3, # Czy relacja ma sens logiczny
    "autobiographical_relevance": 0.2, # Czy pasuje do kontekstu autobiograficznego
    "psychological_depth": 0.1   # Czy wnosi wgląd psychologiczny
}

PHENOMENON_TYPES = {
    "cognitive": {
        "MYŚL": ["retrospekcja", "prospektywna", "analityczna", "asocjacyjna", "obsesyjna"],
        "WSPOMNIENIE": ["autobiograficzne", "traumatyczne", "nostalgiczne", "fragmentaryczne"],
        "WYOBRAŻENIE": ["wizualne", "audytywne", "fantazyjne", "lękowe"],
        "ANALIZA": ["sytuacyjna", "przyczynowa", "porównawcza", "krytyczna"],
        "OCENA": ["siebie", "innych", "sytuacji", "przyszłości"],
        "PLAN": ["krótkoterminowy", "długoterminowy", "awaryjny", "idealny"]
    },
    "emotional": {
        "EMOCJA": ["podstawowa", "złożona", "mieszana", "stłumiona"],
        "UCZUCIE": ["pozytywne", "negatywne", "ambiwalentne", "intensywne"],
        "NASTRÓJ": ["długotrwały", "chwilowy", "cykliczny", "sezonowy"],
        "STRACH": ["konkretny", "egzystencjalny", "społeczny", "irracjonalny"],
        "ZŁOŚĆ": ["na_siebie", "na_innych", "na_sytuację", "bezradności"]
    },
    "motivational": {
        "INTENCJA": ["świadoma", "nieświadoma", "konfliktrowa", "ukryta"],
        "PRAGNIENIE": ["spełnione", "niespełnione", "konfliktowe", "zakázane"],
        "POTRZEBA": ["podstawowa", "psychologiczna", "społeczna", "duchowa"],
        "CEL": ["osiągnięty", "porzucony", "odłożony", "nierealistyczny"]
    },
    "behavioral": {
        "KOMPENSACJA": ["nadmierna", "skuteczna", "destrukcyjna", "twórcza"],
        "UNIKANIE": ["społeczeństwa", "konfliktów", "odpowiedzialności", "emocji"],
        "ADAPTACJA": ["pozytywna", "negatywna", "częściowa", "wymuszona"],
        "OBRONA": ["zaprzeczenie", "projekcja", "racjonalizacja", "wyparcie"]
    },
    "social": {
        "PORÓWNANIE": ["z_innymi", "z_przeszłością", "z_ideałem", "z_normą"],
        "PROJEKCJA": ["własnych_lęków", "pragnień", "wad", "cech"],
        "OCZEKIWANIE": ["realistyczne", "nadmierne", "rozczarowujące", "społeczne"],
        "STEREOTYP": ["pozytywny", "negatywny", "kulturowy", "osobisty"]
    },
    "existential": {
        "SENS": ["życia", "cierpienia", "działania", "relacji"],
        "WARTOŚĆ": ["osobista", "społeczna", "moralna", "estetyczna"],
        "TOŻSAMOŚĆ": ["zawodowa", "społeczna", "płciowa", "osobista"],
        "ROLA": ["rodzinna", "zawodowa", "społeczna", "życiowa"]
    }
}

# Structured phenomenon format
PHENOMENON_STRUCTURE = {
    "format": "{PHENOMENON_TYPE}: {subtype} -> {content}",
    "format_with_subject": "{PHENOMENON_TYPE}: {subtype} -> [{subject}] {content}"
}