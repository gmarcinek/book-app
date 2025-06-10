"""
Literary Domain Implementation - Backup/Fallback obecnego prompter systemu
Implementuje wszystkie metody z BaseNER używając literary_consts.py
"""

from typing import List, Dict, Any
from .base import BaseNER, DomainConfig
from .literary_consts import (
    LITERARY_ENTITY_TYPES_FLAT,
    LITERARY_META_ANALYSIS_CONTEXT,
    LITERARY_EXTRACTION_RULES,
    LITERARY_CONFIDENCE_GUIDE,
    LITERARY_SPECIAL_INSTRUCTIONS,
    LITERARY_ALIASES_EXAMPLES,
    LITERARY_JSON_TEMPLATE,
    format_literary_entity_types,
    format_literary_phenomenon_lines,
    get_literary_confidence_threshold
)


class LiteraryNER(BaseNER):
    """
    Literary/Autobiographical Domain NER
    Backup/fallback implementation of current prompter system
    """
    
    def __init__(self):
        config = DomainConfig(
            name="literary",
            entity_types=LITERARY_ENTITY_TYPES_FLAT,
            confidence_threshold=0.3,  # Lower for psychological content
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        """Get domain-specific entity types"""
        return LITERARY_ENTITY_TYPES_FLAT
    
    def get_confidence_threshold(self, entity_type: str = None) -> float:
        """Get confidence threshold for entity type"""
        if entity_type:
            return get_literary_confidence_threshold(entity_type)
        return self.config.confidence_threshold
    
    def get_meta_analysis_prompt(self, text: str) -> str:
        """
        META-PROMPT: Analizuje chunk i generuje spersonalizowany prompt NER
        Backup implementation of meta_analysis.py
        """
        entity_types_str = format_literary_entity_types()
        
        prompt = f"""Jesteś ekspertem od Named Entity Recognition. Twoim zadaniem jest przeanalizować podany fragment tekstu i utworzyć SPERSONALIZOWANY PROMPT do ekstrakcji encji specjalnie dopasowany do tego konkretnego fragmentu.

FRAGMENT TEKSTU DO ANALIZY:
{text}

{LITERARY_META_ANALYSIS_CONTEXT}

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
    
    def get_base_extraction_prompt(self, text: str) -> str:
        """
        Standard entity extraction prompt (FALLBACK)
        Backup implementation of entity_extraction.py
        """
        entity_types_str = format_literary_entity_types()
        phenomenon_examples = format_literary_phenomenon_lines()
        
        prompt = f"""Zidentyfikuj konkretne encje w tekście według ścisłych kryteriów.

TEKST:
{text}

{LITERARY_EXTRACTION_RULES}

DOSTĘPNE TYPY ENCJI:
{entity_types_str}

{LITERARY_CONFIDENCE_GUIDE}

STRUKTURA FENOMENÓW:
{phenomenon_examples}

ENCJE STRUKTURALNE:
- SCENA: spójny fragment akcji z określoną lokacją, uczestnikami i tematyką
  Przykład: "rozmowa_w_kuchni_o_planach" (lokacja: kuchnia, uczestnicy: narrator+matka, temat: planowanie)
- DIALOG: rozmowa między postaciami jako obiektywny fakt
  Przykład: "dialog_narratora_z_matką_o_jutrzejszych_planach"

{LITERARY_SPECIAL_INSTRUCTIONS}

{LITERARY_ALIASES_EXAMPLES}

FORMAT - TYLKO JSON:
{LITERARY_JSON_TEMPLATE}

JSON:"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str) -> str:
        """
        Buduje finalny prompt do ekstrakcji używając custom instructions z meta-prompt
        Backup implementation of custom_extraction.py
        """
        entity_types_str = format_literary_entity_types()
        
        final_prompt = f"""{custom_instructions}

TEKST DO ANALIZY:
{text}

DOSTĘPNE TYPY ENCJI (użyj tylko z tej listy):
{entity_types_str}

WYMAGANY FORMAT JSON:
{LITERARY_JSON_TEMPLATE}

WYKONAJ EKSTRAKCJĘ - ZWRÓĆ TYLKO JSON:"""
        
        return final_prompt
    
    def validate_entity(self, entity_data: Dict[str, Any]) -> bool:
        """Validate extracted entity for literary domain"""
        # Basic validation
        if not entity_data.get('name') or not entity_data.get('type'):
            return False
        
        # Check if entity type is in allowed list
        if entity_data['type'] not in self.get_entity_types():
            return False
        
        # Confidence validation
        confidence = entity_data.get('confidence', 0.0)
        if confidence < 0.1 or confidence > 1.0:
            return False
        
        # Literary-specific validation
        entity_type = entity_data['type']
        min_confidence = self.get_confidence_threshold(entity_type)
        
        # Allow lower confidence for psychological content
        if entity_type in ['FENOMENON', 'EMOCJA', 'MYŚL'] and confidence >= 0.2:
            return True
        
        return confidence >= min_confidence
    
    def should_use_cleaning(self) -> bool:
        """Whether this domain should use semantic cleaning"""
        return False  # Literary domain preserves raw text nuances
    
    def get_domain_specific_config(self) -> Dict[str, Any]:
        """Get domain-specific configuration"""
        return {
            "uses_phenomena": True,
            "supports_psychological_states": True,
            "supports_retrospection": True,
            "supports_scenes_and_dialogs": True,
            "confidence_strategy": "permissive_for_psychology",
            "aliases_required": True,
            "context_heavy": True,
            "preserves_raw_text": True,  # No semantic cleaning
            "uses_cleaning": False
        }