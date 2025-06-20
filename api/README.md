# NER Knowledge API

REST API for accessing and interacting with the semantic knowledge base built by the NER system.

## Quick Start

```bash
# From project root
cd api
poetry run server
```

Server will start at: http://localhost:8000
- 📖 **API Docs**: http://localhost:8000/docs
- 🔍 **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 📊 Knowledge Base Stats
```http
GET /stats
```
Returns overview statistics of the knowledge base.

**Response:**
```json
{
  "entities": 150,
  "chunks": 25,
  "relationships": 89,
  "storage_size_mb": 2.4,
  "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
  "thresholds": {
    "name_similarity": 0.85,
    "context_similarity": 0.7
  }
}
```

### 🗂️ List Entities
```http
GET /entities?limit=50&offset=0&entity_type=OSOBA
```

**Parameters:**
- `limit` (max 200): Number of entities per page
- `offset`: Starting position for pagination
- `entity_type`: Filter by entity type (optional)

**Response:**
```json
[
  {
    "id": "sem.1750171544683242.aa517584",
    "name": "Warszawa", 
    "type": "MIEJSCE",
    "confidence": 0.95,
    "aliases": ["stolica", "WWA"],
    "description": "Stolica Polski...",
    "source_chunks": ["chunk_0"]
  }
]
```

### 🔍 Get Entity Details
```http
GET /entities/{entity_id}
```

Returns detailed entity information including relationships and related entities.

**Response:**
```json
{
  "entity": {
    "id": "sem.1750171544683242.aa517584",
    "name": "Warszawa",
    "type": "MIEJSCE",
    "confidence": 0.95,
    "aliases": ["stolica", "WWA"],
    "description": "Stolica Polski...",
    "source_chunks": ["chunk_0"]
  },
  "relationships": [
    {
      "source": "entity_1",
      "target": "entity_2", 
      "relation_type": "located_in",
      "confidence": 0.8
    }
  ],
  "related_entities": [
    {
      "id": "related_id",
      "name": "Related Entity",
      "type": "OSOBA",
      "confidence": 0.7
    }
  ],
  "metadata": {
    "created_at": "2025-06-17T16:45:44",
    "updated_at": "2025-06-17T16:45:44",
    "merge_count": 2
  }
}
```

### 🔎 Search Entities
```http
POST /search
```

**Request Body:**
```json
{
  "query": "Warszawa",
  "max_results": 10
}
```

**Response:**
```json
{
  "query": "Warszawa",
  "results": [
    {
      "entity": {
        "id": "sem.1750171544683242.aa517584",
        "name": "Warszawa",
        "type": "MIEJSCE",
        "confidence": 0.95,
        "aliases": ["stolica", "WWA"],
        "description": "Stolica Polski...",
        "source_chunks": ["chunk_0"]
      },
      "similarity": 1.0
    }
  ],
  "total_found": 1
}
```

### ⚙️ Process New Text
```http
POST /process
```

**Request Body:**
```json
{
  "text": "Jan Kowalski mieszka w Krakowie i pracuje w Microsoft.",
  "domains": ["auto"],
  "model": "gpt-4o-mini"
}
```

**Response:**
```json
{
  "status": "success",
  "text_length": 58,
  "entities_before": 150,
  "entities_after": 153,
  "new_entities": 3,
  "domains_used": ["literary", "simple"],
  "model_used": "gpt-4o-mini",
  "chunks_created": 1,
  "processing_time_stats": {
    "chunks_processed": 1,
    "entities_extracted_raw": 3,
    "entities_extracted_valid": 3,
    "semantic_deduplication_hits": 0
  }
}
```

### 🕸️ Knowledge Graph
```http
GET /graph?max_nodes=200&max_edges=400&entity_types=OSOBA,MIEJSCE
```

**Parameters:**
- `max_nodes` (max 500): Limit number of nodes returned
- `max_edges` (max 1000): Limit number of edges returned  
- `entity_types`: Comma-separated entity types to include

**Response:**
```json
{
  "nodes": [
    {
      "id": "entity_1",
      "type": "entity",
      "data": {
        "name": "Warszawa",
        "type": "MIEJSCE",
        "confidence": 0.95
      }
    },
    {
      "id": "chunk_0", 
      "type": "chunk",
      "data": {
        "text": "Fragment tekstu...",
        "document_source": "document.txt"
      }
    }
  ],
  "edges": [
    {
      "source": "chunk_0",
      "target": "entity_1", 
      "relation_type": "contains",
      "confidence": 1.0
    }
  ],
  "stats": {
    "node_count": 175,
    "edge_count": 245,
    "entity_count": 150,
    "chunk_count": 25,
    "returned_nodes": 175,
    "returned_edges": 245
  },
  "truncated": {
    "nodes": false,
    "edges": false
  },
  "available_entity_types": ["OSOBA", "MIEJSCE", "ORGANIZACJA", "PRZEDMIOT"]
}
```

### 🏷️ Entity Types
```http
GET /entity-types
```

**Response:**
```json
{
  "entity_types": [
    {"type": "MIEJSCE", "count": 45},
    {"type": "OSOBA", "count": 38},
    {"type": "ORGANIZACJA", "count": 25},
    {"type": "PRZEDMIOT", "count": 42}
  ],
  "total_types": 4
}
```

### 🗑️ Delete Entity
```http
DELETE /entities/{entity_id}
```

**Response:**
```json
{
  "status": "deleted",
  "entity_id": "sem.1750171544683242.aa517584"
}
```

## Development

### Dependencies
API uses FastAPI with CORS enabled for Next.js frontend:
- `fastapi==0.104.1`
- `uvicorn[standard]==0.24.0`
- `pydantic==2.5.0`

### CORS Configuration
Configured for Next.js development servers:
- `http://localhost:3000`
- `http://localhost:3001`

### Error Handling
All endpoints return consistent error format:
```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `200`: Success
- `404`: Entity not found
- `500`: Server error (processing failed, store not initialized)

### Performance Notes
- Entity listing is paginated (max 200 per request)
- Graph endpoints are limited to prevent large responses
- Search results are capped at configurable limits
- FAISS indices provide fast similarity search

## Integration Examples

### Next.js Fetch Example
```javascript
// Search entities
const searchEntities = async (query) => {
  const response = await fetch('http://localhost:8000/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, max_results: 10 })
  });
  return await response.json();
};

// Process new text
const processText = async (text) => {
  const response = await fetch('http://localhost:8000/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      text, 
      domains: ['auto'], 
      model: 'gpt-4o-mini' 
    })
  });
  return await response.json();
};
```

### Graph Visualization
The `/graph` endpoint returns data compatible with:
- **D3.js**: Direct use of nodes/edges arrays
- **vis.js**: Convert to DataSets
- **Cytoscape.js**: Transform to elements format
- **React Flow**: Map to nodes/edges with positions

### Real-time Updates
For real-time knowledge base updates in your frontend:
1. Process text via `/process` endpoint
2. Poll `/stats` for change detection
3. Refresh entity lists or search results
4. Update graph visualization

## Troubleshooting

### "Store not initialized" Error
Ensure the `semantic_store` directory exists in project root with valid data:
```bash
ls ../semantic_store/
# Should show: entities/ chunks/ faiss/ graph/ metadata.json
```

### CORS Issues
If Next.js runs on different port, update CORS settings in `server.py`:
```python
allow_origins=["http://localhost:YOUR_PORT"]
```

### Large Response Times
For better performance with large knowledge bases:
- Use pagination parameters
- Filter by entity_types
- Limit graph node/edge counts
- Consider caching on frontend