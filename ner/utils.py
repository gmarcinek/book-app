"""
NER Utils - Memory monitoring, validation, ID generation, simple JSON parsing
"""

import os
import json
import time
import hashlib
import psutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def log_memory_usage(stage: str = ""):
    """Monitor RAM usage to detect memory leaks"""
    try:
        usage = psutil.virtual_memory()
        print(f"📈 [MEMORY] {stage}: {usage.percent:.1f}% ({usage.used // (1024 ** 2)} MB used, {usage.available // (1024 ** 2)} MB free)")
    except Exception:
        # Fail silently if psutil not available
        pass


def generate_entity_id(name: str, entity_type: str) -> str:
    """Generate unique entity ID"""
    timestamp = str(int(time.time() * 1000000))
    hash_input = f"{name}_{entity_type}_{timestamp}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"ent.{timestamp}.{hash_suffix}"


def validate_entity_name(name: str) -> bool:
    """Validate entity name length"""
    if not name or not isinstance(name, str):
        return False
    
    name_stripped = name.strip()
    # Basic length validation - reasonable limits
    return 2 <= len(name_stripped) <= 100


def validate_file_exists(file_path: str) -> bool:
    """Check if file exists and is readable"""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file() and os.access(path, os.R_OK)
    except Exception:
        return False


def validate_text_content(text: str) -> bool:
    """Validate text content is not empty and reasonable size"""
    if not text or not isinstance(text, str):
        return False
    
    text_stripped = text.strip()
    if not text_stripped:
        return False
    
    max_size = 50 * 1024 * 1024  # 50MB text limit
    return len(text_stripped.encode('utf-8')) <= max_size


def validate_entity_type(entity_type: str) -> bool:
    """Validate entity type is non-empty string"""
    if not entity_type or not isinstance(entity_type, str):
        return False
    
    entity_type_stripped = entity_type.strip()
    return len(entity_type_stripped) > 0


def get_file_size_mb(file_path: str) -> Optional[float]:
    """Get file size in MB, return None if error"""
    try:
        size_bytes = Path(file_path).stat().st_size
        return size_bytes / (1024 * 1024)
    except Exception:
        return None


def check_memory_available(required_mb: float = 100.0) -> bool:
    """Check if enough memory is available for processing"""
    try:
        memory = psutil.virtual_memory()
        available_mb = memory.available / (1024 * 1024)
        return available_mb >= required_mb
    except Exception:
        return True  # Assume OK if can't check


def cleanup_text(text: str) -> str:
    """Clean text for processing - preserve line breaks but normalize spacing"""
    if not text:
        return ""
    
    # Split by lines, clean each line individually, rejoin with \n
    lines = text.split('\n')
    cleaned_lines = [' '.join(line.split()) for line in lines]  # Normalize spaces within each line
    return '\n'.join(cleaned_lines).strip()


def safe_filename(name: str, max_length: int = 50) -> str:
    """Convert name to safe filename"""
    if not name:
        return "unnamed"
    
    safe_name = "".join(c for c in name if c.isalnum() or c in "._- ")
    safe_name = safe_name.replace(" ", "_").strip("._-")
    
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length].rstrip("._-")
    
    return safe_name or "unnamed"


def load_entities_from_directory(entities_dir: Path) -> List[Dict[str, Any]]:
    """Load all JSON entity files from directory"""
    entities = []
    for file in entities_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                entity = json.load(f)
                entities.append(entity)
        except Exception as e:
            print(f"⚠️ [WARN] Failed to load entity file {file.name}: {e}")
    return entities


# === SIMPLE JSON PARSING FOR LLM RESPONSES ===

def parse_llm_json_response(response: str, expected_key: str = None) -> Optional[dict]:
    """Simple JSON parsing for LLM responses - no overthinking"""
    try:
        if not response or '{' not in response:
            return None
        
        # Basic cleanup only
        clean = response.strip().replace('```json', '').replace('```', '')
        clean = clean.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        data = json.loads(clean)
        
        if expected_key and expected_key not in data:
            return None
        
        return data
        
    except Exception:
        return None  # Just fallback, don't log noise
    

import re

def parse_markdown_table(table_lines):
    headers = [h.strip() for h in table_lines[0].strip('|').split('|')]
    rows = table_lines[2:]  # pomijamy separator z myślnikami
    parsed_rows = []

    for line in rows:
        if not line.strip().startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        row_text = '; '.join(f"{k}: {v}" for k, v in zip(headers, cells))
        parsed_rows.append(row_text)

    return parsed_rows

def markdown_to_plain_text(md_text: str) -> str:
    lines = md_text.split('\n')
    result_lines = []
    in_table = False
    table_block = []

    for line in lines:
        # Detekcja początku tabeli
        if re.match(r'^\s*\|.*\|\s*$', line):
            table_block.append(line)
            in_table = True
        elif in_table and re.match(r'^\s*\|[-:\s|]+\|\s*$', line):
            table_block.append(line)
        elif in_table and re.match(r'^\s*\|.*\|\s*$', line):
            table_block.append(line)
        elif in_table:
            # koniec tabeli
            result_lines.extend(parse_markdown_table(table_block))
            in_table = False
            table_block = []
            result_lines.append(line.strip())  # kontynuuj analizę dla pozostałych linii
        else:
            # zwykły tekst markdown bez formatowania
            plain_line = re.sub(r'\*\*(.*?)\*\*', r'\1', line)  # bold
            plain_line = re.sub(r'\*(.*?)\*', r'\1', plain_line)  # italic
            plain_line = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', plain_line)  # link
            plain_line = re.sub(r'^#+\s*', '', plain_line)  # nagłówki
            plain_line = re.sub(r'`([^`]*)`', r'\1', plain_line)  # inline code
            result_lines.append(plain_line.strip())

    # jeśli tabela była na końcu
    if in_table:
        result_lines.extend(parse_markdown_table(table_block))

    return '\n'.join([line for line in result_lines if line.strip()])
