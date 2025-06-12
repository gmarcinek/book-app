
SIMPLE_ENTITY_TYPES = {
    "core": ["OSOBA", "MIEJSCE", "PRZEDMIOT"],
    "extended": ["WYDARZENIE", "CZAS", "KONCEPCJA"]
}

SIMPLE_ENTITY_TYPES_FLAT = []
for category in SIMPLE_ENTITY_TYPES.values():
    SIMPLE_ENTITY_TYPES_FLAT.extend(category)

def format_simple_entity_types() -> str:
    return ", ".join(SIMPLE_ENTITY_TYPES_FLAT)

SIMPLE_ENTITY_TYPES = {
    "core": ["OSOBA", "MIEJSCE", "PRZEDMIOT"],
    "extended": ["WYDARZENIE", "CZAS", "KONCEPCJA"]
}

SIMPLE_EXAMPLES = {
    "OSOBA": ["Jan Kowalski", "sąsiad", "sprzedawca", "mama"],
    "MIEJSCE": ["dom", "sklep", "urząd", "kuchnia", "park"],
    "PRZEDMIOT": ["telefon", "książka", "samochód", "pralka"],
    "WYDARZENIE": ["spotkanie", "wypadek", "urodziny", "mecz"],
    "CZAS": ["wczoraj", "2023", "rano", "wiosna"],
    "KONCEPCJA": ["miłość", "demokracja", "AI", "teoria"]
}

SIMPLE_PLACE_VS_OBJECT_GUIDE = """
MIEJSCE: gdzie można być (dom, sklep, park)
PRZEDMIOT: można dotknąć/przenieść (telefon, książka)
KONCEPCJA: abstrakcje, idee (miłość, teoria)
"""