# ner/aggregation/graph_builder.py

import json
from pathlib import Path
from typing import Dict, Any, List
from ..utils import load_entities_from_directory
from .symbol_index import SymbolIndex


class GraphBuilder:
    """
    Buduje zbiorczy graf wiedzy (knowledge graph) z plików encji.
    """
    def __init__(self, entities_dir: Path):
        self.entities_dir = Path(entities_dir)
        self.symbol_index = SymbolIndex()

    def build_graph(
        self,
        entities_dir: Path,
        output_file: str,
        aggregation_stats: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        entities = load_entities_from_directory(entities_dir)
        index_info = self.symbol_index.create_symbol_index(entities)
        summary = self.symbol_index.generate_graph_summary(entities)

        result = {
            "entities": entities,
            "symbols": index_info["symbols"],
            "alias_map": index_info["alias_map"],
            "duplicates_detected": index_info["duplicates_detected"],
            "summary": summary
        }

        if aggregation_stats:
            result["aggregation_stats"] = aggregation_stats

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return result
