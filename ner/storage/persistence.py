"""
ner/storage/persistence.py

Handles save/load operations for entities, chunks, graph, and FAISS indices
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import networkx as nx

from .models import StoredEntity, StoredChunk, EntityRelationship

logger = logging.getLogger(__name__)


class StoragePersistence:

    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.entities_dir = self.storage_dir / "semantic_store"
        self.chunks_dir = self.storage_dir / "chunks" 
        self.faiss_dir = self.storage_dir / "faiss"
        self.graph_dir = self.storage_dir / "graph"
        self.backups_dir = self.storage_dir / "backups"
        
        # Create directories
        for dir_path in [self.storage_dir, self.entities_dir, self.chunks_dir, 
                        self.faiss_dir, self.graph_dir, self.backups_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.storage_dir / "metadata.json"
        
        logger.info(f"💾 StoragePersistence initialized: {self.storage_dir}")
    
    def save_entity(self, entity: StoredEntity) -> bool:
        try:
            entity_file = self.entities_dir / f"{entity.id}.json"
            entity_data = entity.to_dict_for_json()
            
            with open(entity_file, 'w', encoding='utf-8') as f:
                json.dump(entity_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Saved entity: {entity.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save entity {entity.id}: {e}")
            return False
    
    def load_entity(self, entity_id: str) -> Optional[StoredEntity]:
        try:
            entity_file = self.entities_dir / f"{entity_id}.json"
            
            if not entity_file.exists():
                return None
            
            with open(entity_file, 'r', encoding='utf-8') as f:
                entity_data = json.load(f)
            
            # Reconstruct StoredEntity (embeddings will be regenerated)
            return StoredEntity(**entity_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to load entity {entity_id}: {e}")
            return None
    
    def save_chunk(self, chunk: StoredChunk) -> bool:
        try:
            chunk_file = self.chunks_dir / f"{chunk.id}.json"
            chunk_data = chunk.to_dict_for_json()
            
            with open(chunk_file, 'w', encoding='utf-8') as f:
                json.dump(chunk_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"💾 Saved chunk: {chunk.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save chunk {chunk.id}: {e}")
            return False
    
    def load_chunk(self, chunk_id: str) -> Optional[StoredChunk]:
        try:
            chunk_file = self.chunks_dir / f"{chunk_id}.json"
            
            if not chunk_file.exists():
                return None
            
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
            
            # Reconstruct StoredChunk (embedding will be regenerated)
            return StoredChunk(**chunk_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to load chunk {chunk_id}: {e}")
            return None
    
    def load_all_entities(self) -> Dict[str, StoredEntity]:
        entities = {}
        
        logger.info(f"📂 Loading entities from {self.entities_dir}")
        
        for entity_file in self.entities_dir.glob("*.json"):
            try:
                entity_id = entity_file.stem
                entity = self.load_entity(entity_id)
                
                if entity:
                    entities[entity_id] = entity
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to load entity file {entity_file}: {e}")
        
        logger.info(f"📂 Loaded {len(entities)} entities")
        return entities
    
    def load_all_chunks(self) -> Dict[str, StoredChunk]:
        chunks = {}
        
        logger.info(f"📂 Loading chunks from {self.chunks_dir}")
        
        for chunk_file in self.chunks_dir.glob("*.json"):
            try:
                chunk_id = chunk_file.stem
                chunk = self.load_chunk(chunk_id)
                
                if chunk:
                    chunks[chunk_id] = chunk
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to load chunk file {chunk_file}: {e}")
        
        logger.info(f"📂 Loaded {len(chunks)} chunks")
        return chunks
    
    def save_graph(self, graph: nx.MultiDiGraph) -> bool:
        try:
            # Save as JSON (primary format - more reliable)
            graph_json_file = self.graph_dir / "knowledge_graph.json"
            graph_data = self._prepare_graph_for_json(graph)
            
            with open(graph_json_file, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Try to save as GraphML (secondary format - for visualization tools)
            try:
                graph_file = self.graph_dir / "knowledge_graph.graphml"
                cleaned_graph = self._clean_graph_for_graphml(graph)
                nx.write_graphml(cleaned_graph, str(graph_file))
                logger.debug("💾 GraphML format saved successfully")
            except Exception as graphml_error:
                logger.warning(f"⚠️ GraphML save failed (using JSON only): {graphml_error}")
            
            logger.info(f"💾 Saved graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save graph: {e}")
            return False
    
    def _prepare_graph_for_json(self, graph: nx.MultiDiGraph) -> Dict[str, Any]:
        """Prepare graph data for JSON serialization"""
        nodes = []
        edges = []
        
        # Process nodes
        for node_id, node_data in graph.nodes(data=True):
            node_entry = {
                'id': str(node_id),
                'type': node_data.get('type', 'unknown')
            }
            
            # Handle node data
            if 'data' in node_data:
                data = node_data['data']
                if isinstance(data, dict):
                    node_entry['data'] = data
                elif isinstance(data, str):
                    try:
                        node_entry['data'] = json.loads(data)
                    except:
                        node_entry['data'] = {'raw': data}
                else:
                    node_entry['data'] = {'value': str(data) if data is not None else None}
            
            nodes.append(node_entry)
        
        # Process edges
        for source, target, edge_key, edge_data in graph.edges(data=True, keys=True):
            edge_entry = {
                'source': str(source),
                'target': str(target),
                'key': str(edge_key) if edge_key is not None else 'default'
            }
            
            # Add edge attributes, filtering out None values
            for key, value in edge_data.items():
                if value is not None:
                    edge_entry[key] = value
            
            edges.append(edge_entry)
        
        return {
            'directed': True,
            'multigraph': True,
            'graph': {},
            'nodes': nodes,
            'links': edges  # NetworkX JSON format uses 'links' for edges
        }
    
    def _clean_graph_for_graphml(self, graph: nx.MultiDiGraph) -> nx.MultiDiGraph:
        cleaned_graph = nx.MultiDiGraph()
        
        # Copy nodes with cleaned data
        for node_id, node_data in graph.nodes(data=True):
            cleaned_node_data = {}
            
            for key, value in node_data.items():
                if value is None:
                    continue  # Skip None values
                elif isinstance(value, (str, int, float, bool)):
                    cleaned_node_data[key] = value
                elif isinstance(value, dict):
                    # Serialize dict as JSON string
                    cleaned_node_data[key] = json.dumps(value, default=str)
                elif isinstance(value, list):
                    # Serialize list as JSON string
                    cleaned_node_data[key] = json.dumps(value, default=str)
                else:
                    # Convert other types to string
                    cleaned_node_data[key] = str(value)
            
            cleaned_graph.add_node(node_id, **cleaned_node_data)
        
        # Copy edges with cleaned data
        for source, target, edge_key, edge_data in graph.edges(data=True, keys=True):
            cleaned_edge_data = {}
            
            for key, value in edge_data.items():
                if value is None:
                    continue  # Skip None values
                elif isinstance(value, (str, int, float, bool)):
                    cleaned_edge_data[key] = value
                elif isinstance(value, dict):
                    # Serialize dict as JSON string
                    cleaned_edge_data[key] = json.dumps(value, default=str)
                elif isinstance(value, list):
                    # Serialize list as JSON string
                    cleaned_edge_data[key] = json.dumps(value, default=str)
                else:
                    # Convert other types to string
                    cleaned_edge_data[key] = str(value)
            
            cleaned_graph.add_edge(source, target, key=edge_key, **cleaned_edge_data)
        
        return cleaned_graph
    
    def load_graph(self) -> Optional[nx.MultiDiGraph]:
        try:
            # Try JSON first (more reliable)
            json_file = self.graph_dir / "knowledge_graph.json"
            if json_file.exists():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        graph_data = json.load(f)
                    
                    graph = nx.node_link_graph(graph_data, directed=True, multigraph=True)
                    
                    # Ensure it's MultiDiGraph
                    if not isinstance(graph, nx.MultiDiGraph):
                        multi_graph = nx.MultiDiGraph()
                        multi_graph.add_nodes_from(graph.nodes(data=True))
                        multi_graph.add_edges_from(graph.edges(data=True))
                        graph = multi_graph
                    
                    logger.info(f"📂 Loaded graph from JSON: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
                    return graph
                    
                except Exception as json_error:
                    logger.warning(f"⚠️ JSON graph load failed: {json_error}")
            
            # Fallback to GraphML
            graphml_file = self.graph_dir / "knowledge_graph.graphml"
            if graphml_file.exists():
                try:
                    graph = nx.read_graphml(str(graphml_file))
                    
                    # Convert to MultiDiGraph if needed
                    if not isinstance(graph, nx.MultiDiGraph):
                        multi_graph = nx.MultiDiGraph()
                        multi_graph.add_nodes_from(graph.nodes(data=True))
                        multi_graph.add_edges_from(graph.edges(data=True))
                        graph = multi_graph
                    
                    logger.info(f"📂 Loaded graph from GraphML: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
                    return graph
                    
                except Exception as graphml_error:
                    logger.warning(f"⚠️ GraphML graph load failed: {graphml_error}")
            
            # No existing graph found
            logger.info("📂 No existing graph found, creating new")
            return nx.MultiDiGraph()
            
        except Exception as e:
            logger.error(f"❌ Failed to load graph: {e}")
            return nx.MultiDiGraph()  # Return empty graph as fallback
    
    def save_metadata(self, metadata: Dict[str, Any]) -> bool:
        try:
            # Add timestamp
            metadata_with_timestamp = {
                **metadata,
                'last_saved': datetime.now().isoformat(),
                'storage_version': '2.0'  # Updated version for SemanticStore
            }
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_with_timestamp, f, indent=2, ensure_ascii=False, default=str)
            
            logger.debug("💾 Saved metadata")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")
            return False
    
    def load_metadata(self) -> Dict[str, Any]:
        try:
            if not self.metadata_file.exists():
                return {}
            
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.debug("📂 Loaded metadata")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Failed to load metadata: {e}")
            return {}
    
    def create_backup(self, backup_name: Optional[str] = None) -> bool:
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_dir = self.backups_dir / backup_name
            
            # Copy entire storage directory (excluding backups)
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            
            backup_dir.mkdir(parents=True)
            
            # Copy subdirectories
            for subdir in [self.entities_dir, self.chunks_dir, self.faiss_dir, self.graph_dir]:
                if subdir.exists():
                    dest_dir = backup_dir / subdir.name
                    shutil.copytree(subdir, dest_dir)
            
            # Copy metadata
            if self.metadata_file.exists():
                shutil.copy2(self.metadata_file, backup_dir / "metadata.json")
            
            logger.info(f"💾 Created backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            return False
    
    def restore_from_backup(self, backup_name: str) -> bool:
        try:
            backup_dir = self.backups_dir / backup_name
            
            if not backup_dir.exists():
                logger.error(f"❌ Backup not found: {backup_name}")
                return False
            
            # Clear current storage (except backups)
            for subdir in [self.entities_dir, self.chunks_dir, self.faiss_dir, self.graph_dir]:
                if subdir.exists():
                    shutil.rmtree(subdir)
            
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            
            # Restore from backup
            for backup_subdir in backup_dir.iterdir():
                if backup_subdir.is_dir():
                    dest_dir = self.storage_dir / backup_subdir.name
                    shutil.copytree(backup_subdir, dest_dir)
                elif backup_subdir.name == "metadata.json":
                    shutil.copy2(backup_subdir, self.metadata_file)
            
            logger.info(f"✅ Restored from backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to restore from backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        
        for backup_dir in self.backups_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    stat = backup_dir.stat()
                    backups.append({
                        'name': backup_dir.name,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'size_mb': sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file()) / (1024 * 1024)
                    })
                except Exception as e:
                    logger.warning(f"⚠️ Error reading backup {backup_dir.name}: {e}")
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups
    
    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        backups = self.list_backups()
        removed_count = 0
        
        if len(backups) > keep_count:
            backups_to_remove = backups[keep_count:]
            
            for backup in backups_to_remove:
                try:
                    backup_dir = self.backups_dir / backup['name']
                    shutil.rmtree(backup_dir)
                    removed_count += 1
                    logger.info(f"🗑️ Removed old backup: {backup['name']}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to remove backup {backup['name']}: {e}")
        
        return removed_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        try:
            # Count files
            entity_count = len(list(self.entities_dir.glob("*.json")))
            chunk_count = len(list(self.chunks_dir.glob("*.json")))
            
            # Calculate sizes
            total_size = sum(f.stat().st_size for f in self.storage_dir.rglob('*') if f.is_file())
            entities_size = sum(f.stat().st_size for f in self.entities_dir.glob('*.json'))
            chunks_size = sum(f.stat().st_size for f in self.chunks_dir.glob('*.json'))
            
            return {
                'entity_files': entity_count,
                'chunk_files': chunk_count,
                'total_size_mb': total_size / (1024 * 1024),
                'entities_size_mb': entities_size / (1024 * 1024),
                'chunks_size_mb': chunks_size / (1024 * 1024),
                'storage_path': str(self.storage_dir),
                'backup_count': len(list(self.backups_dir.iterdir())),
                'has_faiss_indices': any(self.faiss_dir.glob('*.faiss')),
                'has_graph_json': (self.graph_dir / 'knowledge_graph.json').exists(),
                'has_graph_graphml': (self.graph_dir / 'knowledge_graph.graphml').exists()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get storage stats: {e}")
            return {}
    
    def exists(self) -> bool:
        return (self.storage_dir.exists() and 
                (any(self.entities_dir.glob("*.json")) or 
                 any(self.chunks_dir.glob("*.json")) or
                 self.metadata_file.exists()))