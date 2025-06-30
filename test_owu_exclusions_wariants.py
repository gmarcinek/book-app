#!/usr/bin/env python3
"""
Simple test: Find EXCLUSIONS from OWU document using GPT-4.1-nano
Tests if LLM can identify WYŁĄCZENIE_Z_UMOWY entities from the document
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from llm import LLMClient, LLMConfig, Models
from ner.domains.owu.owu_consts import format_owu_entity_types

def load_owu_document(file_path: str) -> str:
    """Load OWU markdown document"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"📄 Loaded document: {len(content):,} characters")
        return content
    except Exception as e:
        print(f"❌ Failed to load document: {e}")
        return ""

def test_find_exclusions(document_text: str) -> dict:
    """Test LLM ability to find exclusions from OWU document"""
    
    # Simple, clear NER prompt
    prompt = f"""Jesteś systemem NER (Named Entity Recognition) który wyciąga encje z dokumentów ubezpieczeniowych.

Twoje zadanie: znajdź wszystkie WARIANTY UBEZPIECZENIA oferowane w umowie.

TEKST DOKUMENTU:
{document_text}

SZUKAJ ODPOWIEDZI NA PYTANIA:
- Jakie rodzaje/typy ubezpieczenia są dostępne?
- Jakie są różne warianty ochrony ubezpieczeniowej?
- Jakie pakiety/plany ubezpieczenia oferuje umowa?
- Jakie są poziomy ochrony (basic, standard, premium)?

WZORCE DO SZUKANIA:
- "wariant", "rodzaj ubezpieczenia", "typ ochrony"
- "pakiet", "plan", "program ubezpieczeniowy"
- "opcja", "zakres", "poziom ochrony"
- "basic", "standard", "premium", "plus"
- Nazwy własne wariantów: "Ochrona Rodzinna", "Pakiet Senior"
- Listy z opcjami: a), b), c) lub 1., 2., 3.
- Tabele z wariantami i ich parametrami

INSTRUKCJE:
1. Każdy wariant/typ/pakiet = osobna encja
2. Zapisz dokładnie w którym artykule/punkcie znalazłeś
3. Nazwa = oficjalna nazwa wariantu z dokumentu
4. Description = co obejmuje dany wariant, jakie ma cechy
5. Aliases = różne sposoby nazywania tego wariantu

JSON:
{{
 "entities": [
   {{
     "type": "INSURANCE_VARIANT",
     "name": "oficjalna_nazwa_wariantu",
     "description": "szczegółowy opis wariantu ubezpieczenia, co obejmuje, jakie ma limity, dla kogo jest przeznaczony, jakie świadczenia oferuje, minimum 10 słów dla wyszukiwarki embedera",
     "confidence": 0.9,
     "evidence": "art X, pkt Y + fragment opisujący wariant",
     "aliases": ["alternatywne nazwy", "skróty", "potoczne określenia"]
   }}
 ]
}}

Zwróć TYLKO JSON bez komentarzy."""

    # Initialize LLM client
    print(f"🤖 Using model: {Models.GPT_4_1_MINI}")
    llm_client = LLMClient(Models.GPT_4_1_MINI)
    config = LLMConfig(temperature=0.0, max_tokens=24000)
    
    try:
        print("🔍 Sending request to LLM...")
        response = llm_client.chat(prompt, config)
        print(f"✅ Got response: {len(response)} characters")
        return {
            "status": "success",
            "response": response,
            "prompt_length": len(prompt),
            "response_length": len(response)
        }
    except Exception as e:
        print(f"❌ LLM request failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def parse_and_display_results(response_data: dict):
    """Parse LLM response and display results"""
    if response_data["status"] != "success":
        print(f"❌ Test failed: {response_data['error']}")
        return
    
    response = response_data["response"]
    
    # Try to parse JSON
    try:
        import json
        
        # Clean response
        clean_response = response.strip()
        if '```json' in clean_response:
            clean_response = clean_response.split('```json')[1].split('```')[0]
        elif '```' in clean_response:
            parts = clean_response.split('```')
            if len(parts) >= 3:
                clean_response = parts[1]
        
        data = json.loads(clean_response.strip())
        entities = data.get('entities', [])
        
        print(f"\n🎯 RESULTS: FOUND {len(entities)} WARIANTS")
        print("=" * 80)
        
        for i, entity in enumerate(entities, 1):
            name = entity.get('name', 'Unknown')
            description = entity.get('description', '')
            confidence = entity.get('confidence', 0.0)
            evidence = entity.get('evidence', '')
            
            print(f"\n{i}. {name}")
            print(f"   📝 Description: {description}")
            print(f"   📊 Confidence: {confidence}")
            print(f"   🔍 Evidence: {evidence[:100]}...")
        
        print("=" * 80)
        print(f"📊 Stats: {response_data['prompt_length']:,} chars prompt → {response_data['response_length']:,} chars response")
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"Raw response: {response[:500]}...")
    except Exception as e:
        print(f"❌ Error processing results: {e}")

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OWU Exclusions Test - GPT-4.1-nano")
    parser.add_argument("file_path", help="Path to OWU document (e.g., docs/owu_COMBINED_5281a67c.md)")
    args = parser.parse_args()
    
    print("🧪 OWU Exclusions Test - GPT-4.1-nano")
    print("=" * 50)
    
    # Load document from provided path
    document_text = load_owu_document(args.file_path)
    
    if not document_text:
        print("❌ No document loaded, exiting")
        return
    
    # Test finding exclusions
    print("\n🔍 Testing exclusion detection...")
    results = test_find_exclusions(document_text)
    
    # Display results
    print("\n📋 Processing results...")
    parse_and_display_results(results)

if __name__ == "__main__":
    main()