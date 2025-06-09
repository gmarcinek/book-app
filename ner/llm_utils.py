from llm import LLMClient
from .domains import DomainFactory
from .utils import load_ner_config

def call_llm_semantic_cleaning(text: str, model_name: str = None, domain_name: str = "literary") -> str:
    """
    Wysyła prompt czyszczący tekst do LLM - używa domain-specific logic
    """
    config = load_ner_config()
    model = model_name or config.get("default_model", "qwen-coder")
    client = LLMClient(
        model,
        max_tokens=8000,
        temperature=0.0,
    )

    # Get domain and check if it supports cleaning
    domain = DomainFactory.use([domain_name])[0]
    
    if not domain.should_use_cleaning():
        # Domain doesn't use cleaning - return original text
        print(f"Domain '{domain_name}' doesn't use semantic cleaning - returning original text")
        return text
    
    # Domain supports cleaning - use domain-specific prompt
    if hasattr(domain, 'get_semantic_cleaning_prompt'):
        prompt = domain.get_semantic_cleaning_prompt(text)
    else:
        # Fallback - return original if no cleaning method
        print(f"Domain '{domain_name}' doesn't implement semantic cleaning - returning original text")
        return text

    response = client.chat(prompt)
    return extract_clean_text_from_response(response)


def extract_clean_text_from_response(response: str) -> str:
    """
    Usuwa ewentualne formatowanie markdown z odpowiedzi (```)
    """
    response = response.strip()
    if response.startswith("```"):
        parts = response.split("```")
        if len(parts) >= 2:
            return parts[1].strip()
    return response