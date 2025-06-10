"""
Semantic cleaning prompt
"""

from .prompt_utils import format_phenomenon_lines


def get_semantic_cleaning_prompt(text: str) -> str:
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