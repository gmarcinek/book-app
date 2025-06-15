# ner/aggregation/file_manager.py

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..utils import generate_entity_id, validate_file_exists
from ..config import NERConfig, create_default_ner_config
from .indexer import EntityIndex


class EntityFileManager:
    """
    Odpowiedzialny za tworzenie i aktualizowanie plików encji.
    """
    def __init__(self, entities_dir: Path, config: Optional[NERConfig] = None):
        self.entities_dir = Path(entities_dir)
        self.entities_dir.mkdir(parents=True, exist_ok=True)
        
        # Use provided config or create default
        self.config = config if config is not None else create_default_ner_config()
        
        self.indexer = EntityIndex(self.entities_dir)
        self.indexer.load()

    def create_or_update_entity(
        self, entity_data: Dict[str, Any], chunk_refs: List[str]
    ) -> tuple[Optional[str], bool, int]:
        """
        Tworzy lub aktualizuje plik encji. Zwraca:
        - id encji
        - czy została stworzona
        - liczba zaindeksowanych aliasów
        """
        name = entity_data.get("name", "").strip()
        etype = entity_data.get("type", "").strip()
        aliases = entity_data.get("aliases", []) or []

        if not name or not etype:
            print(f"⚠️ [FileManager] Nieprawidłowe dane encji: brak 'name' lub 'type'")
            return None, False, 0

        entity_id = self.indexer.find(name, aliases)
        created = False

        if entity_id:
            # 🔄 Aktualizacja istniejącej encji
            entity_file = self.entities_dir / f"{entity_id}.json"
            if entity_file.exists():
                existing = self._load_entity(entity_file)
                updated = self._merge(existing, entity_data, chunk_refs)
                self._write(entity_file, updated)
                alias_count = len(updated.get("aliases", []))
                return entity_id, False, alias_count
        else:
            # ✨ Tworzenie nowej encji
            entity_id = generate_entity_id(name, etype)
            entity_data["id"] = entity_id
            new_entity = self._format_new(entity_data, chunk_refs)
            entity_file = self.entities_dir / f"{entity_id}.json"
            self._write(entity_file, new_entity)
            created = True
            alias_count = len(new_entity.get("aliases", []))
            return entity_id, True, alias_count

        return None, False, 0

    def _load_entity(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, path: Path, data: Dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _merge(
        self, existing: Dict[str, Any], new: Dict[str, Any], chunk_refs: List[str]
    ) -> Dict[str, Any]:
        # 📊 Confidence - wybierz wyższą
        if new.get("confidence", 0) > existing.get("confidence", 0):
            existing["confidence"] = new["confidence"]

        # 📝 Description - wybierz dłuższy
        if len(new.get("description", "")) > len(existing.get("description", "")):
            existing["description"] = new["description"]
        
        if len(new.get("evidence", "")) > len(existing.get("evidence", "")):
            existing["evidence"] = new["evidence"]
    
        # 🏷️ Aliases - merge wszystkich
        old_aliases = set(existing.get("aliases", []))
        new_aliases = set(new.get("aliases", []))
        all_aliases = (old_aliases | new_aliases) - {existing.get("name", "").lower()}
        existing["aliases"] = sorted(all_aliases)

        # 🔗 Source info - merge referencji
        src = existing.setdefault("source_info", {})
        old_refs = set(src.get("chunk_references", []))
        old_refs.update(chunk_refs)
        src["chunk_references"] = sorted(old_refs)

        existing_chunks = set(src.get("found_in_chunks", []))
        incoming_chunks = set(new.get("source_info", {}).get("found_in_chunks", []))
        src["found_in_chunks"] = sorted(existing_chunks | incoming_chunks)

        # ⏰ Metadata - update timestamp
        existing.setdefault("metadata", {})["last_updated"] = datetime.now().isoformat()

        return existing

    def _format_new(self, entity_data: Dict[str, Any], chunk_refs: List[str]) -> Dict[str, Any]:
        return {
            "id": entity_data["id"],
            "name": entity_data["name"],
            "type": entity_data["type"],
            "description": entity_data.get("description", ""),
            "evidence": entity_data.get("evidence", ""),
            "confidence": entity_data.get("confidence", 0.5),
            "aliases": entity_data.get("aliases", []),
            "source_info": {
                "chunk_references": chunk_refs,
                "found_in_chunks": entity_data.get("source_info", {}).get("found_in_chunks", []),
                "source_document": entity_data.get("source_info", {}).get("source_document", "unknown")
            },
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "model_used": entity_data.get("metadata", {}).get("model_used", "unknown"),
                "extraction_method": entity_data.get("metadata", {}).get("extraction_method", "unknown")
            }
        }