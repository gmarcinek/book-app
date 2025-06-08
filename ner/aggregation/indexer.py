# ner/aggregation/indexer.py

import json
from pathlib import Path
from typing import Dict, List, Optional
from ..utils import log_memory_usage


class EntityIndex:
    """
    Ładowanie i zarządzanie indeksami encji oraz aliasów.
    """
    def __init__(self, entities_dir: Path):
        self.entities_dir = entities_dir
        self.entity_index: Dict[str, str] = {}
        self.alias_index: Dict[str, str] = {}

    def load(self):
        """
        Ładuje indeksy encji i aliasów z plików `ent.*.json`.
        """
        self.entity_index.clear()
        self.alias_index.clear()

        entity_files = list(self.entities_dir.glob("ent.*.json"))
        loaded = 0
        aliases = 0

        for file in entity_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                eid = data.get("id")
                name = data.get("name", "").strip().lower()
                alias_list = data.get("aliases", [])

                if name and eid:
                    self.entity_index[name] = eid
                    loaded += 1

                    for alias in alias_list:
                        alias_norm = alias.strip().lower()
                        if alias_norm:
                            self.alias_index[alias_norm] = eid
                            aliases += 1

            except Exception as e:
                print(f"[Indexer] Nie można załadować {file}: {e}")

        log_memory_usage(f"Załadowano indeks encji: {loaded} encji, {aliases} aliasów")

    def find(self, name: str, aliases: Optional[List[str]] = None) -> Optional[str]:
        """
        Wyszukuje istniejący identyfikator encji po nazwie lub aliasach.
        """
        key = name.strip().lower()

        if key in self.entity_index:
            return self.entity_index[key]
        if key in self.alias_index:
            return self.alias_index[key]

        if aliases:
            for alias in aliases:
                ak = alias.strip().lower()
                if ak in self.entity_index:
                    return self.entity_index[ak]
                if ak in self.alias_index:
                    return self.alias_index[ak]

        return None
