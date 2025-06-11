"""
Meta-prompt for chunk analysis
"""

from .prompt_utils import format_entity_types


def get_chunk_analysis_prompt(text: str) -> str:
    """META-PROMPT: Analizuje chunk i generuje spersonalizowany prompt NER"""
    entity_types_str = format_entity_types()
    
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