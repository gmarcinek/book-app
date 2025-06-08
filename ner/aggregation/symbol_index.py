# ner/aggregation/symbol_index.py

from typing import Dict, List, Any


class SymbolIndex:
    """
    Tworzy indeks symboli (nazwy, aliasy) oraz wykrywa duplikaty.
    """
    def create_symbol_index(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        symbols = {}
        alias_map = {}
        name_variants = {}

        for entity in entities:
            name = entity.get("name", "").strip()
            entity_id = entity.get("id", "")
            entity_type = entity.get("type", "")
            aliases = entity.get("aliases", [])

            if not name or not entity_id:
                continue

            name_lower = name.lower()
            name_clean = name_lower.replace("a", "").replace("y", "").replace("i", "")

            # Symbol map
            if name_lower not in symbols:
                symbols[name_lower] = []
            symbols[name_lower].append({
                "entity_id": entity_id,
                "original_name": name,
                "type": entity_type,
                "confidence": entity.get("confidence", 0.5),
                "aliases": aliases
            })

            # Alias map
            for alias in aliases:
                alias_lower = alias.strip().lower()
                if alias_lower:
                    alias_map.setdefault(alias_lower, []).append({
                        "main_entity": name,
                        "entity_id": entity_id,
                        "entity_type": entity_type
                    })

            # Detekcja wariantów
            name_variants.setdefault(name_clean, []).append({
                "name": name,
                "name_lower": name_lower,
                "entity_id": entity_id,
                "aliases": aliases
            })

        duplicates = {
            clean: group
            for clean, group in name_variants.items()
            if len(group) > 1
        }

        return {
            "symbols": symbols,
            "alias_map": alias_map,
            "duplicates_detected": duplicates,
            "total_unique_names": len(symbols),
            "total_aliases": len(alias_map),
            "potential_duplicates": len(duplicates)
        }

    def generate_graph_summary(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not entities:
            return {"total_entities": 0}

        types = {}
        confidences = []
        alias_count = 0

        for e in entities:
            etype = e.get("type", "unknown")
            types[etype] = types.get(etype, 0) + 1

            conf = e.get("confidence", 0)
            if isinstance(conf, (int, float)):
                confidences.append(conf)

            aliases = e.get("aliases", [])
            if isinstance(aliases, list):
                alias_count += len(aliases)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        return {
            "total_entities": len(entities),
            "entity_types": types,
            "avg_confidence": round(avg_conf, 3),
            "confidence_range": {
                "min": min(confidences) if confidences else 0,
                "max": max(confidences) if confidences else 0
            },
            "total_aliases": alias_count,
            "avg_aliases_per_entity": round(alias_count / len(entities), 2) if entities else 0
        }
