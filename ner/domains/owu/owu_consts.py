# owu_consts.py - Rozszerzona lista typów encji dla OWU

OWU_ENTITY_TYPES = [
    # === SEKCJA 1: PODSTAWOWE TYPY STRUKTURALNE ===
    "PODMIOT_UMOWY", 
    "DOKUMENT", 
    "ROZDZIAŁ", 
    "ARTYKUŁ_PRAWNY", 
    "ODNIESIENIE",
    
    # === SEKCJA 2: DEFINICJE I TERMINOLOGIA - PRIORYTET ===
    "TERMIN_ZDEFINIOWANY",
    "DEFINICJA",
    "TERMINOLOGIA",
    "WARIANT_UBEZPIECZENIA",
    "WYJAŚNIENIE",
    "NUMER_BANKOWY",
    "NUMER_TELEFONU",
    "ADRES",
    
    # === SEKCJA 3: ASPEKTY CZASOWE ===
    "TERMIN_CZASOWY",
    
    # === SEKCJA 4: ASPEKTY FINANSOWE ===
    "KWOTA", 
    "INDEKSACJA", 
    "SKŁADKA_UBEZPIECZENIOWA", 
    "SUMA_UBEZPIECZENIA", 
    "ODSZKODOWANIE",
    
    # === SEKCJA 5: OSOBY I PODMIOTY ===
    "PODMIOT_FORMALNY", 
    "BENEFICJENT", 
    "PŁATNIK", 
    "UBEZPIECZAJĄCY", 
    "UBEZPIECZONY", 
    "RZECZOZNAWCA",
    
    # === SEKCJA 6: ZDARZENIA I RYZYKA ===
    "ZDARZENIE", 
    "WYPADEK", 
    "RYZYKO_UBEZPIECZENIOWE", 
    "SIŁA_WYŻSZA", 
    "KATASTROFA_NATURALNA",
    
    # === SEKCJA 7: MEDYCZNE I ZDROWOTNE ===
    "CHOROBA", 
    "USZCZERBEK_NA_ZDROWIU",
    
    # === SEKCJA 8: DOKUMENTY I FORMULARZE ===
    "POLISA_UBEZPIECZENIOWA", 
    "ANEKS_DO_UMOWY", 
    "ZGŁOSZENIE_SZKODY", 
    "DEKLARACJA",
    
    # === SEKCJA 9: PROCESY I PROCEDURY ===
    "CZYNNOŚĆ_FORMALNA", 
    "LIKWIDACJA_SZKODY", 
    "REGRES_UBEZPIECZYCIELA",
    
    # === SEKCJA 10: WARUNKI I OGRANICZENIA ===
    "WARUNEK", 
    "WYŁĄCZENIE_Z_UMOWY",
    
    # === SEKCJA 11: LOKALIZACJA I ORGANIZACJA ===
    "LOKALIZACJA", 
    "ORGANIZACJA", 
    "PRZEDMIOT_UBEZPIECZENIA",
]

def format_owu_entity_types() -> str:
    """Formatuje typy encji jako string rozdzielony przecinkami."""
    return ", ".join(OWU_ENTITY_TYPES)

def get_entity_count() -> int:
    """Zwraca łączną liczbę zdefiniowanych typów encji."""
    return len(OWU_ENTITY_TYPES)