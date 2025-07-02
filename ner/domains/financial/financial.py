"""
financial Domain Implementation - Clean and simplified
"""

from typing import List
from ..base import BaseNER, DomainConfig
from ...entity_config import DEFAULT_ENTITY_TYPES, DEFAULT_CONFIDENCE_THRESHOLDS

class FinancialNER(BaseNER):
    """FinancialNER Domain with clean entity types and relationship extraction"""
    
    def __init__(self):
        config = DomainConfig(
            name="financial",
            entity_types=DEFAULT_ENTITY_TYPES,
            confidence_threshold=DEFAULT_CONFIDENCE_THRESHOLDS["entity_extraction"],
        )
        super().__init__(config)
    
    def get_entity_types(self) -> List[str]:
        return DEFAULT_ENTITY_TYPES
    
    def get_meta_analysis_prompt(self, text: str, contextual_entities: List[dict] = None) -> str:
        """META-PROMPT: Clean and focused"""
        prompt = f"""Przeanalizuj tekst i stwórz SPERSONALIZOWANY PROMPT NER.
TEKST: {text}

ANALIZA:
- Nazwane organizacje / Firmy (INSTITUTION)
- Osoby (PERSON)
- Forma płatnośc (PAYMENT_TYPE)
- Role (ROLE)
- Konta bankowe (IBAN)
- Tytuł przelewu (PAYMENT_DESCRIPTION)
- Numer faktury (INVOICE_NUMBER)
- Określone daty / godziny(DATE)
- Numery Rejestracyjne / kody / klucze / PESEL / NIP / REGON (CODE)
- Konkretne adresy (ADDRESS)
- Przedmioty / Produkty (ITEM)

ZWRÓĆ GOTOWY PROMPT BEZ JSON WRAPPERA:"""
           
        return prompt

    def get_base_extraction_prompt(self, text: str) -> str:
        """FALLBACK: Simple and direct"""

        prompt = f"""Jesteś agentem AI wyspecjalizowanym w Named Entity Recognition.

TEKST: {text}

TYPY ENCJI:
{', '.join([
"INSTITUTION",
"PERSON",
"PAYMENT_TYPE",
"ROLE",
"IBAN",
"PAYMENT_DESCRIPTION",
"INVOICE_NUMBER",
"DATE",
"CODE",
"ADDRESS",
"ITEM"
])}

ZASADY:
- Forma podstawowa
- Tylko encje jawnie obecne
- Aliases: wszystkie warianty nazwy

JSON:
{{
    "entities": [
        {{
            "name": "Jan Kowalski",
            "type": "PERSON", 
            "description": "semantycznie użyteczny opis dla wyszukiwarki embedera, używaj wiedzy z tekstu i wiedzy ogólnej o świecie jednocześnie bądź precyzyjny jak matematyk opisujacy to co widzi",
            "evidence": "nabywca: Jan Kowalski...",
            "aliases": ["Jan", "Kowalski", "Nabywca"],
            "confidence": 0.85
        }}
    ]
 ]
}}"""
        return prompt
    
    def build_custom_extraction_prompt(self, text: str, custom_instructions: str, known_aliases: dict = None) -> str:
        """FinancialNer: ekstrakcja danych finansowych i kontraktowych"""
        aliases_info = ""
        if known_aliases:
            aliases_info = "\n\nZNANE ENCJE Z KONTEKSTEM (uwzględnij w ekstrakcji):\n"
            
            for entity_data in known_aliases:
                name = entity_data.get('name', '')
                entity_id = entity_data.get('id', '')
                entity_type = entity_data.get('type', '')
                description = entity_data.get('description', '')[:350]
                aliases = entity_data.get('aliases', [])
                confidence = entity_data.get('confidence', 0.0)
                
                aliases_str = ", ".join(aliases) if aliases else "brak"
                aliases_info += f"- '{name}' ({entity_type}): {description}\n"
                aliases_info += f"  Aliases: [{aliases_str}] | Confidence: {confidence:.2f}\n\n"
            
            aliases_info += "UWAGA: Jeśli znajdziesz te encje lub ich aliases, użyj głównej nazwy jako 'name', zachowaj lub poszerz description, dodaj aliases.\n"

        return f"""{custom_instructions}

    ZADANIE: Wyodrębnij wszystkie wystąpienia encji finansowych i kontraktowych z podanego tekstu. Skup się na następujących typach:
    - numery faktur (np. "FV/2023/07/15")
    - numery kont bankowych (np. IBAN)
    - instytucje (banki, urzędy, firmy)
    - osoby (w kontekście występujących nazwisk lub pełnych imion)
    - towary lub przedmioty świadczeń (np. "abonament", "usługa ochrony", "paliwo", "czujnik alarmowy")

    Każdą encję oznacz odpowiednim typem i dołącz dowód cytatu z tekstu (evidence). Ustal także aliases i poziom pewności (confidence).

    {aliases_info}
    TEKST: {text}

    JSON (EVIDENCE obowiązkowy):
    {{
    "entities": [
        {{
        "name": "deskryptywna_nazwa_podstawowa",
        "type": "TYP_Z_LISTY", 
        "description": "semantycznie użyteczny opis dla wyszukiwarki embedera, minimalna długość to 10 słów, spróbuj powiedzieć i ekstrapolować jak najwięcej można prawdziwych stwierdzeń na temat encji",
        "confidence": 0.X,
        "evidence": "cytat lub lokalizacja w tekście",
        "aliases": ["alias1", "alias2"]
        }}
    ]
    }}"""
        
        return final_prompt
    
    def should_use_cleaning(self) -> bool:
        return False