OBECNY FLOW PIPELINE (co robi)
mermaidgraph TD
    A[Document] --> B[TextChunker]
    B --> C[Multiple Chunks]
    C --> D[EntityExtractor]
    D --> E[Auto-classify OR Domains]
    E --> F[Contextual Entities Lookup]
    F --> G[Meta-analysis LLM]
    G --> H[Entity Extraction LLM]
    H --> I[Parsing & Validation]
    I --> J[Batch Clustering]
    J --> K[SemanticStore Update]
    K --> L[Relationship Discovery]
    L --> M[Cross-chunk Relationships]
    M --> N[Final Knowledge Graph]
LUIGI TASKS BREAKDOWN (co trzeba zrobić)
PHASE 1: Document Loading & Chunking
python# ner/pipeline/document_tasks.py (~120 LOC)
class LoadDocument(luigi.Task):           # 25 LOC
class ChunkDocument(luigi.Task):          # 35 LOC
class ValidateChunks(luigi.Task):         # 20 LOC
class InitializeSemanticStore(luigi.Task): # 40 LOC
PHASE 2: Per-Chunk Processing
python# ner/pipeline/chunk_tasks.py (~200 LOC)
class AutoClassifyChunk(luigi.Task):      # 35 LOC
class LoadContextualEntities(luigi.Task): # 30 LOC
class RunMetaAnalysis(luigi.Task):        # 45 LOC
class ExtractRawEntities(luigi.Task):     # 50 LOC
class ValidateEntities(luigi.Task):       # 40 LOC
PHASE 3: Entity Processing
python# ner/pipeline/entity_tasks.py (~180 LOC)
class ClusterChunkEntities(luigi.Task):   # 60 LOC
class StoreEntitiesInSemantic(luigi.Task): # 45 LOC
class GenerateEntityEmbeddings(luigi.Task): # 35 LOC
class UpdateFAISSIndices(luigi.Task):     # 40 LOC
PHASE 4: Relationship Processing
python# ner/pipeline/relationship_tasks.py (~150 LOC)
class ExtractChunkRelationships(luigi.Task): # 50 LOC
class ResolveEntityReferences(luigi.Task):   # 40 LOC
class StoreMergeRelationships(luigi.Task):   # 35 LOC
class BuildRelationshipGraph(luigi.Task):    # 25 LOC
PHASE 5: Cross-Document & Final
python# ner/pipeline/final_tasks.py (~130 LOC)
class DiscoverCrossChunkRelations(luigi.Task): # 45 LOC
class FinalEntityDeduplication(luigi.Task):    # 40 LOC
class BuildKnowledgeGraph(luigi.Task):         # 45 LOC
PHASE 6: Pipeline Infrastructure
python# ner/pipeline/config.py (~80 LOC)
# ner/pipeline/utils.py (~100 LOC)
# ner/pipeline/runner.py (~120 LOC)
PLIKI DO ZMIANY/UTWORZENIA
NOWE PLIKI (15 plików):
ner/pipeline/
├── __init__.py                 # 10 LOC
├── config.py                   # 80 LOC - Luigi config
├── utils.py                    # 100 LOC - helpers
├── runner.py                   # 120 LOC - main orchestrator
├── document_tasks.py           # 120 LOC - Phase 1
├── chunk_tasks.py              # 200 LOC - Phase 2
├── entity_tasks.py             # 180 LOC - Phase 3
├── relationship_tasks.py       # 150 LOC - Phase 4
├── final_tasks.py              # 130 LOC - Phase 5
├── task_mixins.py              # 60 LOC - common functionality
└── luigi.cfg                   # 20 LOC - Luigi configuration

Total NOWE: ~1,170 LOC w 11 plikach
PLIKI DO MODYFIKACJI (12 plików):
python# MAJOR CHANGES:
ner/extractor/base.py           # -300 LOC (remove extract_entities)
                               # +50 LOC (Luigi integration)

ner/extractor/extraction.py    # -200 LOC (extract functions)
                               # +30 LOC (Luigi adapters)

ner/storage/store.py           # +80 LOC (Luigi-friendly methods)

ner/pipeline.py                # -150 LOC (old pipeline)
                               # +40 LOC (Luigi runner integration)

# MINOR CHANGES:
ner/__init__.py                # +20 LOC (Luigi exports)
ner/config.py                  # +15 LOC (Luigi settings)
ner/domains/base.py            # +10 LOC (Luigi compatibility)
ner/domains/literary/literary.py # +10 LOC (Luigi adapters)
orchestrator/main.py           # +25 LOC (Luigi CLI integration)
requirements.txt               # +1 LOC (luigi>=3.3.0)
pyproject.toml                 # +5 LOC (Luigi dependency)
README.md                      # +100 LOC (Luigi documentation)

Total MODYFIKACJE: ~570 LOC zmian w 12 plikach
SZCZEGÓŁOWY EFFORT BREAKDOWN
CORE TASK IMPLEMENTATION:
Document Tasks (Phase 1):
pythonclass LoadDocument(luigi.Task):
    file_path = luigi.Parameter()
    
    def output(self):
        return luigi.LocalTarget(f"temp/document_{hash(self.file_path)}.json")
    
    def run(self):
        # Adapted from current DocumentLoader
        loader = DocumentLoader()
        document = loader.load_document(self.file_path)
        
        with self.output().open('w') as f:
            json.dump({
                'content': document.content,
                'source_file': document.source_file,
                'file_type': document.file_type,
                'metadata': document.metadata
            }, f, indent=2)

class ChunkDocument(luigi.Task):
    file_path = luigi.Parameter()
    model = luigi.Parameter(default="gpt-4o-mini")
    
    def requires(self):
        return LoadDocument(file_path=self.file_path)
    
    def output(self):
        return luigi.LocalTarget(f"temp/chunks_{hash(self.file_path)}.json")
    
    def run(self):
        # Adapted from current TextChunker
        with self.input().open('r') as f:
            document_data = json.load(f)
        
        chunker = TextChunker(model_name=self.model)
        chunks = chunker.chunk_text(document_data['content'])
        
        chunk_data = [chunker.chunk_to_dict(chunk) for chunk in chunks]
        
        with self.output().open('w') as f:
            json.dump(chunk_data, f, indent=2)
Per-Chunk Tasks (Phase 2):
pythonclass AutoClassifyChunk(luigi.Task):
    chunk_id = luigi.Parameter()
    document_path = luigi.Parameter()
    
    def requires(self):
        return ChunkDocument(file_path=self.document_path)
    
    def output(self):
        return luigi.LocalTarget(f"temp/domains_{self.chunk_id}.json")
    
    def run(self):
        # Load chunks, find specific chunk
        with self.input().open('r') as f:
            chunks_data = json.load(f)
        
        chunk_data = next(c for c in chunks_data if c['id'] == int(self.chunk_id))
        
        # Auto-classify (adapted from current AutoNER)
        classifier = AutoNER()
        domains = classifier.classify_chunk_with_llm(chunk_data['text'])
        
        with self.output().open('w') as f:
            json.dump({'domains': domains}, f)
INTEGRATION POINTS
Orchestrator Integration:
python# orchestrator/main.py modifications
def main():
    if args.use_luigi:
        # NEW: Luigi pipeline
        import luigi
        from ner.pipeline import ProcessDocument
        
        luigi.build([
            ProcessDocument(
                file_path=args.input,
                model=args.model,
                domains=args.domains
            )
        ], local_scheduler=True)
    else:
        # OLD: Direct pipeline
        result = process_text_to_knowledge(...)
SemanticStore Integration:
python# ner/storage/store.py additions
class SemanticStore:
    def load_from_luigi_task(self, task_output_path):
        """Load data from Luigi task output"""
        
    def save_for_luigi_task(self, data, task_output_path):
        """Save data for Luigi task consumption"""
        
    def get_luigi_compatible_stats(self):
        """Stats format compatible with Luigi tasks"""
TOTAL EFFORT ESTIMATION
FILES COUNT:

Nowe pliki: 11 files (~1,170 LOC)
Modyfikowane pliki: 12 files (~570 LOC changes)
Razem: 23 files, ~1,740 LOC effort

DEVELOPMENT PHASES:
Phase 1 - Core Tasks (40% effort):

Document loading & chunking tasks
Basic Luigi infrastructure
~696 LOC

Phase 2 - Processing Tasks (35% effort):

Per-chunk processing pipeline
Entity extraction & validation
~609 LOC

Phase 3 - Advanced Features (20% effort):

Relationship processing
Cross-chunk relationships
~348 LOC

Phase 4 - Integration (5% effort):

CLI integration
Documentation updates
~87 LOC

MIGRATION STRATEGY
OPTION A: Big Bang (3-4 dni coding)

Napisz wszystko od razu
Testuj całość na końcu
Risk: Dużo rzeczy może się popsuć

OPTION B: Incremental (5-7 dni coding)

Day 1: Document tasks + chunking
Day 2: Entity extraction tasks
Day 3: Clustering & storage tasks
Day 4: Relationship tasks
Day 5: Integration & testing
Benefit: Każdy krok testowany osobno

OPTION C: Parallel (zachowaj oba)
python# CLI switch
python main.py file.txt --pipeline=luigi     # NEW
python main.py file.txt --pipeline=direct    # OLD (default)
VERDICT
SCOPE SUMMARY:

23 pliki (11 nowych + 12 modyfikowanych)
~1,740 LOC total effort
~5-7 dni development time
Zachowana funkcjonalność + improved debuggability

Bottom line: To significant refactor, ale manageable i bardzo opłacalny dla debuggability i maintainability.
Chcesz żebym zaczął od Phase 1 (document tasks + basic infrastructure)? Czy wolisz Option C (parallel pipelines) żeby zachować working version?

