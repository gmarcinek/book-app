"""
NER Utils - Memory monitoring, validation, ID generation
Memory-safe utilities for NER processing
"""

import os
import json
import time
import hashlib
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, List


def load_ner_config(config_path: str = "ner/ner_config.json") -> Dict[str, Any]:
    """Load NER configuration from JSON file"""
    try:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
    
    # Fallback defaults
    return {
        "max_tokens": 8000,
        "chunk_size": 8000,
        "chunk_overlap": 400,
        "max_iterations": 100,
        "min_entity_length": 2,
        "max_entity_length": 100,
        "enable_memory_monitoring": True
    }


def log_memory_usage(stage: str = ""):
    """Monitor RAM usage to detect memory leaks"""
    config = load_ner_config()
    if not config.get("enable_memory_monitoring", True):
        return
    
    usage = psutil.virtual_memory()
    print(f"[MEMORY] {stage}: {usage.percent:.1f}% ({usage.used // (1024 ** 2)} MB used, {usage.available // (1024 ** 2)} MB free)")


def generate_entity_id(name: str, entity_type: str) -> str:
    """Generate unique entity ID"""
    timestamp = str(int(time.time() * 1000000))  # microsecond precision
    hash_input = f"{name}_{entity_type}_{timestamp}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    return f"ent.{timestamp}.{hash_suffix}"


def validate_entity_name(name: str) -> bool:
    """Validate entity name length"""
    if not name or not isinstance(name, str):
        return False
    
    config = load_ner_config()
    min_len = config.get("min_entity_length", 2)
    max_len = config.get("max_entity_length", 100)
    
    name_stripped = name.strip()
    return min_len <= len(name_stripped) <= max_len


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
    
    # Check reasonable size (not too big for memory)
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
    """Clean text for processing - remove extra whitespace, normalize"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize line endings
    cleaned = " ".join(text.split())
    return cleaned.strip()


def safe_filename(name: str, max_length: int = 50) -> str:
    """Convert name to safe filename"""
    if not name:
        return "unnamed"
    
    # Remove unsafe characters
    safe_name = "".join(c for c in name if c.isalnum() or c in "._- ")
    safe_name = safe_name.replace(" ", "_").strip("._-")
    
    # Truncate if too long
    if len(safe_name) > max_length:
        safe_name = safe_name[:max_length].rstrip("._-")
    
    return safe_name or "unnamed"

def load_entities_from_directory(entities_dir: Path) -> List[Dict[str, Any]]:
    """
    Load all JSON entity files from the given directory and return them as a list of dicts.
    Ignores non-JSON files and errors on invalid JSON.
    """
    entities = []
    for file in entities_dir.glob("*.json"):
        try:
            with open(file, encoding="utf-8") as f:
                entity = json.load(f)
                entities.append(entity)
        except Exception as e:
            print(f"[WARN] Failed to load entity file {file.name}: {e}")
    return entities