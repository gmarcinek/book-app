# PIPELINE.md

Luigi Pipeline Documentation - skrócona instrukcja uruchamiania tasków

## 🚀 Quick Start

### Poetry (Recommended)

```bash
poetry run luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/your-file.pdf" --local-scheduler
```

### Pip

```bash
luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/your-file.pdf" --local-scheduler
```

## 📋 Available Tasks

### 1. ConditionalProcessor (Full Pipeline)

**Auto-detects file type and runs appropriate processing chain**

**Poetry:**

```bash
poetry run luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/document.pdf" --local-scheduler
```

**Pip:**

```bash
luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/document.pdf" --local-scheduler
```

### 2. LLMMarkdownProcessor (PDF → Markdown with Batch Processing)

**Converts PDF pages to Markdown using LLM vision models with parallel batch processing**

**Poetry:**

```bash
poetry run luigi --module luigi_pipeline.tasks.preprocessing.llm_markdown_processor LLMMarkdownProcessor --file-path "docs/document.pdf" --local-scheduler
```

**Pip:**

```bash
luigi --module luigi_pipeline.tasks.preprocessing.llm_markdown_processor LLMMarkdownProcessor --file-path "docs/document.pdf" --local-scheduler
```

### 3. PDFProcessing (PDF → Images + Text)

**Extracts images and text from PDF pages**

**Poetry:**

```bash
poetry run luigi --module luigi_pipeline.tasks.preprocessing.pdf_processing PDFProcessing --file-path "docs/document.pdf" --local-scheduler
```

**Pip:**

```bash
luigi --module luigi_pipeline.tasks.preprocessing.pdf_processing PDFProcessing --file-path "docs/document.pdf" --local-scheduler
```

### 4. TextPreprocessing (Text Files)

**Processes plain text files**

**Poetry:**

```bash
poetry run luigi --module luigi_pipeline.tasks.preprocessing.text_processing TextPreprocessing --file-path "docs/document.txt" --local-scheduler
```

**Pip:**

```bash
luigi --module luigi_pipeline.tasks.preprocessing.text_processing TextPreprocessing --file-path "docs/document.txt" --local-scheduler
```

### 5. FileRouter (Auto File Type Detection)

**Determines processing strategy based on file type**

**Poetry:**

```bash
poetry run luigi --module luigi_pipeline.tasks.preprocessing.file_router FileRouter --file-path "docs/document.pdf" --local-scheduler
```

**Pip:**

```bash
luigi --module luigi_pipeline.tasks.preprocessing.file_router FileRouter --file-path "docs/document.pdf" --local-scheduler
```

## ⚙️ Configuration

Edit `luigi_pipeline/config.yaml` to customize processing settings:

```yaml
LLMMarkdownProcessor:
  model: "claude-3.5-haiku" # LLM model to use
  batch_size: 5 # Pages per batch (parallel processing)
  max_concurrent_batches: 1 # Max batches running concurrently
  batch_delay: 5.0 # Delay between batch groups (seconds)
  rate_limit_backoff: 20.0 # Wait time after rate limit error
  retry_failed_pages: true # Retry failed pages
  temperature: 0.0 # LLM temperature
```

## 📁 Output Structure

All tasks output to `output/` directory:

```
output/
├── llm_markdown_HASH.json           # LLM processing results
├── combined_markdown_HASH.md        # Combined markdown from all pages
├── markdown_HASH/                   # Individual page markdowns
│   ├── page_001_OK.md
│   ├── page_002_OK.md
│   └── ...
└── conditional_processor_HASH.json  # Final pipeline results
```

## 🔧 Task Parameters

### Common Parameters

- `--file-path` - Path to input file (required)
- `--preset` - Processing preset (default: "default")
- `--local-scheduler` - Use local Luigi scheduler

### LLMMarkdownProcessor Specific

- All parameters come from `config.yaml`
- Override with environment variables if needed

## 📊 Batch Processing Performance

**Current Setup (Claude 3.5 Haiku):**

- **Batch Size**: 5 pages processed in parallel
- **Expected Speedup**: ~5x faster than sequential processing
- **Rate Limits**: 50 RPM, 50k ITPM, 10k OTPM
- **Cost**: ~$0.017 per 5-page batch

## 🐛 Troubleshooting

### Common Issues

**Rate Limit Errors:**

- Reduce `batch_size` in config.yaml
- Increase `batch_delay` between batches
- Check API usage quotas

**Vision Errors:**

- Ensure Claude models are in `VISION_MODELS` in `llm/models.py`
- Check image format auto-detection in `llm/utils.py`

**Max Tokens Errors:**

- Verify `MODEL_MAX_TOKENS` limits in `llm/models.py`
- Claude 3.5 Haiku: 8192 tokens max
- Claude 3 Haiku: 4096 tokens max

### Debug Mode

Add `--log-level DEBUG` for verbose logging:

```bash
poetry run luigi --module luigi_pipeline.tasks.conditional_processor ConditionalProcessor --file-path "docs/test.pdf" --local-scheduler --log-level DEBUG
```

## 🚀 Performance Tips

1. **Use Claude 3.5 Haiku** for best cost/performance balance
2. **Batch size 5** works well for most documents
3. **Monitor rate limits** in logs - adjust delays if needed
4. **Use SSD storage** for faster intermediate file I/O
5. **Concurrent batches = 1** is usually optimal to avoid rate limits

## 📈 Supported File Types

- **PDF**: Full processing with vision extraction
- **TXT/MD**: Text-only processing
- **Auto-detection**: Based on file extension

## 🔄 Pipeline Flow

```
Input File
    ↓
FileRouter (detect type)
    ↓
┌─ PDF ──→ PDFProcessing ──→ LLMMarkdownProcessor ──→ MarkdownCombiner
│
└─ TXT ──→ TextPreprocessing
    ↓
ConditionalProcessor (final results)
```
