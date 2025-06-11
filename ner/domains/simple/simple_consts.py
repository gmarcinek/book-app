SIMPLE_ENTITY_TYPES = {
    "core": ["OSOBA", "MIEJSCE", "OBIEKT"]
}

SIMPLE_ENTITY_TYPES_FLAT = []
for category in SIMPLE_ENTITY_TYPES.values():
    SIMPLE_ENTITY_TYPES_FLAT.extend(category)

def format_simple_entity_types() -> str:
    return ", ".join(SIMPLE_ENTITY_TYPES_FLAT)

# Przykłady dla promptów
SIMPLE_EXAMPLES = {
    "OSOBA": ["Jan Kowalski", "sąsiad", "sprzedawca", "mama", "pan Nowak"],
    "MIEJSCE": ["dom", "sklep", "urząd", "pralnia", "suszarnia", "kuchnia", "pokój", "biuro"],
    "OBIEKT": ["pralka", "suszarka", "telefon", "książka", "samochód", "komputer", "narzędzie"]
}

SIMPLE_PLACE_VS_OBJECT_GUIDE = """
MIEJSCE (gdzie można być/wejść/przebywać):
- dom, mieszkanie, pokój, kuchnia
- sklep, urząd, biuro, szkoła
- pralnia, suszarnia, warsztat
- park, plac zabaw, parking

OBIEKT (co można dotknąć/użyć/przenieść):
- pralka, suszarka, lodówka
- telefon, komputer, książka
- samochód, rower, narzędzie
- ubranie, jedzenie, zabawka
"""