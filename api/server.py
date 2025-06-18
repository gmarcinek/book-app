"""
FastAPI REST Server for NER Knowledge Base
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from ner.storage import SemanticStore
from ner import process_text_to_knowledge
from ner.loaders import LoadedDocument

app = FastAPI(title="NER Knowledge API", version="1.0.0")

# Add CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global store instance
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

@app.on_event("startup")
async def startup():
    global store
    storage_dir = Path(__file__).parent.parent / "semantic_store"
    store = SemanticStore(storage_dir=str(storage_dir))
    print(f"📊 API started with {len(store.entities)} entities")

@app.get("/")
async def root():
    return {
        "message": "NER Knowledge API", 
        "version": "1.0.0",
        "endpoints": [
            "/stats", "/entities", "/search", "/process", "/graph"
        ]
    }

@app.get("/stats")
async def get_stats():
    """Get knowledge base statistics"""
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
async def get_entities(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    entity_type: Optional[str] = None
):
    """Get entities with pagination and optional filtering"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    entities = list(store.entities.values())
    
    # Filter by type if specified
    if entity_type:
        entities = [e for e in entities if e.type.upper() == entity_type.upper()]
    
    # Apply pagination
    paginated = entities[offset:offset+limit]
    
    return [
        EntityResponse(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            confidence=entity.confidence,
            aliases=entity.aliases,
            description=entity.description,
            source_chunks=entity.source_chunk_ids
        )
        for entity in paginated
    ]

@app.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get specific entity with relationships"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    entity = store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    relationships = store.relationship_manager.get_entity_relationships(entity_id)
    
    # Get related entities
    related_entity_ids = store.relationship_manager.get_related_entities(entity_id, max_depth=2)
    related_entities = []
    for rel_id in related_entity_ids[:10]:  # Limit to 10
        rel_entity = store.get_entity_by_id(rel_id)
        if rel_entity:
            related_entities.append({
                "id": rel_entity.id,
                "name": rel_entity.name,
                "type": rel_entity.type,
                "confidence": rel_entity.confidence
            })
    
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
        "related_entities": related_entities,
        "metadata": {
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
            "merge_count": entity.merge_count
        }
    }

@app.post("/search")
async def search_entities(query: SearchQuery):
    """Search entities by name similarity"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    results = store.search_entities_by_name(query.query, query.max_results)
    
    return {
        "query": query.query,
        "results": [
            {
                "entity": EntityResponse(
                    id=entity.id,
                    name=entity.name,
                    type=entity.type,
                    confidence=entity.confidence,
                    aliases=entity.aliases,
                    description=entity.description,
                    source_chunks=entity.source_chunk_ids
                ),
                "similarity": round(similarity, 3)
            }
            for entity, similarity in results
        ],
        "total_found": len(results)
    }

@app.post("/process")
async def process_text(input_data: TextInput):
    """Process new text and extract entities"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    try:
        # Track entities before processing
        entities_before = len(store.entities)
        
        # Create document
        document = LoadedDocument(
            content=input_data.text,
            source_file="api_input",
            file_type="text",
            metadata={"source": "api"}
        )
        
        # Process
        result = process_text_to_knowledge(
            document,
            entities_dir="semantic_store",
            model=input_data.model,
            domain_names=input_data.domains,
            output_aggregated=False
        )
        
        if result["status"] == "success":
            entities_after = len(store.entities)
            new_entities_count = entities_after - entities_before
            
            # Get processing stats
            processing_stats = result.get("processing_stats", {})
            extraction_stats = processing_stats.get("extraction_stats", {})
            
            return {
                "status": "success",
                "text_length": len(input_data.text),
                "entities_before": entities_before,
                "entities_after": entities_after,
                "new_entities": new_entities_count,
                "domains_used": input_data.domains,
                "model_used": input_data.model,
                "chunks_created": processing_stats.get("chunks_created", 0),
                "processing_time_stats": {
                    "chunks_processed": extraction_stats.get("chunks_processed", 0),
                    "entities_extracted_raw": extraction_stats.get("entities_extracted_raw", 0),
                    "entities_extracted_valid": extraction_stats.get("entities_extracted_valid", 0),
                    "semantic_deduplication_hits": extraction_stats.get("semantic_deduplication_hits", 0)
                }
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph")
async def get_knowledge_graph(
    max_nodes: int = Query(200, le=500),
    max_edges: int = Query(400, le=1000),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types to include")
):
    """Get knowledge graph data for visualization"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    graph_data = store.relationship_manager.export_graph_data()
    
    # Filter by entity types if specified
    if entity_types:
        type_filter = [t.strip().upper() for t in entity_types.split(",")]
        filtered_nodes = []
        filtered_node_ids = set()
        
        for node in graph_data['nodes']:
            if node.get('type') == 'entity':
                entity_type = node.get('data', {}).get('type', '').upper()
                if entity_type in type_filter:
                    filtered_nodes.append(node)
                    filtered_node_ids.add(node['id'])
            else:
                filtered_nodes.append(node)
                filtered_node_ids.add(node['id'])
        
        # Filter edges to only include those between filtered nodes
        filtered_edges = [
            edge for edge in graph_data['edges']
            if edge['source'] in filtered_node_ids and edge['target'] in filtered_node_ids
        ]
        
        graph_data['nodes'] = filtered_nodes
        graph_data['edges'] = filtered_edges
    
    # Apply limits
    nodes = graph_data['nodes'][:max_nodes]
    edges = graph_data['edges'][:max_edges]
    
    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            **graph_data['stats'],
            "returned_nodes": len(nodes),
            "returned_edges": len(edges)
        },
        "truncated": {
            "nodes": len(graph_data['nodes']) > max_nodes,
            "edges": len(graph_data['edges']) > max_edges
        },
        "available_entity_types": list(set(
            node.get('data', {}).get('type', 'unknown') 
            for node in graph_data['nodes'] 
            if node.get('type') == 'entity'
        ))
    }

@app.get("/entity-types")
async def get_entity_types():
    """Get all available entity types with counts"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    type_counts = {}
    for entity in store.entities.values():
        entity_type = entity.type
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
    
    return {
        "entity_types": [
            {"type": entity_type, "count": count}
            for entity_type, count in sorted(type_counts.items())
        ],
        "total_types": len(type_counts)
    }

@app.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str):
    """Delete entity from knowledge base"""
    if not store:
        raise HTTPException(status_code=500, detail="Store not initialized")
    
    entity = store.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    try:
        # Remove from FAISS
        store.faiss_manager.remove_entity(entity_id)
        
        # Remove from graph
        if store.relationship_manager.graph.has_node(entity_id):
            store.relationship_manager.graph.remove_node(entity_id)
        
        # Remove from memory
        del store.entities[entity_id]
        
        # Remove file
        entity_file = store.persistence.entities_dir / f"{entity_id}.json"
        if entity_file.exists():
            entity_file.unlink()
        
        return {"status": "deleted", "entity_id": entity_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete entity: {str(e)}")
    
 # Po utworzeniu app:
app.mount("/static", StaticFiles(directory="api/static"), name="static")

@app.get("/visualize")
async def visualize_graph():
    """Redirect to graph visualization"""
    from fastapi.responses import FileResponse
    return FileResponse("api/static/graph.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)