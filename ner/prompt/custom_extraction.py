"""
Custom extraction prompt builder
"""

from .prompt_utils import format_entity_types


def build_custom_extraction_prompt(text: str, custom_instructions: str) -> str:
    """Buduje finalny prompt do ekstrakcji używając custom instructions z meta-prompt"""
    entity_types_str = format_entity_types()
    
    final_prompt = f"""{custom_instructions}

TEKST DO ANALIZY:
{text}

DOSTĘPNE TYPY ENCJI (użyj tylko z tej listy):
{entity_types_str}

WYMAGANY FORMAT JSON:
{{
  "entities": [
    {{
      "name": "nazwa_w_formie_podstawowej",
      "type": "TYP_Z_LISTY_WYŻEJ",
      "description": "definicja encji 3-5 zdań z uwzględnieniem kontekstu",
      "confidence": 0.85,
      "context": "fragment_tekstu_gdzie_wystepuje",
      "aliases": ["wariant1", "wariant2", "skrót"],
      "phenomenon_structure": {{
        "main_type": "MYŚL",
        "subtype": "retrospekcja", 
        "content": "szczegóły fenomenu"
      }} // tylko dla typu FENOMENON
    }}
  ]
}}

WYKONAJ EKSTRAKCJĘ - ZWRÓĆ TYLKO JSON:"""
    
    return final_prompt