from .indexer import EntityIndex
from .file_manager import EntityFileManager
from .symbol_index import SymbolIndex
from .graph_builder import GraphBuilder
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class GraphAggregator:
    def __init__(self, entities_dir: str = "entities", config_path: str = "ner/ner_config.json"):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        self.entities_dir = Path(entities_dir) / timestamp
        self.entities_dir.mkdir(parents=True, exist_ok=True)

        self.log_dir = self.entities_dir / "log"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.indexer = EntityIndex(self.entities_dir)
        self.file_manager = EntityFileManager(self.entities_dir, config_path)
        self.symbol_index = SymbolIndex()
        self.graph_builder = GraphBuilder(self.entities_dir)

        self.aggregation_stats = {
            "entities_created": 0,
            "entities_updated": 0,
            "duplicates_merged": 0,
            "files_written": 0,
            "aliases_indexed": 0
        }

    def load_entity_index(self):
        self.indexer.load()

    def find_existing_entity(self, name: str, aliases: List[str] = None) -> Optional[str]:
        return self.indexer.find(name, aliases)

    def create_entity_file(self, entity_data: Dict[str, Any], chunk_refs: List[str]) -> Optional[str]:
        entity_id, created, alias_count = self.file_manager.create_or_update_entity(entity_data, chunk_refs)

        if entity_id:
            if created:
                self.aggregation_stats["entities_created"] += 1
            else:
                self.aggregation_stats["entities_updated"] += 1
            self.aggregation_stats["aliases_indexed"] += alias_count
        return entity_id

    def create_aggregated_graph(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        if output_file is None:
            output_file = self.entities_dir / "knowledge_graph.json"
        return self.graph_builder.build_graph(self.entities_dir, output_file, self.aggregation_stats)

    def get_aggregation_stats(self) -> Dict[str, Any]:
        return {
            **self.aggregation_stats,
            "entities_dir": str(self.entities_dir),
            "index_size": len(self.indexer.entity_index),
            "alias_index_size": len(self.indexer.alias_index),
            "config": {
                "entities_directory": str(self.entities_dir)
            }
        }

    def reset_stats(self):
        self.aggregation_stats = {
            "entities_created": 0,
            "entities_updated": 0,
            "duplicates_merged": 0,
            "files_written": 0,
            "aliases_indexed": 0
        }
