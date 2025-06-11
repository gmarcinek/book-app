"""
Zracjonalizowany LiricNER - KISS ale z zachowaniem jakości z pierwowzoru
"""

from typing import List, Dict, Any
from ..base import BaseNER, DomainConfig
from .liric_consts import (
    LIRIC_ENTITY_TYPES_FLAT,
    format_liric_entity_types,
    get_liric_confidence_threshold,
    LIRIC_CORE_INSTRUCTIONS,
    LIRIC_JSON_TEMPLATE,
    build_confidence_guide
)


class LiricNER(BaseNER):
    """
    Racjonalny NER dla poezji - uproszczony ale kompletny
    Zachowuje jakość z pierwowzoru, usuwa redundancje
    """
    
    def __init__(self):
        config = DomainConfig(
            name="liric",
            entity_types=LIRIC_ENTITY_TYPES_FLAT,
            confidence_threshold=0.3
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        return LIRIC_ENTITY_TYPES_FLAT
    
    def get_confidence_threshold(self, entity_type: str = None) -> float:
        if entity_type:
            return get_liric_confidence_threshold(entity_type)
        return self.config.confidence_threshold
    
    def get_meta_analysis_prompt(self, text: str) -> str:
        """
        META-PROMPT: Skrócony ale zachowuje kluczowe elementy z pierwowzoru
        Było: ~50 linii → Teraz: ~20 linii (60% redukcja)
        """
        entity_types_str = format_liric_entity_types()
        confidence_guide = build_confidence_guide()  # ← DYNAMICZNY
        
        return f"""Przeanalizuj tekst poetycki i stwórz SPERSONALIZOWANY PROMPT NER.

TEKST: {text}

ANALIZA (sprawdź):
• Typ liryki (miłosna/krajobrazowa/filozoficzna/inne)
• Dominujące figury poetyckie i środki stylistyczne
• Struktura kompozycyjna (zwrotki, rytm, organizacja)
• Kluczowe motywy symboliczne i obrazowe

WYMAGANIA DO PROMPTU:
• ZAWSZE szukaj: ZWROTKA, METAFORA, PORÓWNANIE, PERSONIFIKACJA
• Dostosuj instrukcje do specyfiki tego konkretnego tekstu
• Uwzględnij wykryte charakterystyczne elementy
• {confidence_guide.replace('CONFIDENCE POETRY:', 'Confidence:')}

DOSTĘPNE TYPY: {entity_types_str}

ZWRÓĆ JSON: {{"prompt": "Zidentyfikuj encje poetyckie w [typ_liryki]..."}}"""
    
    def get_base_extraction_prompt(self, text: str) -> str:
        """
        FALLBACK: Skrócony ale zachowuje aggressive search z pierwowzoru
        Było: ~40 linii → Teraz: ~25 linii (37% redukcja)
        """
        entity_types_str = format_liric_entity_types()
        confidence_guide = build_confidence_guide()  # ← DYNAMICZNY
        
        return f"""Zidentyfikuj encje poetyckie - SZUKAJ AGRESYWNIE wszystkich figur.

TEKST: {text}

{LIRIC_CORE_INSTRUCTIONS}

{confidence_guide}

TYPY: {entity_types_str}

INSTRUKCJE SEMANTYCZNE:
• ZWROTKA: strukturalne podziały tekstu
• PORÓWNANIE: eksplicytne zestawienia podobieństw
• PERSONIFIKACJA: atrybuty ludzkie nadane nieożywionym obiektom
• SYMBOL: obiekty reprezentujące głębsze znaczenia
• FENOMENON: wszelkie stany wewnętrzne podmiotu lirycznego
• ALIASES: uwzględnij wszystkie warianty nazewnicze

JSON: {LIRIC_JSON_TEMPLATE}"""
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
        """
        CUSTOM: Zachowuje strukturę z pierwowzoru ale uproszczona
        """
        entity_types_str = format_liric_entity_types()
        
        return f"""{custom_instructions}

TEKST POETYCKI: {text}

DOSTĘPNE TYPY: {entity_types_str}
FORMAT JSON: {LIRIC_JSON_TEMPLATE}

WYKONAJ EKSTRAKCJĘ - ZWRÓĆ TYLKO JSON:"""
    
    def validate_entity(self, entity_data: Dict[str, Any]) -> bool:
        """Walidacja z pierwowzoru - zachowana logika + FENOMENON"""
        if not entity_data.get('name') or not entity_data.get('type'):
            return False
        
        if entity_data['type'] not in self.get_entity_types():
            return False
        
        confidence = entity_data.get('confidence', 0.0)
        if confidence < 0.1 or confidence > 1.0:
            return False
        
        entity_type = entity_data['type']
        min_confidence = self.get_confidence_threshold(entity_type)
        
        # Zachowana permissive logika dla figur poetyckich
        if entity_type in ['METAFORA', 'SYMBOL', 'ALEGORIA'] and confidence >= 0.2:
            return True
        
        # Permissive dla psychologii (ważne w poezji)
        if entity_type in ['EMOCJA', 'MYŚL', 'NASTRÓJ'] and confidence >= 0.3:
            return True
        
        return confidence >= min_confidence
    
    def should_use_cleaning(self) -> bool:
        return False
    
    def get_domain_specific_config(self) -> Dict[str, Any]:
        """Zachowana konfiguracja z pierwowzoru"""
        return {
            "uses_poetic_structure": True,
            "supports_metaphors": True,
            "supports_symbolism": True,
            "supports_stylistic_figures": True,
            "confidence_strategy": "permissive_for_metaphors",
            "aliases_required": True,
            "context_heavy": True,
            "preserves_poetic_form": True,
            "uses_cleaning": False
        }