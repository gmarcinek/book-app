"""
FastAPI REST Server for NER Knowledge Base with auto-reload on semantic_store changes
"""

from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sys
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from ner.storage import SemanticStore
from ner import process_text_to_knowledge
from ner.loaders import LoadedDocument

globals()["store_loaded_at"] = datetime.now()

app = FastAPI(title="NER Knowledge API", version="1.0.0")

# Add CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store: Optional[SemanticStore] = None

class TextInput(BaseModel):
    text: str
    domains: Optional[List[str]] = ["auto"]
    model: Optional[str] = "gpt-4o-mini"

class SearchQuery(BaseModel):
    query: str
    max_results: Optional[int] = 10

class EntityResponse(BaseModel):
    id: str
    name: str
    type: str
    confidence: float
    aliases: List[str]
    description: str
    source_chunks: List[str]

class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    type: Optional[str] = None
    confidence: Optional[float] = None

class EntityCreateRequest(BaseModel):
    name: str
    type: str
    description: Optional[str] = ""
    aliases: Optional[List[str]] = []
    confidence: Optional[float] = 1.0
    context: Optional[str] = ""

class RelationshipCreateRequest(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    confidence: Optional[float] = 1.0
    evidence: Optional[str] = ""

class RelationshipUpdateRequest(BaseModel):
    relation_type: Optional[str] = None
    confidence: Optional[float] = None
    evidence: Optional[str] = None

class RelationshipResponse(BaseModel):
    source: str
    target: str
    relation_type: str
    confidence: float

class SemanticStoreChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.event_type in ('created', 'modified', 'deleted', 'moved'):
            print(f"\n🔄 Zmiana wykryta w semantic_store: {event.src_path}")
            try:
                globals()["store"] = SemanticStore(storage_dir=str(Path(__file__).parent.parent / "semantic_store"))
                print("✅ Store zaktualizowany")
            except Exception as e:
                print(f"❌ Błąd podczas aktualizacji store: {e}")

def start_watcher(path: Path):
    observer = Observer()
    handler = SemanticStoreChangeHandler()
    observer.schedule(handler, str(path), recursive=True)
    observer.daemon = True
    observer.start()
    print(f"👁️ Obserwacja folderu: {path}")

@app.on_event("startup")
async def startup():
    global store
    storage_dir = Path(__file__).parent.parent / "semantic_store"
    store = SemanticStore(storage_dir=str(storage_dir))
    print(f"📊 API started with {len(store.entities)} entities")
    threading.Thread(target=start_watcher, args=(storage_dir,), daemon=True).start()

@app.get("/")
async def root():
    return {
        "message": "NER Knowledge API",
        "version": "1.0.0",
        "endpoints": ["/stats", "/entities", "/search", "/process", "/graph", "/relationships"]
    }

@app.get("/store-status")
async def store_status():
    return {
        "last_loaded": store_loaded_at.isoformat(),
        "entities": len(store.entities),
        "chunks": len(store.chunks)
    }
    
@app.get("/stats")
async def get_stats():
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    stats = store.get_stats()
    return {
        "entities": stats['entities'],
        "chunks": stats['chunks'],
        "relationships": stats['relationships'].get('total_relationships', 0),
        "storage_size_mb": round(stats['storage'].get('total_size_mb', 0), 2),
        "embedding_model": stats['embedder']['model_name'],
    }

@app.post("/entities")
async def create_entity(entity_data: EntityCreateRequest):
    """Create new entity"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    try:
        from ner.models import Entity
        import uuid
        
        # Generate unique ID
        entity_id = str(uuid.uuid4())
        
        # Create new entity
        entity = Entity(
            id=entity_id,
            name=entity_data.name,
            type=entity_data.type,
            description=entity_data.description or "",
            aliases=entity_data.aliases or [],
            confidence=max(0.0, min(1.0, entity_data.confidence or 1.0)),
            context=entity_data.context or "",
            source_chunk_ids=[],
            document_sources=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            merge_count=0
        )
        
        # Save to disk and memory
        store.persistence.save_entity(entity)
        store.entities[entity_id] = entity
        
        print(f"✅ Entity created: {entity_id} - {entity.name}")
        
        return {
            "status": "created",
            "entity_id": entity_id,
            "entity": EntityResponse(
                id=entity.id,
                name=entity.name,
                type=entity.type,
                confidence=entity.confidence,
                aliases=entity.aliases,
                description=entity.description,
                source_chunks=entity.source_chunk_ids
            )
        }
        
    except Exception as e:
        print(f"❌ Failed to create entity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create entity: {e}")

@app.get("/entities", response_model=List[EntityResponse])
async def get_entities(limit: int = Query(50, le=200), offset: int = Query(0, ge=0), entity_type: Optional[str] = None):
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    entities = list(store.entities.values())
    if entity_type:
        entities = [e for e in entities if e.type.upper() == entity_type.upper()]
    paginated = entities[offset:offset+limit]
    return [
        EntityResponse(
            id=e.id,
            name=e.name,
            type=e.type,
            confidence=e.confidence,
            aliases=e.aliases,
            description=e.description,
            source_chunks=e.source_chunk_ids
        ) for e in paginated
    ]

@app.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    entity = store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    relationships = store.relationship_manager.get_entity_relationships(entity_id)
    related_ids = store.relationship_manager.get_related_entities(entity_id, max_depth=2)
    related = [
        {
            "id": e.id,
            "name": e.name,
            "type": e.type,
            "confidence": e.confidence
        }
        for eid in related_ids[:10]
        if (e := store.get_entity_by_id(eid))
    ]
    return {
        "entity": EntityResponse(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            confidence=entity.confidence,
            aliases=entity.aliases,
            description=entity.description,
            source_chunks=entity.source_chunk_ids
        ),
        "relationships": relationships[:20],
        "related_entities": related,
        "metadata": {
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "merge_count": entity.merge_count
        }
    }

@app.put("/entities/{entity_id}")
async def update_entity(entity_id: str, update_data: EntityUpdateRequest):
    """Update entity fields - FIXED: Added missing PUT endpoint"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    entity = store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    try:
        # Update entity fields if provided
        if update_data.name is not None:
            entity.name = update_data.name
        if update_data.description is not None:
            entity.description = update_data.description
        if update_data.aliases is not None:
            entity.aliases = update_data.aliases
        if update_data.type is not None:
            entity.type = update_data.type
        if update_data.confidence is not None:
            entity.confidence = max(0.0, min(1.0, update_data.confidence))  # Clamp to [0,1]
        
        # Update timestamp
        entity.updated_at = datetime.now().isoformat()
        
        # Save to disk
        store.persistence.save_entity(entity)
        
        # Update in-memory store
        store.entities[entity_id] = entity
        
        print(f"✅ Entity {entity_id} updated: {entity.name}")
        
        return {
            "status": "updated", 
            "entity_id": entity_id,
            "updated_fields": {
                k: v for k, v in update_data.dict().items() 
                if v is not None
            }
        }
        
    except Exception as e:
        print(f"❌ Failed to update entity {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update entity: {e}")

@app.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str):
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    entity = store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    try:
        store.faiss_manager.remove_entity(entity_id)
        if store.relationship_manager.graph.has_node(entity_id):
            store.relationship_manager.graph.remove_node(entity_id)
        del store.entities[entity_id]
        file = store.persistence.entities_dir / f"{entity_id}.json"
        if file.exists():
            file.unlink()
        return {"status": "deleted", "entity_id": entity_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete entity: {e}")

@app.post("/relationships")
async def create_relationship(rel_data: RelationshipCreateRequest):
    """Create new relationship between entities"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    # Verify both entities exist
    source_entity = store.get_entity_by_id(rel_data.source_id)
    target_entity = store.get_entity_by_id(rel_data.target_id)
    
    if not source_entity:
        raise HTTPException(status_code=404, detail=f"Source entity {rel_data.source_id} not found")
    if not target_entity:
        raise HTTPException(status_code=404, detail=f"Target entity {rel_data.target_id} not found")
    
    try:
        import uuid
        
        # Generate relationship ID
        rel_id = str(uuid.uuid4())
        
        # Add relationship to graph
        store.relationship_manager.graph.add_edge(
            rel_data.source_id,
            rel_data.target_id,
            id=rel_id,
            relation_type=rel_data.relation_type,
            confidence=max(0.0, min(1.0, rel_data.confidence or 1.0)),
            evidence=rel_data.evidence or "",
            created_at=datetime.now().isoformat(),
            discovery_method="manual"
        )
        
        # Save relationships to disk
        store.relationship_manager.save_relationships()
        
        print(f"✅ Relationship created: {rel_id} - {source_entity.name} -> {target_entity.name}")
        
        return {
            "status": "created",
            "relationship_id": rel_id,
            "relationship": {
                "id": rel_id,
                "source": source_entity.name,
                "target": target_entity.name,
                "source_id": rel_data.source_id,
                "target_id": rel_data.target_id,
                "relation_type": rel_data.relation_type,
                "confidence": rel_data.confidence or 1.0,
                "evidence": rel_data.evidence or "",
                "created_at": datetime.now().isoformat(),
                "discovery_method": "manual"
            }
        }
        
    except Exception as e:
        print(f"❌ Failed to create relationship: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {e}")

@app.get("/relationships/{relationship_id}")
async def get_relationship(relationship_id: str):
    """Get specific relationship details"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    # Find relationship in graph
    for source, target, data in store.relationship_manager.graph.edges(data=True):
        if data.get('id') == relationship_id:
            source_entity = store.get_entity_by_id(source)
            target_entity = store.get_entity_by_id(target)
            
            return {
                "id": relationship_id,
                "source": source_entity.name if source_entity else source,
                "target": target_entity.name if target_entity else target,
                "source_id": source,
                "target_id": target,
                "relation_type": data.get('relation_type', ''),
                "confidence": data.get('confidence', 0.0),
                "evidence": data.get('evidence', ''),
                "created_at": data.get('created_at', ''),
                "discovery_method": data.get('discovery_method', '')
            }
    
    raise HTTPException(status_code=404, detail="Relationship not found")

@app.get("/relationships")
async def get_relationships(
    entity_id: Optional[str] = None,
    relation_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """Get relationships with optional filtering"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    relationships = []
    
    for source, target, data in store.relationship_manager.graph.edges(data=True):
        # Filter by entity_id if provided
        if entity_id and entity_id not in [source, target]:
            continue
            
        # Filter by relation_type if provided
        if relation_type and data.get('relation_type', '').upper() != relation_type.upper():
            continue
        
        source_entity = store.get_entity_by_id(source)
        target_entity = store.get_entity_by_id(target)
        
        relationships.append({
            "id": data.get('id', f"{source}-{target}"),
            "source": source_entity.name if source_entity else source,
            "target": target_entity.name if target_entity else target,
            "source_id": source,
            "target_id": target,
            "relation_type": data.get('relation_type', ''),
            "confidence": data.get('confidence', 0.0),
            "evidence": data.get('evidence', ''),
            "created_at": data.get('created_at', ''),
            "discovery_method": data.get('discovery_method', '')
        })
    
    # Apply pagination
    paginated = relationships[offset:offset+limit]
    
    return {
        "relationships": paginated,
        "total_found": len(relationships),
        "returned": len(paginated)
    }

@app.put("/relationships/{relationship_id}")
async def update_relationship(relationship_id: str, update_data: RelationshipUpdateRequest):
    """Update relationship"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    # Find and update relationship in graph
    for source, target, data in store.relationship_manager.graph.edges(data=True):
        if data.get('id') == relationship_id:
            try:
                # Update fields if provided
                if update_data.relation_type is not None:
                    data['relation_type'] = update_data.relation_type
                if update_data.confidence is not None:
                    data['confidence'] = max(0.0, min(1.0, update_data.confidence))
                if update_data.evidence is not None:
                    data['evidence'] = update_data.evidence
                
                # Update timestamp
                data['updated_at'] = datetime.now().isoformat()
                
                # Save to disk
                store.relationship_manager.save_relationships()
                
                print(f"✅ Relationship {relationship_id} updated")
                
                return {
                    "status": "updated",
                    "relationship_id": relationship_id,
                    "updated_fields": {
                        k: v for k, v in update_data.dict().items() 
                        if v is not None
                    }
                }
                
            except Exception as e:
                print(f"❌ Failed to update relationship {relationship_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to update relationship: {e}")
    
    raise HTTPException(status_code=404, detail="Relationship not found")

@app.delete("/relationships/{relationship_id}")
async def delete_relationship(relationship_id: str):
    """Delete relationship"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    # Find and remove relationship from graph
    for source, target, data in store.relationship_manager.graph.edges(data=True):
        if data.get('id') == relationship_id:
            try:
                store.relationship_manager.graph.remove_edge(source, target)
                store.relationship_manager.save_relationships()
                
                print(f"✅ Relationship {relationship_id} deleted")
                
                return {
                    "status": "deleted",
                    "relationship_id": relationship_id
                }
                
            except Exception as e:
                print(f"❌ Failed to delete relationship {relationship_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to delete relationship: {e}")
    
    raise HTTPException(status_code=404, detail="Relationship not found")

@app.post("/search")
async def search_entities(query: SearchQuery):
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    results = store.search_entities_by_name(query.query, query.max_results)
    return {
        "query": query.query,
        "results": [
            {
                "entity": EntityResponse(
                    id=e.id,
                    name=e.name,
                    type=e.type,
                    confidence=e.confidence,
                    aliases=e.aliases,
                    description=e.description,
                    source_chunks=e.source_chunk_ids
                ),
                "similarity": round(sim, 3)
            } for e, sim in results
        ],
        "total_found": len(results)
    }

@app.post("/process")
async def process_text(input_data: TextInput):
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    try:
        before = len(store.entities)
        doc = LoadedDocument(
            content=input_data.text,
            source_file="api_input",
            file_type="text",
            metadata={"source": "api"}
        )
        result = process_text_to_knowledge(
            doc,
            entities_dir="semantic_store",
            model=input_data.model,
            domain_names=input_data.domains,
            output_aggregated=False
        )
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        after = len(store.entities)
        stats = result.get("processing_stats", {}).get("extraction_stats", {})
        return {
            "status": "success",
            "text_length": len(input_data.text),
            "entities_before": before,
            "entities_after": after,
            "new_entities": after - before,
            "domains_used": input_data.domains,
            "model_used": input_data.model,
            "chunks_created": result.get("processing_stats", {}).get("chunks_created", 0),
            "processing_time_stats": {
                "chunks_processed": stats.get("chunks_processed", 0),
                "entities_extracted_raw": stats.get("entities_extracted_raw", 0),
                "entities_extracted_valid": stats.get("entities_extracted_valid", 0),
                "semantic_deduplication_hits": stats.get("semantic_deduplication_hits", 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph")
async def get_knowledge_graph(max_nodes: int = Query(200, le=500), max_edges: int = Query(400, le=1000), entity_types: Optional[str] = None):
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    graph = store.relationship_manager.export_graph_data()
    if entity_types:
        allowed = set(t.strip().upper() for t in entity_types.split(","))
        nodes = [n for n in graph['nodes'] if n.get('type') != 'entity' or n.get('data', {}).get('type', '').upper() in allowed]
        node_ids = set(n['id'] for n in nodes)
        edges = [e for e in graph['edges'] if e['source'] in node_ids and e['target'] in node_ids]
    else:
        nodes = graph['nodes']
        edges = graph['edges']
    return {
        "nodes": nodes[:max_nodes],
        "edges": edges[:max_edges],
        "stats": {
            **graph['stats'],
            "returned_nodes": len(nodes[:max_nodes]),
            "returned_edges": len(edges[:max_edges])
        },
        "truncated": {
            "nodes": len(nodes) > max_nodes,
            "edges": len(edges) > max_edges
        },
        "available_entity_types": list(set(
            n.get('data', {}).get('type', 'unknown')
            for n in nodes if n.get('type') == 'entity'
        ))
    }

@app.get("/entity-types")
async def get_entity_types():
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    counter = {}
    for e in store.entities.values():
        counter[e.type] = counter.get(e.type, 0) + 1
    return {
        "entity_types": [
            {"type": k, "count": v} for k, v in sorted(counter.items())
        ],
        "total_types": len(counter)
    }
