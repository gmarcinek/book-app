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

2. ZIDENTYFIKUJ WYZWANIA dla ekstrakcji NER w tym fragmencie:
   - Niejednoznaczne nazwy (np. "dom" jako obiekt vs miejsce)
   - Metafory i abstrakcje
   - Fenomeny psychiczne wymagające specjalnej uwagi
   - Braki i nieobecności jako encje

3. STWÓRZ SPERSONALIZOWANY PROMPT NER który:
   - Jest dopasowany do stylu i treści tego konkretnego fragmentu
   - Zawiera konkretne instrukcje dla znalezionych wzorców
   - Uwzględnia zidentyfikowane wyzwania
   - Zawiera odpowiednie przykłady z podobnego kontekstu
   - WYMAGAJ ALIASES dla wszystkich encji (warianty nazw, skróty, formy odmienione)

DOSTĘPNE TYPY ENCJI: {entity_types_str}

FORMAT ODPOWIEDZI - ZWRÓĆ TYLKO GOTOWY PROMPT NER:

<CUSTOM_NER_PROMPT>
[TUTAJ WSTAW SWÓJ SPERSONALIZOWANY PROMPT DO EKSTRAKCJI NER]
</CUSTOM_NER_PROMPT>

WYMAGANIA DO CUSTOM PROMPTU:
- Zaczynaj od "Zidentyfikuj encje w poniższym fragmencie..."
- Uwzględnij specyfikę tego fragmentu w instrukcjach
- Dodaj konkretne przykłady z podobnego kontekstu
- Zakończ wymaganiem formatu JSON
- Długość: 300-600 słów

WYGENERUJ TERAZ SPERSONALIZOWANY PROMPT:"""
    
    return prompt