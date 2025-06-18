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
from fastapi.staticfiles import StaticFiles

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
        "endpoints": ["/stats", "/entities", "/search", "/process", "/graph"]
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

app.mount("/static", StaticFiles(directory="api/static"), name="static")

@app.get("/visualize")
async def visualize_graph():
    from fastapi.responses import FileResponse
    return FileResponse("api/static/graph.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)