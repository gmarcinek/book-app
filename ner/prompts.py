"""
NER Prompts - Precyzyjne prompty używające rozbudowanych konstant
"""

from typing import Dict, List, Any
from .consts import (
    RELATIONSHIP_TYPES, ENTITY_TYPES_FLAT, PHENOMENON_PREFIXES_FLAT,
    AUTOBIOGRAPHICAL_PATTERNS, RELATIONSHIP_ENTITY_CONSTRAINTS
)

def format_phenomenon_lines():
    """Format structured phenomenon types for prompt with subject support"""
    from .consts import PHENOMENON_TYPES, PHENOMENON_STRUCTURE
    
    lines = [
        f"FORMATY FENOMENÓW:",
        f"- Bez podmiotu: {PHENOMENON_STRUCTURE['format']}",
        f"- Z podmiotem: {PHENOMENON_STRUCTURE['format_with_subject']}",
        "",
        "PRZYKŁADY Z PODMIOTAMI:",
        "- MYŚL: retrospekcja -> [narrator] nie miałem wtedy czasu na gotowanie",
        "- EMOCJA: wdzięczność -> [mieszkańcy] cieszenie się z prądu", 
        "- KOMPENSACJA: skuteczna -> [narrator] zjedzenie tortu w cukierni",
        "- PORÓWNANIE: z_innymi -> [narrator] inni mają gorsze warunki",
        "",
        "ROZPOZNAWANIE PODMIOTÓW Z TEKSTU:",
        "- 'ja', 'nie mam', 'myślę' → [narrator]",
        "- 'my', 'mamy', 'cieszmy się' → [mieszkańcy]", 
        "- konkretne imiona/role → [imię/rola]",
        "- gdy nieznany podmiot → brak nawiasów lub [narrator]",
        "",
        "DOSTĘPNE TYPY I PODTYPY:"
    ]
    
    for category, phenomena in list(PHENOMENON_TYPES.items())[:3]:  # Limit for prompt
        lines.append(f"• {category.upper()}:")
        for phenom_type, subtypes in phenomena.items():
            subtypes_str = ", ".join(subtypes[:4])  # Limit subtypes
            lines.append(f"  - {phenom_type}: {subtypes_str}")
    
    return "\n".join(lines)

def format_relationship_types():
    """Format relationship types by category for prompt"""
    sections = []
    for category, relations in RELATIONSHIP_TYPES.items():
        relations_str = ", ".join(relations)
        sections.append(f"• {category.upper()}: {relations_str}")
    return "\n".join(sections)

def format_entity_types():
    """Format entity types for prompt"""
    return ", ".join(ENTITY_TYPES_FLAT)

class NERPrompts:
    """Ulepszone prompty z precyzyjnymi instrukcjami i rozbudowanymi konstantami"""
    
    @classmethod
    def get_semantic_cleaning_prompt(cls, text: str) -> str:
        """Prompt do przekształcenia surowego tekstu w sformalizowaną treść"""
        
        phenomenon_examples = format_phenomenon_lines()
        
        prompt = f"""Przekształć poniższy fragment wspomnieniowego tekstu autobiograficznego
w sformalizowaną scenę nadającą się do ekstrakcji encji i fenomenów.

TEKST DO ANALIZY:
{text}

ZASADY PRZETWARZANIA:
1. Usuń elementy niekonkretne: "czas", "życie", "los", "zawsze", "może", "jakby"
2. Zachowaj konkretne obiekty, miejsca, osoby, wydarzenia, BRAKI, myśli i stany psychiczne
3. Zidentyfikuj fenomeny psychiczne i oznacz je strukturalnie:
{phenomenon_examples}
4. Używaj formatu: TYP_FENOMENU: podtyp -> konkretna treść
5. Każde oznaczenie fenomenu jako osobne zdanie
5. Język neutralny, bez metafor i poetyckości
6. Nie dodawaj faktów - tylko parafrazuj istniejące
7. Czas bezczasowy (prezentacyjny) zamiast przeszłego

FORMAT: czysty tekst z oznaczeniami fenomenów

PRZYKŁAD TRANSFORMACJI:
Input: "Nie miałem piekarnika. Zresztą i tak nie miałbym czasu. Zjadłem coś na zimno."
Output: Brak piekarnika w mieszkaniu. MYŚL: retrospekcja -> wtedy nie miałem czasu na gotowanie. KOMPENSACJA: skuteczna -> zjedzenie zimnego posiłku zamiast gotowania.

TWOJA TRANSFORMACJA:
{text}
"""
        return prompt

    @classmethod
    def get_entity_extraction_prompt(cls, text: str) -> str:
        """Precyzyjny prompt do ekstrakcji encji z rozbudowanymi typami"""
        
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
- "KOMPENSACJA: skuteczna -> zimny posiłek" → encja: "kompensacja_skuteczna" (typ: FENOMENON)
- "zimny posiłek" → encja: "posiłek" (typ: JEDZENIE) z właściwością "zimny"

FORMAT - TYLKO JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "meta": {{
        "description": "krótka definicja (1-2 słowa)",
        "source": "tekst" | "wiedza_ogólna" | "implikacja",
        "confidence": 0.85,
        "context": "fragment_tekstu_gdzie_wystepuje",
        "phenomenon_structure": {{
          "main_type": "MYŚL",
          "subtype": "retrospekcja", 
          "content": "nie miałem wtedy czasu"
        }} // tylko dla typu FENOMENON
      }}
    }}
  ]
}}

JSON:"""
        return prompt

    @classmethod  
    def get_relationship_extraction_prompt(cls, entity_name: str, entity_type: str, 
                                         entity_context: List[str], text_sample: str) -> str:
        """Precyzyjny prompt do ekstrakcji relacji z walidacją typów"""
        
        # Ograniczenie kontekstu
        context_entities = entity_context[:10] if len(entity_context) > 10 else entity_context
        context_str = ", ".join(context_entities) if context_entities else "brak"
        
        # Formatowanie typów relacji
        relationship_types_str = format_relationship_types()
        
        # Przykłady wzorców autobiograficznych
        pattern_examples = []
        for pattern_type, patterns in AUTOBIOGRAPHICAL_PATTERNS.items():
            examples = [f"{subj} {rel} {obj}" for subj, rel, obj in patterns[:2]]
            pattern_examples.append(f"• {pattern_type}: {', '.join(examples)}")
        pattern_examples_str = "\n".join(pattern_examples)

        prompt = f"""Znajdź logiczne relacje dla encji: "{entity_name}" (typ: {entity_type})

TEKST ŹRÓDŁOWY: 
{text_sample[:600]}...

DOSTĘPNE ENCJE W KONTEKŚCIE: 
{context_str}

KRYTERIA JAKOŚCI RELACJI:
1. ✅ POTWIERDZONE w tekście lub logicznie wynikające
2. ✅ ZGODNE z wiedzą ogólną
3. ✅ PASUJĄCE do kontekstu autobiograficznego
4. ❌ UNIKAJ relacji encji ze sobą samą
5. ❌ UNIKAJ nadmiernych generalizacji

DOZWOLONE TYPY RELACJI:
{relationship_types_str}

TYPOWE WZORCE AUTOBIOGRAFICZNE:
{pattern_examples_str}

PRZYKŁADY DOBRYCH RELACJI:
- "piekarnik" → lacks (BRAK w tekście: "nie miałem piekarnika")
- "osoba" experiences "myśl_braku_czasu" (FENOMENON z tekstu)
- "mieszkanie" lacks "piekarnik" (strukturalna, potwierdzona)

PRZYKŁADY ZŁYCH RELACJI:
- "piekarnik" uses "piekarnik" (samorelacja)
- "chleb" located_in "piekarnik" (piekarnika nie ma!)
- wszystko "similar_to" wszystko (nadmierne)

ODPOWIEDZ TYLKO JSON (maksymalnie 5 najlepszych relacji):
{{
  "internal_relationships": [
    {{
      "type": "typ_z_listy_wyżej",
      "target_entity": "nazwa_encji_z_kontekstu",
      "evidence": "konkretne_uzasadnienie_z_tekstu",
      "confidence": 0.90,
      "quality_score": 0.85
    }}
  ],
  "external_relationships": [
    {{
      "type": "typ_relacji",
      "value": "konkretna_wartość_nie_encja",
      "source": "tekst" | "wiedza_ogólna" | "implikacja"
    }}
  ],
  "missing_entities": [
    {{
      "name": "nazwa_brakującej_encji",
      "type": "typ_z_listy_encji",
      "reason": "dlaczego_potrzebna_dla_kompletności"
    }}
  ]
}}

JSON:"""
        return prompt

    @classmethod
    def get_quality_validation_prompt(cls, relationships: List[Dict], original_text: str) -> str:
        """Prompt do walidacji jakości wyekstraktowanych relacji"""
        
        relationships_str = "\n".join([
            f"- {r['type']}: {r.get('subject', '?')} → {r.get('target_entity', r.get('value', '?'))}"
            for r in relationships[:10]
        ])
        
        prompt = f"""Oceń jakość i spójność poniższych relacji względem oryginalnego tekstu.

ORYGINALNY TEKST:
{original_text}

RELACJE DO OCENY:
{relationships_str}

KRYTERIA OCENY:
1. EVIDENCE (0-1): Czy relacja jest potwierdzona w tekście?
2. LOGIC (0-1): Czy relacja ma sens logiczny?
3. RELEVANCE (0-1): Czy pasuje do kontekstu autobiograficznego?
4. REDUNDANCY (0-1): Czy nie dubluje innych relacji?

ZADANIA:
1. Usuń relacje sprzeczne lub nonsensowne
2. Znajdź brakujące ważne relacje
3. Grupuj podobne relacje
4. Oceń ogólną spójność

ODPOWIEDZ JSON:
{{
  "validated_relationships": [
    {{
      "type": "typ",
      "subject": "podmiot", 
      "target": "cel",
      "evidence_score": 0.9,
      "logic_score": 0.8,
      "relevance_score": 0.85,
      "final_score": 0.85
    }}
  ],
  "removed_relationships": ["powody_usunięcia"],
  "suggested_additions": [
    {{"type": "typ", "subject": "podmiot", "target": "cel", "reason": "dlaczego_brakuje"}}
  ],
  "overall_coherence": 0.82
}}

JSON:"""
        return prompt


# Backward compatibility functions
def get_entity_extraction_prompt(text: str) -> str:
    return NERPrompts.get_entity_extraction_prompt(text)

def get_relationship_extraction_prompt(entity_name: str, entity_type: str, 
                                     entity_context: List[str], text_sample: str) -> str:
    return NERPrompts.get_relationship_extraction_prompt(
        entity_name, entity_type, entity_context, text_sample
    )