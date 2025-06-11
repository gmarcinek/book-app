# Book Agent - NER Module Commands

## Quick Start

```bash
# Basic usage - single file
poetry run app document.pdf

# With specific model
poetry run app book.docx --model claude-4-sonnet

# Batch processing
poetry run app documents/ --batch
```

## Available Models

| Model               | Provider  | Description                                | Cost | NER Quality |
| ------------------- | --------- | ------------------------------------------ | ---- | ----------- |
| `qwen2.5-coder`     | Ollama    | **Default** - Fast, local, coding-oriented | Free | ⭐⭐ |
| `qwen2.5-coder:32b` | Ollama    | Larger version, better quality             | Free | ⭐⭐⭐ |
| `codestral`         | Ollama    | Alternative local model                    | Free | ⭐⭐ |
| `claude-4-sonnet`   | Anthropic | **Best quality** - Premium model           | $$$$ | ⭐⭐⭐⭐⭐ |
| `claude-4-opus`     | Anthropic | **Highest intelligence** - Most expensive  | $$$$$ | ⭐⭐⭐⭐⭐ |
| `claude-3.5-sonnet` | Anthropic | Very good quality, fast                   | $$$ | ⭐⭐⭐⭐ |
| `claude-3.5-haiku`  | Anthropic | **Best for NER** - Fast, cheap, reliable  | $ | ⭐⭐⭐⭐ |
| `claude-3-haiku`    | Anthropic | Cheapest Claude, basic quality            | $ | ⭐⭐⭐ |
| `gpt-4o`            | OpenAI    | High quality GPT model                     | $$$ | ⭐⭐⭐⭐ |
| `gpt-4o-mini`       | OpenAI    | Cheaper GPT option                         | $$ | ⭐⭐⭐ |
| `gpt-4.1-mini`      | OpenAI    | Latest mini version                        | $$ | ⭐⭐⭐ |

### Recommendations by Use Case

**📊 NER/Entity Extraction:**
- **Best value**: `claude-3.5-haiku` - 10x cheaper than Sonnet, reliable JSON
- **Budget**: `claude-3-haiku` - 12x cheaper, may need retries
- **Premium**: `claude-4-sonnet` - highest accuracy

**🧠 Complex Analysis:**
- **Best**: `claude-4-opus` - most intelligent
- **Balanced**: `claude-4-sonnet` - great quality/cost ratio
- **Good**: `claude-3.5-sonnet` - fast and reliable

**💻 Local/Free:**
- **Default**: `qwen2.5-coder` - good for most tasks
- **Better**: `qwen2.5-coder:32b` - higher quality, slower

### Single File Processing

```bash
# Minimal - uses all defaults
poetry run app document.txt

# Specify model
poetry run app file.pdf --model claude-4-sonnet

# Custom entities directory
poetry run app book.docx --entities-dir my_knowledge

# Skip relationships (faster)
poetry run app large_file.pdf --no-relationships

# Enable conflict resolution
poetry run app document.txt --resolve

# Single domain scan
poetry run app docs/kamienica.txt --model gpt-4o-mini --domains simple

# Auto domain scan
poetry run app docs/kamienica.txt --model gpt-4o-mini
```

### Batch Processing

```bash
# Process all files in directory
poetry run app documents/ --batch

# Specific file pattern
poetry run app books/ --batch --pattern "*.pdf"

# Multiple patterns (process PDFs and DOCX)
poetry run app library/ --batch --pattern "*.{pdf,docx}"

# Text files only
poetry run app texts/ --batch --pattern "*.txt"
```

## Advanced Options

### Model & Performance

```bash
# Use high-quality cloud model
poetry run app document.pdf --model claude-4-sonnet

# Local model for privacy
poetry run app sensitive.txt --model qwen2.5-coder:32b

# Increase file size limit (default 50MB)
poetry run app huge_book.pdf --max-size 200.0

# Custom config file
poetry run app file.txt --config my_ner_config.json
```

### Features Control

```bash
# Skip relationship extraction (much faster)
poetry run app document.pdf --no-relationships

# Enable duplicate resolution
poetry run app messy_data.txt --resolve

# Skip aggregated graph creation
poetry run app file.txt --no-aggregation

# All features enabled
poetry run app complete.pdf --resolve
```

### Output Control

```bash
# Quiet mode (minimal output)
poetry run app document.pdf --quiet

# Verbose mode (detailed stats)
poetry run app file.txt --verbose

# JSON output (for scripting)
poetry run app data.pdf --json > result.json

# Custom output file name
poetry run app book.pdf --output my_knowledge_graph.json
```

## File Format Support

| Format     | Extension | Description        | Notes                         |
| ---------- | --------- | ------------------ | ----------------------------- |
| Plain Text | `.txt`    | Simple text files  | UTF-8 encoding preferred      |
| Markdown   | `.md`     | Markdown documents | Full syntax support           |
| PDF        | `.pdf`    | PDF documents      | Text extraction only (no OCR) |
| Word       | `.docx`   | Microsoft Word     | Modern format only            |
| RTF        | `.rtf`    | Rich Text Format   | Cross-platform text           |

## Examples by Use Case

### Academic Research

```bash
# Process research papers
poetry run app papers/ --batch --pattern "*.pdf" --model claude-4-sonnet --resolve

# Single paper with detailed analysis
poetry run app research.pdf --model claude-4-sonnet --verbose --resolve
```

### Book Analysis

```bash
# Analyze entire book
poetry run app "War and Peace.txt" --model qwen2.5-coder:32b --resolve

# Multiple books
poetry run app library/ --batch --pattern "*.{txt,pdf}" --entities-dir book_knowledge
```

### Quick Testing

```bash
# Fast processing for testing
poetry run app sample.txt --no-relationships --quiet

# Local model for privacy
poetry run app confidential.pdf --model qwen2.5-coder --no-relationships
```

### Production Processing

```bash
# Full pipeline with all features
poetry run app documents/ --batch --model claude-4-sonnet --resolve --verbose

# Custom configuration for specific domain
poetry run app legal_docs/ --batch --config legal_ner_config.json --resolve
```

## Output Structure

### Entity Files

```
entities/
├── ent.1234567890123456.abcd1234.json  # Individual entity
├── ent.1234567890123457.efgh5678.json
└── ...
```

### Aggregated Graph

```
knowledge_graph_document_20231206_143022.json
```

### Example Entity File Structure

```json
{
  "id": "ent.1234567890123456.abcd1234",
  "name": "Shakespeare",
  "type": "OSOBA",
  "description": "English playwright and poet",
  "confidence": 0.95,
  "source_info": {
    "evidence": "William Shakespeare was born in...",
    "chunk_references": ["chunk_0_pos_1250-4250"],
    "found_in_chunks": [0],
    "source_document": "literature.pdf"
  },
  "relationships": {
    "internal": [
      {
        "type": "WROTE",
        "target_entity": "Hamlet",
        "evidence": "Shakespeare wrote Hamlet in...",
        "confidence": 0.9
      }
    ],
    "external": [
      {
        "type": "BIRTH_YEAR",
        "value": "1564",
        "source": "historical_record"
      }
    ],
    "pending": [
      {
        "name": "Anne Hathaway",
        "type": "OSOBA",
        "reason": "Mentioned as Shakespeare's wife"
      }
    ]
  },
  "metadata": {
    "created": "2023-12-06T14:30:22.123456",
    "last_updated": "2023-12-06T14:30:22.123456",
    "model_used": "claude-4-sonnet",
    "extraction_method": "llm_chunk_based"
  }
}
```

## Troubleshooting

### Common Issues

**"File not found"**

```bash
# Check file exists
ls -la document.pdf

# Use absolute path
poetry run app /full/path/to/document.pdf
```

**"LLM model not available"**

```bash
# For Ollama models, ensure Ollama is running
ollama serve

# Pull model if not available
ollama pull qwen2.5-coder

# List available models
ollama list
```

**"Memory issues with large files"**

```bash
# Increase system memory or reduce file size
poetry run app large.pdf --max-size 25.0

# Skip relationships to reduce memory usage
poetry run app large.pdf --no-relationships
```

**"API key errors for cloud models"**

```bash
# Set environment variables
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"

# Or use local models
poetry run app document.pdf --model qwen2.5-coder
```

### Performance Tips

1. **Use local models** for faster, free processing
2. **Skip relationships** (`--no-relationships`) for 2-3x speed boost
3. **Process in batches** rather than individual files
4. **Use `--quiet`** mode to reduce I/O overhead
5. **Increase `--max-size`** only if you have sufficient RAM

### Getting Help

```bash
# Show all available options
poetry run app --help

# Check model availability
poetry run app document.txt --model nonexistent-model
```
