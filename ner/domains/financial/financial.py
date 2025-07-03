"""
Financial Domain Implementation - Invoices, receipts, payments
"""

from typing import List
from ner.domains.base import BaseNER, DomainConfig
from ner.types import DEFAULT_ENTITY_TYPES, DEFAULT_CONFIDENCE_THRESHOLDS

class FinancialNER(BaseNER):
    """Financial NER Domain for invoices, receipts, and financial documents"""
    
    def __init__(self):
        config = DomainConfig(
            name="financial",
            entity_types=["FAKTURA", "KWOTA", "FIRMA", "TOWAR", "DATA_PLATNOSCI", "NUMER_KONTA", "NIP", "ADRES"],
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLDS["entity_extraction"],
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        return ["FAKTURA", "KWOTA", "FIRMA", "TOWAR", "DATA_PLATNOSCI", "NUMER_KONTA", "NIP", "ADRES"]
    
    def get_meta_analysis_prompt(self, text: str, contextual_entities: List[dict] = None) -> str:
        """META-PROMPT: Analyze financial documents"""
        
        contextual_info = ""
        if contextual_entities:
            contextual_info = "\n\nKONTEKST Z POPRZEDNICH DOKUMENTÓW:\n"
            for entity_data in contextual_entities:
                name = entity_data.get('name', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')
                
                contextual_info += f"- {name} ({entity_type}): {description}...\n"
        
        prompt = f"""Przeanalizuj dokument finansowy i stwórz SPERSONALIZOWANY PROMPT NER.

{contextual_info}

TEKST DOKUMENTU FINANSOWEGO:
{text}

ANALIZA:
- Faktury, paragony, potwierdzenia płatności
- Kwoty pieniężne (brutto, netto, VAT)
- Firmy (sprzedawca, nabywca)
- Towary i usługi
- Daty płatności i wystawienia
- Numery kont bankowych
- Numery NIP
- Adresy firm

DOSTĘPNE TYPY ENCJI:
FAKTURA, KWOTA, FIRMA, TOWAR, DATA_PLATNOSCI, NUMER_KONTA, NIP, ADRES

ZWRÓĆ GOTOWY PROMPT NER BEZ JSON WRAPPERA:"""
           
        return prompt

    def get_base_extraction_prompt(self, text: str) -> str:
        """FALLBACK: Simple financial document extraction"""

        prompt = f"""Jesteś agentem AI wyspecjalizowanym w analizie dokumentów finansowych.

DOKUMENT FINANSOWY:
{text}

TYPY ENCJI:
- FAKTURA: numery faktur, rachunków
- KWOTA: kwoty pieniężne (brutto, netto, VAT)
- FIRMA: nazwy firm (sprzedawca, nabywca)
- TOWAR: nazwy towarów i usług
- DATA_PLATNOSCI: terminy płatności
- NUMER_KONTA: numery rachunków bankowych
- NIP: numery identyfikacji podatkowej
- ADRES: adresy firm

ZWRÓĆ TYLKO JSON:
{{
    "entities": [
        {{
            "name": "Faktura VAT 2024/001",
            "type": "FAKTURA", 
            "description": "numer dokumentu sprzedażowego",
            "confidence": 0.9
        }}
    ]
}}"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        """Custom extraction for financial documents"""
        
        aliases_info = ""
        if known_aliases:
            aliases_info = "\n\nZNANE PODMIOTY FINANSOWE:\n"
            
            for entity_data in known_aliases:
                name = entity_data.get('name', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')
                
                aliases_info += f"- '{name}' ({entity_type}): {description}\n"

        final_prompt = f"""{custom_instructions}

{aliases_info}

DOKUMENT FINANSOWY:
{text}

DOSTĘPNE TYPY ENCJI:
FAKTURA, KWOTA, FIRMA, TOWAR, DATA_PLATNOSCI, NUMER_KONTA, NIP, ADRES

ZASADY:
- Wyciągnij wszystkie kwoty z walutą
- Zidentyfikuj firmy (sprzedawca/nabywca)
- Znajdź numery dokumentów
- Wypisz wszystkie towary/usługi

ZWRÓĆ TYLKO JSON:
{{
    "entities": [
        {{
            "name": "nazwa encji",
            "type": "TYP_Z_LISTY",
            "description": "semantyczny opis encji finansowej",
            "confidence": 0.9
        }}
    ]
}}"""
        
        return final_prompt
    
    def should_use_cleaning(self) -> bool:
        return False