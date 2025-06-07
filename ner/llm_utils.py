from llm import LLMClient
from .prompts import NERPrompts
from .utils import load_ner_config

def call_llm_semantic_cleaning(text: str, model_name: str = None) -> str:
    """
    Wysyła prompt czyszczący tekst wspomnieniowy do LLM i zwraca czystą wersję.
    """
    config = load_ner_config()
    model = model_name or config.get("default_model", "qwen-coder")
    client = LLMClient(
        model,
        max_tokens=5000,
        temperature=0.0,
    )

    prompt = NERPrompts.get_semantic_cleaning_prompt(text)
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