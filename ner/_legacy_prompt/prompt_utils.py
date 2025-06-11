"""
Prompt utilities - formatters for entity types and phenomena
"""

from ..consts import ENTITY_TYPES_FLAT, PHENOMENON_TYPES, PHENOMENON_STRUCTURE


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