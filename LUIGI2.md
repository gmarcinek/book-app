# MONO-BLOK 
## 1: ner/extractor/base.py::extract_entities()
Obecny monster (300+ LOC):
pythondef extract_entities(self, chunks: List[TextChunk]) -> List[ExtractedEntity]:
    for chunk in chunks:
        # 1. Auto-classification (jeśli auto mode)
        # 2. Extract entities from chunk 
        # 3. Batch clustering per chunk
        # 4. Store in semantic store
        # 5. Extract relationships 
        # 6. Cross-chunk relationship discovery
        # 7. Final deduplication
Luigi tasks breakdown:
pythonclass ProcessDocument(luigi.Task):           # Master orchestrator
    document_path = luigi.Parameter()
    
    def requires(self):
        return [ProcessChunk(chunk_id=i, document_path=self.document_path) 
                for i in self.get_chunk_ids()]

class ProcessChunk(luigi.Task):              # Per-chunk orchestrator  
    chunk_id = luigi.Parameter()
    document_path = luigi.Parameter()
    
    def requires(self):
        return [
            LoadChunk(chunk_id=self.chunk_id, document_path=self.document_path),
            InitializeSemanticStore(document_path=self.document_path)
        ]

class ExtractChunkEntities(luigi.Task):      # Just entity extraction
class ClusterChunkEntities(luigi.Task):     # Just clustering  
class StoreChunkEntities(luigi.Task):       # Just storage
class ExtractChunkRelationships(luigi.Task): # Just relationships

# MONO-BLOK
## 2: ner/extractor/extraction.py::extract_entities_from_chunk_multi_domain()
Obecny blob (200+ LOC):
pythondef extract_entities_from_chunk_multi_domain(extractor, chunk, domains, domain_names, chunk_id):
    # Auto-classification logic
    if domain_names == ["auto"]:
        domains, domain_names = _auto_classify_chunk(extractor, chunk)
    
    # Multi-domain extraction
    for domain, domain_name in zip(domains, domain_names):
        # Contextual entities lookup
        # Meta-analysis 
        # Entity extraction
        # Validation
        # Stats updating
Luigi tasks breakdown:
pythonclass AutoClassifyChunk(luigi.Task):
    chunk_id = luigi.Parameter()
    document_path = luigi.Parameter()
    
    def run(self):
        # ONLY auto-classification logic

class GetContextualEntities(luigi.Task):  
    chunk_id = luigi.Parameter()
    
    def requires(self):
        return LoadSemanticStore()
    
    def run(self):
        # ONLY contextual entities lookup

class RunMetaAnalysis(luigi.Task):
    chunk_id = luigi.Parameter()
    
    def requires(self):
        return [AutoClassifyChunk(...), GetContextualEntities(...)]
    
    def run(self):
        # ONLY meta-prompt generation

class ExtractRawEntities(luigi.Task):
    chunk_id = luigi.Parameter()
    
    def requires(self):
        return RunMetaAnalysis(...)
    
    def run(self):
        # ONLY LLM extraction + parsing

class ValidateEntities(luigi.Task):
    chunk_id = luigi.Parameter()
    
    def requires(self):
        return ExtractRawEntities(...)
    
    def run(self):
        # ONLY validation + cleaning

# MONO-BLOK 
## 3: ner/pipeline.py::process_text_to_knowledge()
Obecny workflow (150+ LOC):
pythondef process_text_to_knowledge(input_source, entities_dir, model, config, domain_names):
    # Document loading
    # Text chunking  
    # Entity extraction (calls mono-blok #1)
    # Results aggregation
    # Output generation
Luigi tasks breakdown:
pythonclass LoadDocument(luigi.Task):
    file_path = luigi.Parameter()
    
    def run(self):
        # ONLY document loading

class ChunkDocument(luigi.Task):
    file_path = luigi.Parameter()
    model = luigi.Parameter()
    
    def requires(self):
        return LoadDocument(file_path=self.file_path)
    
    def run(self):
        # ONLY text chunking

class InitializeSemanticStore(luigi.Task):
    document_path = luigi.Parameter()
    
    def run(self):
        # ONLY semantic store initialization

class AggregateResults(luigi.Task):
    document_path = luigi.Parameter()
    
    def requires(self):
        return [ProcessChunk(chunk_id=i, document_path=self.document_path) 
                for i in self.get_chunk_ids()]
    
    def run(self):
        # ONLY final aggregation + output generation
        
# DEPENDENCY GRAPH (Luigi będzie enforcing)
mermaidgraph TD
    A[LoadDocument] --> B[ChunkDocument]
    B --> C[InitializeSemanticStore]
    
    C --> D1[ProcessChunk_001]
    C --> D2[ProcessChunk_002] 
    C --> D3[ProcessChunk_N]
    
    D1 --> E1[AutoClassifyChunk_001]
    D1 --> F1[GetContextualEntities_001]
    
    E1 --> G1[RunMetaAnalysis_001]
    F1 --> G1
    
    G1 --> H1[ExtractRawEntities_001]
    H1 --> I1[ValidateEntities_001]
    I1 --> J1[ClusterEntities_001]
    J1 --> K1[StoreEntities_001]
    K1 --> L1[ExtractRelationships_001]
    
    L1 --> M[CrossChunkRelationships]
    M --> N[FinalDeduplication]
    N --> O[AggregateResults]

# SECONDARY MONO-BLOKS (smaller)
ner/extractor/batch_clustering.py::batch_cluster_chunk_entities()
python# Obecny (100+ LOC):

def batch_cluster_chunk_entities(self, chunk_entities, chunk_id):
    # Similarity computation
    # Merge decisions  
    # Entity creation/merging
    # Store updates

# Luigi breakdown:
class ComputeEntitySimilarities(luigi.Task):  # ONLY similarity matrix
class MakeClusterDecisions(luigi.Task):       # ONLY merge decisions
class ExecuteEntityMerges(luigi.Task):        # ONLY merging + storage
ner/storage/store.py::get_contextual_entities_for_ner()
python# Obecny (80+ LOC w różnych metodach):

def get_contextual_entities_for_ner():
    # Embedding generation
    # FAISS search
    # Result formatting

# Luigi breakdown:
class GenerateQueryEmbedding(luigi.Task):     # ONLY embedding  
class SearchSimilarEntities(luigi.Task):     # ONLY FAISS search
class FormatContextualResults(luigi.Task):   # ONLY formatting
TASK GRANULARITY DECISION
COARSE-GRAINED (fewer tasks):
pythonclass ProcessChunk(luigi.Task):               # One task = whole chunk processing
class ExtractEntities(luigi.Task):           # One task = all domains
class ProcessRelationships(luigi.Task):      # One task = all relationships
FINE-GRAINED (many tasks):
pythonclass AutoClassifyChunk(luigi.Task):          # One task = auto-classification only
class GetContextualEntities(luigi.Task):     # One task = contextual lookup only  
class RunMetaAnalysis(luigi.Task):           # One task = meta-prompt only
class ExtractRawEntities(luigi.Task):        # One task = LLM call only
class ValidateEntities(luigi.Task):          # One task = validation only
HYBRID (recommended):

Coarse-grained dla stable, working parts
Fine-grained dla debugging-heavy parts (entity extraction pipeline)

KONKRETNE BOUNDARIES
DEFINITYWNIE ROZBIĆ:

extract_entities() → 8-10 Luigi tasks
extract_entities_from_chunk_multi_domain() → 5-6 Luigi tasks
process_text_to_knowledge() → 4-5 Luigi tasks

PRAWDOPODOBNIE ROZBIĆ:
4. batch_cluster_chunk_entities() → 3-4 Luigi tasks
5. Contextual entities lookup → 2-3 Luigi tasks
ZOSTAW JAKO LIBRARIES:

All domain prompts & logic
SemanticStore internal methods
LLM clients
Document loaders
Validation functions

Czy widzisz jakieś inne mono-bloki które powinienem rozbić? Lub może któryś z tych wydaje Ci się za drobny dla Luigi task?