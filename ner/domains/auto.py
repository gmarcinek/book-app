"""
AutoNER - Domain Classifier (not a real NER domain)
Classifies text chunks to determine appropriate domains
"""

import json
import logging
from typing import List, Callable

logger = logging.getLogger(__name__)


class AutoNER:
    """Domain classifier - determines which domains to use for a text chunk"""
    
    def __init__(self):
        pass
    
    def classify_chunk(self, text: str) -> List[str]:
        """
        Classify text chunk and return list of appropriate domain names
        
        Args:
            text: Text chunk to classify
            
        Returns:
            List of domain names (e.g. ["literary"] or ["liric"] or ["literary", "liric"])
        """
        prompt = self._get_classification_prompt(text)
        
        # This would be called by the extractor with its LLM client
        # For now, return a placeholder - actual implementation needs LLM access
        return self._parse_classification_response("")
    
    def _get_classification_prompt(self, text: str) -> str:
        """Generate classification prompt for the text"""
        return f"""Sklasyfikuj tekst do których grup można go przypisać:

MOŻLIWE GRUPY:
1. literary - proza, narracja, opisy, dialogi, wspomnienia, autobiografia, tekst literacki
2. liric - poezja, wersy, rymy, figury poetyckie, symbolika, tekst poetycki
3. simple - podstawowe encje (osoby, miejsca, organizacje, przedmioty, wydarzenia, czas)
4. owu - dokumenty prawne, regulaminy, OWU, polisy, definicje formalne, artykuły, świadczenia, ograniczenia

TEKST DO KLASYFIKACJI:
{text}

ZASADY:
- Jeśli tekst jest jednoznacznie poetycki (wersy, rymy, strofy) → ["liric"]
- Jeśli tekst jest prozą/narracją → ["literary"] 
- Jeśli tekst zawiera głównie podstawowe informacje → ["simple"]
- Jeśli niepewny lub mieszany → ["literary", "simple"]
- Jeśli bardzo niepewny → ["simple"] (fallback)
- Jeśli tekst zawiera terminy prawne (np. „Ubezpieczyciel”, „Polisa”, „świadczenie”, „OWU”) → ["owu"]

ZWRÓĆ TYLKO JSON:
{{"domains": ["domain1", "domain2"]}}"""
    
    def _parse_classification_response(self, response: str) -> List[str]:
        """Parse LLM response to extract domain names"""
        try:
            # Clean response
            clean_response = response.strip()
            
            # Handle code blocks
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                parts = clean_response.split('```')
                if len(parts) >= 3:
                    clean_response = parts[1]
            
            # Parse JSON
            data = json.loads(clean_response.strip())
            
            if isinstance(data, dict) and 'domains' in data:
                domains = data['domains']
            elif isinstance(data, list):
                domains = data
            else:
                logger.warning(f"⚠️ Unexpected classification response format: {type(data)}")
                return ["simple"]  # fallback
            
            # Validate domains
            valid_domains = []
            available_domains = ["literary", "liric", "simple", "owu"]
            
            for domain in domains:
                if isinstance(domain, str) and domain in available_domains:
                    valid_domains.append(domain)
            
            # Ensure we have at least one domain
            if not valid_domains:
                logger.warning("⚠️ No valid domains found in classification, using fallback")
                return ["simple"]
            
            return valid_domains
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse classification JSON: {e}")
            return ["simple"]  # fallback
        except Exception as e:
            logger.error(f"❌ Error parsing classification response: {e}")
            return ["simple"]  # fallback
    
    def classify_chunk_with_llm(self, text: str, llm_call_function: Callable[[str], str]) -> List[str]:
        """
        Classify chunk using provided LLM call function
        
        Args:
            text: Text to classify
            llm_call_function: Function that takes prompt and returns LLM response
            
        Returns:
            List of domain names
        """
        try:
            prompt = self._get_classification_prompt(text)
            response = llm_call_function(prompt)
            domains = self._parse_classification_response(response)
            
            logger.info(f"🔍 Auto-classified chunk: {domains}")
            return domains
            
        except Exception as e:
            logger.error(f"❌ Auto-classification failed: {e}")
            return ["simple"]  # fallback