# Document Splitter Pipeline

Splits PDF documents into logical sections based on Table of Contents (TOC) structure detected by `luigi_toc_pipeline`.

## Overview

The pipeline takes TOC-enabled PDF documents and creates separate PDF files for each major section, preserving original formatting, metadata, and Unicode encoding. This enables downstream processing of individual document sections rather than entire documents.

## Architecture

```
DocumentSplitter
├── Built-in TOC? → Direct splitting (no dependencies)
└── No built-in TOC? → TOCOrchestrator (from luigi_toc_pipeline)
    └── Complete TOC detection chain
```

**Conditional Dependency Design**: Smart routing based on PDF capabilities - uses built-in TOC when available, falls back to detection when needed.

## Usage

### Basic Usage

```bash
# Split document using detected TOC
poetry run python luigi_document_splitter_pipeline/run_splitter_pipeline.py "docs/document.pdf"

# Direct Luigi execution
poetry run luigi --module luigi_document_splitter_pipeline.tasks.document_splitter DocumentSplitter --file-path "docs/document.pdf" --local-scheduler
```

### Batch Processing

```bash
# Process multiple documents
for pdf in docs/*.pdf; do
  poetry run python luigi_document_splitter_pipeline/run_splitter_pipeline.py "$pdf"
done
```

## How It Works

### 1. TOC Source Detection

**Conditional Logic**:

```python
def requires(self):
    if has_builtin_toc(pdf):
        return None  # No dependencies needed
    else:
        return TOCOrchestrator(file_path=self.file_path)
```

**Built-in TOC Path**:

- Uses `doc.get_toc()` to extract embedded TOC structure
- **Performance**: Instant processing, no LLM calls
- **Reliability**: High accuracy from PDF metadata
- **Level Support**: Automatically handles hierarchical levels

**Detected TOC Path** (fallback):

- Runs complete `luigi_toc_pipeline` detection chain
- **Performance**: Slower due to LLM verification
- **Reliability**: Good for documents without embedded TOC

### 2. Level-Based Section Creation

**For Built-in TOC**:

- **Level 1 Sections**: Major chapters/parts → `document_name_lvl_1/`
- **Level 2 Sections**: Subsections/articles → `document_name_lvl_2/`
- **Separate Folders**: Each level gets independent folder structure

**For Detected TOC**:

- **Single Level**: All detected entries → `document_name/`
- **Flat Structure**: No level hierarchy available

### 3. Section Boundary Calculation

**Algorithm**:

```python
for each TOC entry:
  start_page = entry.page
  end_page = next_entry.page - 1  # or document end
  extract_pages(start_page, end_page)
```

**Edge Cases**:

- **Missing page numbers**: Entry skipped with warning
- **Last section**: Extends to document end
- **Single page sections**: Handled correctly
- **Page gaps**: Included in current section

### 3. PDF Creation Process

**For each section**:

1. **Metadata Preservation**: Copy and modify original PDF metadata
2. **Page Extraction**: Use `insert_pdf()` to preserve all content (fonts, images, links)
3. **Filename Generation**: Sanitize title + zero-padded index
4. **Quality Optimization**: Apply compression while preserving Unicode

## Configuration (`config.yaml`)

### Basic Settings

```yaml
DocumentSplitter:
  # File naming
  max_filename_length: 50 # Maximum characters in section filename
  max_sections: 100 # Safety limit to prevent runaway splitting

  # Section boundaries
  overlap_pages: 0 # Pages to overlap between sections (future feature)
```

### Configuration Explanations

| Setting               | Purpose                       | Recommended Value | Notes                                    |
| --------------------- | ----------------------------- | ----------------- | ---------------------------------------- |
| `max_filename_length` | Prevent filesystem issues     | 50                | Windows has 255 char limit for full path |
| `max_sections`        | Safety against malformed TOCs | 100               | Typical documents have <50 sections      |
| `overlap_pages`       | Future: Include context pages | 0                 | Not implemented yet                      |

## Output Structure

### File Organization

**Built-in TOC Output** (with levels):

```
output/
├── doc_splitting/
│   └── document_splitter/
│       └── document_splitter.json         # Task results and metadata
└── sections/
    ├── document_name_lvl_1/                # Level 1: Major sections
    │   ├── section_01_introduction.pdf
    │   ├── section_02_methodology.pdf
    │   └── section_03_results.pdf
    └── document_name_lvl_2/                # Level 2: Subsections
        ├── section_01_basic_concepts.pdf
        ├── section_02_advanced_topics.pdf
        └── section_03_implementation.pdf
```

**Detected TOC Output** (flat structure):

```
output/
├── doc_splitting/
│   └── document_splitter/
│       └── document_splitter.json         # Task results and metadata
└── sections/
    └── document_name/                      # Single level
        ├── section_01_introduction.pdf
        ├── section_02_general_conditions.pdf
        └── section_03_life_insurance.pdf
```

### Filename Convention

**Pattern**: `section_{index:02d}_{sanitized_title}.pdf`

**Examples**:

- `section_01_wprowadzenie.pdf`
- `section_02_ogólne_warunki_ubezpieczenia.pdf`
- `section_03_art_1_co_oznaczają_używane_pojęcia.pdf`

**Sanitization Rules**:

- Replace problematic characters: `<>:"/\|?*` → `_`
- Normalize whitespace: multiple spaces → single `_`
- Strip leading/trailing dots and underscores
- Truncate to `max_filename_length`

## JSON Output Format

### Built-in TOC Success Response

```json
{
  "status": "success",
  "method": "builtin_toc",
  "total_sections_created": 7,
  "level_1_sections": 3,
  "level_2_sections": 4,
  "sections": [
    {
      "title": "Introduction",
      "filename": "section_01_introduction.pdf",
      "file_path": "output/sections/doc_lvl_1/section_01_introduction.pdf",
      "start_page": 5,
      "end_page": 12,
      "pages_count": 8,
      "level": 1,
      "section_index": 0
    },
    {
      "title": "Basic Concepts",
      "filename": "section_01_basic_concepts.pdf",
      "file_path": "output/sections/doc_lvl_2/section_01_basic_concepts.pdf",
      "start_page": 6,
      "end_page": 9,
      "pages_count": 4,
      "level": 2,
      "section_index": 0
    }
  ],
  "output_base_directory": "output/doc_splitting/sections"
}
```

### Detected TOC Success Response

```json
{
  "status": "success",
  "method": "detected_toc",
  "total_sections_created": 4,
  "sections": [
    {
      "title": "Ogólne warunki ubezpieczenia na życie",
      "filename": "section_01_ogólne_warunki_ubezpieczenia_na_życie.pdf",
      "start_page": 4,
      "end_page": 11,
      "pages_count": 8
    }
  ],
  "output_directory": "output/doc_splitting/sections/insurance_document"
}
```

### Failure Response

```json
{
  "status": "no_toc",
  "reason": "TOC not found",
  "sections_created": 0
}
```

## PDF Processing Details

### Metadata Preservation

**Original metadata is preserved and enhanced**:

```python
section_metadata = {
  "title": f"{original.title} - {section_title}",
  "author": original.author,                    # Unchanged
  "subject": f"Section {index}: {section_title}",
  "creator": original.creator,                  # Unchanged
  "producer": f"DocumentSplitter (original: {original.producer})"
}
```

**Benefits**:

- **Traceability**: Clear connection to source document
- **Tool Compatibility**: PDF readers show meaningful titles
- **Metadata Integrity**: Preserves original authorship info

### Content Preservation

**Technical Implementation**:

```python
# Insert pages with full fidelity
section_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)

# Save with Unicode preservation
section_doc.save(file_path,
                garbage=3,      # Remove unused objects (optimization)
                clean=True,     # Clean PDF structure
                ascii=False)    # Preserve Unicode characters
```

**Preserved Elements**:

- ✅ **Text**: All fonts, Unicode characters, formatting
- ✅ **Images**: Full resolution, embedded images
- ✅ **Links**: Internal and external hyperlinks
- ✅ **Bookmarks**: PDF navigation structure
- ✅ **Forms**: Interactive PDF form fields
- ✅ **Annotations**: Comments, highlights, notes

## Error Handling

### Common Scenarios

| Scenario                  | Handling                   | Output                            |
| ------------------------- | -------------------------- | --------------------------------- |
| No TOC found              | Graceful failure           | `status: "no_toc"` + reason       |
| Entry without page number | Skip with warning          | Continue processing other entries |
| Invalid page range        | Clamp to document bounds   | Extract available pages           |
| Filesystem error          | Log error, continue        | Skip problematic section          |
| Empty TOC entries         | Return empty sections list | `sections_created: 0`             |

### Debug Information

**Console Output**:

```
📄 Created: section_01_introduction.pdf (pages 5-12)
⚠️ Skipping entry 'Appendix A' - no page number
📄 Created: section_02_methodology.pdf (pages 13-25)
✅ Document split into 3 sections
   Output: output/doc_splitting/sections/research_paper
```

**File-level Debugging**:

- Check output JSON for complete section list
- Verify TOC detection quality in `luigi_toc_pipeline` debug output
- Examine individual section PDFs for content integrity

## Integration Patterns

### Downstream Processing

**Common usage after splitting**:

```bash
# 1. Split document
poetry run python luigi_document_splitter_pipeline/run_splitter_pipeline.py "contract.pdf"

# 2. Process each section individually
for section in output/doc_splitting/sections/contract/*.pdf; do
  # NER processing, translation, analysis, etc.
  process_document "$section"
done
```

### Pipeline Chaining

```python
# In Luigi task
class MyDocumentProcessor(luigi.Task):
    def requires(self):
        return DocumentSplitter(file_path=self.file_path)

    def run(self):
        # Load splitting results
        with self.input().open('r') as f:
            split_data = json.load(f)

        # Process each section
        for section in split_data['sections']:
            self.process_section(section['file_path'])
```

## Performance Considerations

### Processing Speed

**Typical Performance**:

**Built-in TOC** (fast path):

- **Small documents** (10-50 pages): 0.5-1 seconds
- **Medium documents** (50-200 pages): 1-3 seconds
- **Large documents** (200+ pages): 3-8 seconds

**Detected TOC** (with LLM):

- **Small documents**: 10-30 seconds (TOC detection overhead)
- **Medium documents**: 15-45 seconds
- **Large documents**: 30-90 seconds

**Bottlenecks**:

1. **TOC Detection**: Dominates processing time for detected TOC path
2. **PDF I/O**: Minimal impact with PyMuPDF optimization
3. **Level Processing**: Minimal overhead for built-in TOC levels

### Memory Usage

**Memory Efficient**:

- Processes one section at a time
- No full document loading into memory
- Automatic cleanup of temporary objects

**Scaling**:

- **Linear**: Processing time scales with document size
- **Parallel**: Can process multiple documents simultaneously
- **Storage**: Output size ≈ 1.1x original (metadata overhead)

## Dependencies

### Core Dependencies

- **`luigi_toc_pipeline`**: TOC detection and extraction
- **`luigi_components.structured_task`**: Task base class with standardized output
- **`PyMuPDF (fitz)`**: PDF manipulation and content preservation

### System Requirements

- **Python 3.8+**: For pathlib and typing support
- **Disk Space**: 2x document size (original + sections)
- **Memory**: 100-500MB for typical documents

## Limitations

### Current Limitations

1. **TOC Dependency**: Cannot split documents without detectable or built-in TOC
2. **Level Limitation**: Built-in TOC splits only Level 1 and Level 2 (ignores deeper levels)
3. **Page-based Boundaries**: Cannot split within pages
4. **Sequential Sections**: Assumes non-overlapping, sequential sections

### Future Enhancements

1. **Deeper Level Support**: Handle Level 3+ for built-in TOC
2. **Content-based Boundaries**: Split on semantic boundaries, not just pages
3. **Overlap Support**: Include context pages between sections
4. **Custom Rules**: Domain-specific splitting logic (legal articles, chapters, etc.)
5. **Bookmark Preservation**: Maintain internal PDF navigation for complex documents
6. **Multi-column Detection**: Handle complex layouts

## Troubleshooting

### Common Issues

**No sections created**:

1. **Built-in TOC path**: Check if `doc.get_toc()` returns valid entries
2. **Detected TOC path**: Check if TOC was detected in `output/toc_processing/toc_orchestrator/toc_orchestrator.json`
3. Verify TOC entries have page numbers
4. Check console output for specific error messages

**Wrong output structure**:

1. **Built-in TOC**: Should create `document_name_lvl_1/` and `document_name_lvl_2/` folders
2. **Detected TOC**: Should create single `document_name/` folder
3. Check JSON output for `method` field to confirm which path was used

**Missing sections**:

1. Review TOC entries for missing page numbers
2. Check filename sanitization didn't create conflicts
3. Verify page ranges don't exceed document bounds

**Content quality issues**:

1. Original PDF may have embedded content issues
2. Check if fonts are properly embedded in source
3. Verify Unicode preservation with `ascii=False` setting

**Performance issues**:

1. Most time spent in TOC detection (upstream)
2. Check available disk space for output
3. Consider processing smaller documents first

### Debug Commands

```bash
# Check TOC detection results
cat output/toc_processing/toc_orchestrator/toc_orchestrator.json | jq '.toc_entries'

# Verify section file creation
ls -la output/doc_splitting/sections/*/

# Check splitting results
cat output/doc_splitting/document_splitter/document_splitter.json | jq '.sections'
```
