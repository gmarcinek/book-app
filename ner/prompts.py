"""
NER Prompts - Tylko ekstrakcja encji, bez relacji
"""

from .consts import ENTITY_TYPES_FLAT, PHENOMENON_TYPES, PHENOMENON_STRUCTURE

def format_phenomenon_lines():
    """Format structured phenomenon types for prompt"""
    lines = [
        f"FORMATY FENOMENÓW:",
        f"- Bez podmiotu: {PHENOMENON_STRUCTURE['format']}",
        f"- Z podmiotem: {PHENOMENON_STRUCTURE['format_with_subject']}",
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
    
    for category, phenomena in list(PHENOMENON_TYPES.items())[:2]:  # Limit for prompt
        lines.append(f"• {category.upper()}:")
        for phenom_type, subtypes in phenomena.items():
            subtypes_str = ", ".join(subtypes[:3])  # Limit subtypes
            lines.append(f"  - {phenom_type}: {subtypes_str}")
    
    return "\n".join(lines)

def format_entity_types():
    """Format entity types for prompt"""
    return ", ".join(ENTITY_TYPES_FLAT)

class NERPrompts:
    """Uproszczone prompty - tylko ekstrakcja encji"""
    
    @classmethod
    def get_semantic_cleaning_prompt(cls, text: str) -> str:
        """Prompt do przekształcenia surowego tekstu w sformalizowaną treść"""
        
        phenomenon_examples = format_phenomenon_lines()
        
        prompt = f"""Przekształć poniższy fragment wspomnieniowego tekstu autobiograficznego
w sformalizowaną scenę nadającą się do ekstrakcji encji i fenomenów.

TEKST DO ANALIZY:
{text}

ZASADY PRZETWARZANIA:
1. bądź wnikliwy
2. Zachowaj konkretne obiekty, miejsca, osoby, wydarzenia, BRAKI, myśli i stany psychiczne
3. Zidentyfikuj fenomeny psychiczne i oznacz je strukturalnie:
{phenomenon_examples}
4. Używaj formatu: TYP_FENOMENU: podtyp -> konkretna treść
5. Każde oznaczenie fenomenu jako osobne zdanie
6. Język neutralny, bez metafor i poetyckości
7. Nie dodawaj faktów - tylko parafrazuj istniejące
8. Czas bezczasowy (prezentacyjny) zamiast przeszłego

FORMAT: czysty tekst z oznaczeniami fenomenów

PRZYKŁAD TRANSFORMACJI:
Input: "Nie miałem piekarnika. Zresztą i tak nie miałbym czasu. Zjadłem coś na zimno."
Output: Brak piekarnika w mieszkaniu. MYŚL: retrospekcja -> wtedy nie miałem czasu na gotowanie. Zjedzenie zimnego posiłku zamiast gotowania.

TWOJA TRANSFORMACJA:"""
        return prompt

    @classmethod
    def get_entity_extraction_prompt(cls, text: str) -> str:
        """Prompt do ekstrakcji encji - bez relacji"""
        
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

DOSTĘPNE TYPY ENCJI:
{entity_types_str}

STRUKTURA FENOMENÓW:
{phenomenon_examples}

INSTRUKCJE SPECJALNE:
- "brak piekarnika" → encja: "piekarnik" (typ: PRZEDMIOT) + "brak" (typ: BRAK)
- "MYŚL: retrospekcja -> nie miałem czasu" → encja: "myśl_retrospektywna_braku_czasu" (typ: FENOMENON)
- "zimny posiłek" → encja: "posiłek" (typ: JEDZENIE) z właściwością "zimny"

FORMAT - TYLKO JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu otaczającego",
      "confidence": 0.85,
      "context": "fragment_tekstu_gdzie_wystepuje",
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


# Backward compatibility functions
def get_entity_extraction_prompt(text: str) -> str:
    return NERPrompts.get_entity_extraction_prompt(text)