"""
Status endpoints - basic API info and health checks
"""

from fastapi import APIRouter, HTTPException

from ..deps import get_store, get_store_status

router = APIRouter()


@router.get("/")
async def root():
    """API info and available endpoints"""
    return {
        "message": "NER Knowledge API",
        "version": "1.0.0",
        "endpoints": ["/stats", "/entities", "/search", "/process", "/graph", "/relationships"]
    }


@router.get("/store-status")
async def store_status():
    """Get semantic store status and basic info"""
    return get_store_status()


@router.get("/stats")
async def get_stats():
    """Get comprehensive semantic store statistics"""
    try:
        store = get_store()
        stats = store.get_stats()
        return {
            "entities": stats['entities'],
            "chunks": stats['chunks'],
            "relationships": stats['relationships'].get('total_relationships', 0),
            "storage_size_mb": round(stats['storage'].get('total_size_mb', 0), 2),
            "embedding_model": stats['embedder']['model_name'],
        }
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Store not initialized")