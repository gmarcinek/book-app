#!/usr/bin/env python3
"""
Test GPT-5 TOC Processing - TEXT ONLY (bez vision)
"""

from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from llm import LLMClient, LLMConfig


def test_gpt5_toc_text_only():
    """Test GPT-5 na rzeczywistym TOC tekście BEZ obrazów"""
    print("📋 Testing GPT-5 TOC processing (text only)...")
    
    # Rzeczywisty tekst z owu2.pdf
    toc_text = """Spis treści
Ogólne warunki ubezpieczenia na życie „Ochrona jutra" ...4
Art. 1 		 Co oznaczają używane pojęcia?...4
Art. 2 	 Kogo ubezpieczamy w ramach Umowy podstawowej i w jakim zakresie? ...5
Art. 3 	 Kiedy rozpoczyna się ochrona ubezpieczeniowa i gdzie działa ubezpieczenie? ...5
Art. 4 	 W jaki sposób jest zawierana Umowa?...5
Art. 5 	 W jaki sposób można objąć ochroną kolejną osobę? ...6
Art. 6 	 Jak długo trwa Umowa? ...6
Art. 7 	 W jaki sposób Umowa dodatkowa może zostać przedłużona? ...7
Art. 8 	 W jaki sposób można zrezygnować z przedłużenia Umowy dodatkowej? ...7
Art. 9 	 Jaka jest wysokość Składki i w jaki sposób ją opłacać? Kiedy przysługuje jej zwrot? ...7
Art. 10	 Jak podwyższyć lub obniżyć Sumę ubezpieczenia? ...8
Art. 11 	 Co to jest indeksacja? ...8
Art. 12 	Jakie są obowiązki Właściciela polisy i Ubezpieczonego? ...8
Art. 13 	Komu i jaką kwotę wypłacimy po śmierci Ubezpieczonego? ...9
Art. 14 	Kiedy wypłacimy Świadczenie? ...9
Art. 15 	W jakich sytuacjach nie udzielamy ochrony ubezpieczeniowej i nie wypłacimy pieniędzy? ...10"""
    
    try:
        client = LLMClient(model="gpt-5")
        
        config = LLMConfig(
            temperature=1.0,  # GPT-5 default
            reasoning_effort="low"  # Stable setting
        )
        
        # Simplified prompt - TEXT ONLY
        prompt = f"""Parse this Table of Contents into JSON format.

TEXT:
{toc_text}

Return a JSON object with "entries" array. Each entry should have:
- "title": entry title 
- "page": page number (integer)
- "level": hierarchy level (1=main, 2=sub)
- "type": "chapter" or "section"

Respond ONLY with valid JSON, no markdown.
"""
        
        print("📡 Sending TEXT-ONLY prompt to GPT-5...")
        response = client.chat(prompt, config)  # NO IMAGES
        
        print(f"✅ GPT-5 Response:\n{response}")
        
        # Try to parse JSON
        import json
        try:
            data = json.loads(response.strip())
            entries = data.get("entries", [])
            
            print(f"\n📊 Parsed {len(entries)} entries:")
            for i, entry in enumerate(entries[:5]):  # Show first 5
                level = entry.get('level', 'NULL')
                title = entry.get('title', 'NO_TITLE')[:50]
                page = entry.get('page', 'NULL')
                print(f"  {i+1}. Level={level}, Page={page}, Title='{title}...'")
            
            # Check for NULL levels
            null_levels = [e for e in entries if e.get('level') is None]
            if null_levels:
                print(f"❌ Found {len(null_levels)} entries with NULL level")
                return False
            else:
                print(f"✅ All entries have valid levels!")
                return True
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ GPT-5 TOC test failed: {e}")
        return False


if __name__ == "__main__":
    if test_gpt5_toc_text_only():
        print("\n🎉 GPT-5 TOC TEXT-ONLY test PASSED!")
        sys.exit(0)
    else:
        print("\n❌ GPT-5 TOC TEXT-ONLY test FAILED!")
        sys.exit(1)