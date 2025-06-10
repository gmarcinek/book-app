"""
Poprawka liric_consts.py: wyższy rating psychologii + generyczny FENOMENON
"""

# === ENTITY TYPES - FENOMENON zastępuje specifyczne typy psychiczne ===
LIRIC_ENTITY_TYPES = {
    "core": ["OSOBA", "MIEJSCE", "ORGANIZACJA", "PRZEDMIOT", "WYDARZENIE", "KONCEPCJA"],
    "liric_specific": ["JA_LIRYCZNE", "PODMIOT_LIRYCZNY", "OBRAZ_POETYCKI"],
    "structural": ["ZWROTKA", "TYP_RYMU", "RYTM", "SCENA", "DIALOG", "WYPOWIEDŹ"],
    "figury_stylistyczne": ["METAFORA", "PORÓWNANIE", "PERSONIFIKACJA", "APOSTROFA", "HIPERBOLA", "IRONIA"],
    "figury_składniowe": ["INWERSJA", "ELIPSA", "ANAFOR", "EPIFORA", "PARALELIZM", "GRADACJA"],
    "figury_dźwiękowe": ["ALITERACJA", "ASONANCJA", "ONOMATOPEJA"],
    "symbolika": ["SYMBOL", "ALEGORIA", "ARCHETYP"],
    "psychological": ["EMOCJA", "MYŚL", "NASTRÓJ"],  # ← POWRÓT do konkretnych typów
    "temporal": ["CZAS", "OKRES"],
    "absence": ["BRAK", "NIEOBECNOŚĆ"]
}

# Flatten wszystkich typów - WYMAGANE dla importów
LIRIC_ENTITY_TYPES_FLAT = []
for category in LIRIC_ENTITY_TYPES.values():
    LIRIC_ENTITY_TYPES_FLAT.extend(category)

# === CONFIDENCE - podwyższone dla psychologii ===
LIRIC_CONFIDENCE_THRESHOLDS = {
    "structural": 0.8,           # zwrotki, rymy
    "figury_stylistyczne": 0.6,  # metafory, porównania
    "psychological": 0.6,        # ← PODWYŻSZONE z 0.4 do 0.6 (emocje ważne w poezji!)
    "symbolika": 0.5,            # symbole, alegorie
    "metaphorical": 0.3,         # bardzo metaforyczne
    "default": 0.3
}

# === FENOMENON STRUCTURE - zachowana z literary ale rozszerzona ===
FENOMENON_TYPES = {
    "emocjonalny": [
        "radość", "smutek", "miłość", "tęsknota", "melancholia", 
        "ekstaza", "żal", "nadzieja", "rozpacz", "spokój"
    ],
    "kognitywny": [
        "wspomnienie", "myśl", "refleksja", "marzenie", "wizja",
        "przeczucie", "intuicja", "kontemplacja"
    ],
    "atmosferyczny": [
        "nastrój", "klimat", "atmosfera", "aura", "ton",
        "nastrojowość", "poetyckość"
    ],
    "duchowy": [
        "modlitwa", "medytacja", "transcendencja", "objawienie",
        "mistyka", "duchowość"
    ]
}

# === CORE INSTRUCTIONS - oparte na wiedzy modelu, nie językowych patterns ===
LIRIC_CORE_INSTRUCTIONS = """OBOWIĄZKOWE ENCJE (szukaj zawsze):
• ZWROTKA: grupy wersów oddzielone spacjami lub pustymi liniami
• METAFORA: ukryte przenośnie bez eksplicytnych markerów porównania
• PORÓWNANIE: eksplicytne porównania używające słów sygnalnych
• PERSONIFIKACJA: nadanie cech ludzkich przedmiotom lub abstrakcjom
• EMOCJA: uczucia, stany afektywne (strach, radość, smutek)
• MYŚL: procesy kognitywne, refleksje, wspomnienia
• NASTRÓJ: klimaty, atmosfery poetyckie
• SYMBOL: konkretne obiekty niosące głębsze znaczenie symboliczne"""

# === JSON TEMPLATE - rozszerzony o fenomeny ===
LIRIC_JSON_TEMPLATE = """{
  "entities": [
    {
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji z kontekstem poetyckim",
      "confidence": 0.50,
      "context": "fragment_tekstu_gdzie_wystepuje",
      "aliases": ["wariant1", "wariant2"],
      "phenomenon_structure": {
        "type": "emocjonalny/kognitywny/atmosferyczny/duchowy",
        "content": "szczegóły fenomenu"
      }
    }
  ]
}"""

# === UTILITY FUNCTIONS - WYMAGANE dla importów ===
def format_liric_entity_types() -> str:
    """Format entity types for prompt - WYMAGANE"""
    return ", ".join(LIRIC_ENTITY_TYPES_FLAT)

def get_liric_confidence_threshold(entity_type: str) -> float:
    """Zaktualizowane progi confidence - WYMAGANE"""
    if entity_type in ["ZWROTKA", "TYP_RYMU", "RYTM"]:
        return LIRIC_CONFIDENCE_THRESHOLDS["structural"]
    elif entity_type in ["METAFORA", "PORÓWNANIE", "PERSONIFIKACJA", "APOSTROFA", "HIPERBOLA"]:
        return LIRIC_CONFIDENCE_THRESHOLDS["figury_stylistyczne"]
    elif entity_type == "FENOMENON": 
        return LIRIC_CONFIDENCE_THRESHOLDS["psychological"]  # 0.6
    elif entity_type in ["SYMBOL", "ALEGORIA", "ARCHETYP"]:
        return LIRIC_CONFIDENCE_THRESHOLDS["symbolika"]
    elif entity_type in ["OSOBA", "MIEJSCE", "PRZEDMIOT"]:
        return LIRIC_CONFIDENCE_THRESHOLDS["structural"]
    else:
        return LIRIC_CONFIDENCE_THRESHOLDS["default"]

def get_fenomenon_examples() -> str:
    """Przykłady fenomenów dla promptów"""
    examples = []
    for ftype, subtypes in FENOMENON_TYPES.items():
        example_subtypes = ", ".join(subtypes[:3])  # Pierwsze 3
        examples.append(f"• {ftype}: {example_subtypes}")
    return "\n".join(examples)

def build_confidence_guide() -> str:
    """Buduje dynamiczny przewodnik confidence na podstawie progów"""
    structural = LIRIC_CONFIDENCE_THRESHOLDS["structural"]
    figury = LIRIC_CONFIDENCE_THRESHOLDS["figury_stylistyczne"]
    psychological = LIRIC_CONFIDENCE_THRESHOLDS["psychological"]
    symbolika = LIRIC_CONFIDENCE_THRESHOLDS["symbolika"]
    
    return f"""CONFIDENCE POETRY:
• Struktura (ZWROTKA, TYP_RYMU): {structural}+
• Figury stylistyczne (METAFORA, PORÓWNANIE): {figury}+
• Psychologia (EMOCJA, MYŚL, NASTRÓJ): {psychological}+
• Symbolika (SYMBOL, ALEGORIA): {symbolika}+
• Inne encje: sprawdź indywidualnie"""