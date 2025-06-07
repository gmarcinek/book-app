import json
import sys
import os
import re
import time
import hashlib
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import your LLM module
from llm import LLMClient, Models, LLMConfig

def log_memory_usage(stage: str = ""):
    """Monitor RAM usage to detect memory leaks"""
    usage = psutil.virtual_memory()
    print(f"[MEMORY] {stage}: {usage.percent:.1f}% ({usage.used // (1024 ** 2)} MB used, {usage.available // (1024 ** 2)} MB free)")

class KnowledgeGraphBuilder:
    """Build entity-centric knowledge graph from text"""
    
    def __init__(self, entities_dir: str = "entities", model: str = Models.QWEN_CODER):
        self.entities_dir = Path(entities_dir)
        self.entities_dir.mkdir(exist_ok=True)
        self.model = model
        self.llm_client = None
        self.entity_index = {}  # name -> entity_id mapping
        
    def _init_llm(self):
        """Initialize LLM client"""
        if not self.llm_client:
            log_memory_usage("Before LLM init")
            self.llm_client = LLMClient(
                model=self.model,
                max_tokens=1500,  # Reduced from 2000
                temperature=0.0,
                system_message="Jesteś ekspertem w budowaniu grafów wiedzy. Analizujesz tekst i wyciągasz encje oraz ich powiązania."
            )
            log_memory_usage("After LLM init")
    
    def _generate_entity_id(self, name: str, entity_type: str) -> str:
        """Generate unique entity ID"""
        timestamp = str(int(time.time() * 1000000))  # microsecond precision
        hash_input = f"{name}_{entity_type}_{timestamp}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"ent.{timestamp}.{hash_suffix}"
    
    def _load_entity_index(self):
        """Load existing entity index from files"""
        self.entity_index = {}
        for entity_file in self.entities_dir.glob("ent.*.json"):
            try:
                with open(entity_file, 'r', encoding='utf-8') as f:
                    entity = json.load(f)
                    name_key = entity['name'].lower().strip()
                    self.entity_index[name_key] = entity['id']
            except Exception as e:
                print(f"Warning: Could not load {entity_file}: {e}")
    
    def _find_existing_entity(self, name: str) -> Optional[str]:
        """Find existing entity by name"""
        name_key = name.lower().strip()
        return self.entity_index.get(name_key)
    
    def _extract_entities_from_chunk(self, text: str, chunk_start: int, chunk_end: int, chunk_id: int) -> List[Dict]:
        """Extract entities from text chunk using LLM"""
        log_memory_usage(f"Before entity extraction chunk {chunk_id}")
        self._init_llm()
        
        # Get chunk text on demand
        chunk_text = text[chunk_start:chunk_end].strip()
        
        prompt = f"""Analizuj poniższy fragment tekstu i wyciągnij wszystkie encje.

TEKST:
{chunk_text}

Dla każdej encji podaj:
1. Nazwę (dokładnie jak w tekście)
2. Typ (OSOBA, MIEJSCE, ORGANIZACJA, PRZEDMIOT, itp.)
3. Krótki opis (1-2 zdania)

ODPOWIEDŹ W JSON:
{{
  "entities": [
    {{
      "name": "nazwa encji",
      "type": "TYP",
      "description": "krótki opis",
      "confidence": 0.95
    }}
  ]
}}

ZASADY:
- Maksymalnie 10 encji
- Tylko konkretne, jednoznaczne encje
- Krótkie opisy
"""
        
        try:
            response = self.llm_client.chat(prompt)
            log_memory_usage(f"After LLM call chunk {chunk_id}")
            
            # Parse JSON response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1:
                json_text = response[json_start:json_end]
                result = json.loads(json_text)
                
                # Add chunk info to each entity
                for entity in result.get('entities', []):
                    entity['chunk_id'] = chunk_id
                
                # Clear response to help GC
                del response, chunk_text
                log_memory_usage(f"After processing chunk {chunk_id}")
                
                return result.get('entities', [])
                
        except Exception as e:
            print(f"Error extracting entities from chunk {chunk_id}: {e}")
            log_memory_usage(f"Error in chunk {chunk_id}")
        
        return []
    
    def _find_relationships(self, entity: Dict, all_entities: List[Dict], full_text: str) -> Dict:
        """Find relationships for an entity using LLM"""
        log_memory_usage(f"Before relationships for {entity['name']}")
        self._init_llm()
        
        # Prepare context with other entities (limit to avoid huge prompts)
        other_entities = [e for e in all_entities if e['name'] != entity['name']]
        entity_names = [e['name'] for e in other_entities[:15]]  # Limit to 15 entities
        
        # Limit text length to avoid memory issues
        text_sample = full_text[:3000] if len(full_text) > 3000 else full_text
        
        prompt = f"""Analizuj powiązania encji "{entity['name']}" w kontekście tekstu.

TEKST (fragment):
{text_sample}

ENCJA DO ANALIZY: {entity['name']} ({entity['type']})

INNE ZNALEZIONE ENCJE: {', '.join(entity_names)}

Znajdź TYLKO najważniejsze powiązania tej encji:

ODPOWIEDŹ W JSON:
{{
  "internal_relationships": [
    {{
      "type": "typ_związku",
      "target_entity": "nazwa encji",
      "evidence": "krótki fragment",
      "confidence": 0.9
    }}
  ],
  "external_relationships": [
    {{
      "type": "typ_informacji", 
      "value": "wartość/opis",
      "source": "wiedza_ogólna"
    }}
  ],
  "missing_entities": [
    {{
      "name": "brakująca encja",
      "type": "TYP", 
      "reason": "dlaczego powinna istnieć"
    }}
  ]
}}

ZASADY:
- Maksymalnie 3-5 powiązań na kategorię
- Krótkie, konkretne opisy
- Tylko najważniejsze informacje
"""
        
        try:
            response = self.llm_client.chat(prompt)
            log_memory_usage(f"After relationships LLM call for {entity['name']}")
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1:
                json_text = response[json_start:json_end]
                result = json.loads(json_text)
                
                # Clear response
                del response
                log_memory_usage(f"After processing relationships for {entity['name']}")
                return result
                
        except Exception as e:
            print(f"Error finding relationships for {entity['name']}: {e}")
            log_memory_usage(f"Error in relationships for {entity['name']}")
        
        return {"internal_relationships": [], "external_relationships": [], "missing_entities": []}
    
    def _create_entity_file(self, entity: Dict, relationships: Dict, chunk_refs: List[str]) -> str:
        """Create individual entity JSON file"""
        entity_id = self._generate_entity_id(entity['name'], entity['type'])
        
        # Check for existing entity
        existing_id = self._find_existing_entity(entity['name'])
        if existing_id:
            print(f"Entity '{entity['name']}' already exists as {existing_id}, updating...")
            entity_id = existing_id
        
        entity_data = {
            "id": entity_id,
            "name": entity['name'],
            "type": entity['type'],
            "description": entity.get('description', ''),
            "confidence": entity.get('confidence', 0.5),
            
            "source_info": {
                "evidence": entity.get('evidence', ''),
                "chunk_references": chunk_refs,
                "found_in_chunks": [entity.get('chunk_id', 0)]
            },
            
            "relationships": {
                "internal": relationships.get('internal_relationships', []),
                "external": relationships.get('external_relationships', []),
                "pending": relationships.get('missing_entities', [])
            },
            
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "model_used": self.model
            }
        }
        
        # Save to file
        entity_file = self.entities_dir / f"{entity_id}.json"
        try:
            with open(entity_file, 'w', encoding='utf-8') as f:
                json.dump(entity_data, f, indent=2, ensure_ascii=False)
            
            # Update index
            name_key = entity['name'].lower().strip()
            self.entity_index[name_key] = entity_id
            
            print(f"Created entity file: {entity_file}")
            return entity_id
            
        except Exception as e:
            print(f"Error saving entity {entity_id}: {e}")
            return None
    
    def _chunk_text(self, text: str, chunk_size: int = 2000, overlap: int = 200) -> List[Dict]:
        """Split text into overlapping chunks - SIMPLE VERSION"""
        chunks = []
        text_len = len(text)
        
        # Safety: max 10 chunks
        max_chunks = 10
        
        for i in range(max_chunks):
            start = i * (chunk_size - overlap)
            if start >= text_len:
                break
                
            end = min(start + chunk_size, text_len)
            
            chunks.append({
                'id': i,
                'start': start,
                'end': end
            })
            
            # If we've covered the whole text, stop
            if end >= text_len:
                break
        
        print(f"DEBUG: Created {len(chunks)} chunks safely")
        return chunks
    
    def process_text(self, text: str, source_name: str = "unknown") -> Dict[str, Any]:
        """Main method to process text and build knowledge graph"""
        log_memory_usage("Process start")
        print(f"Processing text: {source_name}")
        print(f"Text length: {len(text)} characters")
        
        # Load existing entity index
        self._load_entity_index()
        print(f"Loaded {len(self.entity_index)} existing entities")
        log_memory_usage("After loading index")
        
        # Split into chunks
        chunks = self._chunk_text(text)
        print(f"Created {len(chunks)} chunks")
        log_memory_usage("After chunking")
        
        # Extract entities from all chunks
        all_entities = []
        for chunk in chunks:
            print(f"Processing chunk {chunk['id']+1}/{len(chunks)}...")
            entities = self._extract_entities_from_chunk(text, chunk['start'], chunk['end'], chunk['id'])
            all_entities.extend(entities)
            print(f"  Found {len(entities)} entities in chunk {chunk['id']+1}")
        
        print(f"Total entities found: {len(all_entities)}")
        log_memory_usage("After entity extraction")
        
        # Process each entity and find relationships
        created_entities = []
        for i, entity in enumerate(all_entities):
            print(f"Processing entity {i+1}/{len(all_entities)}: {entity['name']}")
            
            # Find relationships
            relationships = self._find_relationships(entity, all_entities, text)
            
            # Create chunk references
            chunk_refs = [f"chunk_{entity['chunk_id']}_pos_{entity.get('start', 0)}-{entity.get('end', 0)}"]
            
            # Create entity file
            entity_id = self._create_entity_file(entity, relationships, chunk_refs)
            if entity_id:
                created_entities.append(entity_id)
            
            # Log memory every 5 entities
            if (i + 1) % 5 == 0:
                log_memory_usage(f"After processing {i+1} entities")
        
        log_memory_usage("Process complete")
        
        # Summary
        result = {
            "source": source_name,
            "chunks_processed": len(chunks),
            "entities_found": len(all_entities),
            "entities_created": len(created_entities),
            "created_entity_ids": created_entities,
            "timestamp": datetime.now().isoformat()
        }
        
        return result

def main():
    if len(sys.argv) < 2:
        print("Użycie: python agent/knowledge_graph_builder.py <plik.txt> [model] [entities_dir]")
        print("Models:")
        print(f"  - {Models.QWEN_CODER} (default)")
        print(f"  - {Models.QWEN_CODER_32B}")
        print(f"  - {Models.CODESTRAL}")
        return
    
    text_file = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else Models.QWEN_CODER
    entities_dir = sys.argv[3] if len(sys.argv) > 3 else "entities"
    
    # Read text file
    try:
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Build knowledge graph
    builder = KnowledgeGraphBuilder(entities_dir, model)
    result = builder.process_text(text, text_file)
    
    # Save processing summary
    summary_file = f"kg_summary_{int(time.time())}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== KNOWLEDGE GRAPH BUILT ===")
    print(f"Source: {result['source']}")
    print(f"Chunks processed: {result['chunks_processed']}")
    print(f"Entities found: {result['entities_found']}")
    print(f"Entity files created: {result['entities_created']}")
    print(f"Entities directory: {entities_dir}/")
    print(f"Summary saved: {summary_file}")

if __name__ == "__main__":
    main()