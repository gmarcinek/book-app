# TOC Pipeline

Advanced Table of Contents (TOC) detection and extraction from PDF documents using hybrid heuristic pattern detection and LLM verification.

## Overview

The pipeline combines pattern-based search with AI verification to reliably find and extract structured TOC data from PDF documents. It handles multi-language documents and provides extensive debug output for analysis.

## Architecture

```
TOCOrchestrator
└── TOCFallbackLLMStrategy (TODO: Currently pass-through)
    └── TOCHeuristicDetector
        ├── PatternDetector (Stage 1: Find candidates)
        └── VerificationEngine (Stage 2: LLM verification)
```

## Usage

### Basic Usage

```bash
# Find TOC in document
poetry run python luigi_toc_pipeline/run_toc_pipeline.py "docs/document.pdf"

# Direct Luigi execution
poetry run luigi --module luigi_toc_pipeline.tasks.toc_orchestrator TOCOrchestrator \
  --file-path "docs/document.pdf" --local-scheduler
```

### Advanced Usage

```bash
# With debug output and logging
poetry run luigi --module luigi_toc_pipeline.tasks.toc_orchestrator TOCOrchestrator \
  --file-path "docs/document.pdf" --local-scheduler --log-level DEBUG
```

## Pipeline Stages

### Stage 1: Pattern Detection (`TOCPatternDetector`)

**Purpose**: Find ALL potential TOC locations using regex patterns

**Process**:

1. Scans first N pages (configurable) for TOC keywords
2. For each match, attempts to find TOC boundaries
3. Categorizes candidates by confidence:
   - **Certain**: High confidence patterns, close to document start
   - **Uncertain**: Suspicious patterns, needs LLM verification
   - **Rejected**: False positives, bad proximity/structure

**Patterns Detected**:

- Multi-language keywords: `spis treści`, `table of contents`, `contents`, `indice`, `sommaire`
- TOC entry patterns: dot leaders (`Title...123`), numbered sections (`1.1 Title 25`)
- Content start patterns: `Rozdział 1`, `Chapter 1`, `Introduction`

### Stage 2: LLM Verification (`TOCVerificationEngine`)

**Purpose**: Verify uncertain candidates and extract structured TOC entries

**Process**:

1. Creates cropped PDF for each candidate (debug-friendly)
2. Uses `PDFLLMProcessor` with Claude vision + text extraction
3. Parses LLM response for structured TOC entries
4. Circuit breaker: stops after too many rejections/failures

**LLM Processing**:

- **Model**: Claude 3.5 Haiku (fast, cost-effective)
- **Input**: PDF screenshot + extracted text (with cleaning)
- **Output**: JSON with `{"entries": [{"title": "...", "page": 123, "level": 1, "type": "chapter"}]}`
- **Rate Limiting**: 30s backoff on rate limits

### Stage 3: Orchestration (`TOCOrchestrator`)

**Purpose**: Select best TOC and format final output

**Selection Criteria**:

1. Earliest page number (TOCs usually come first)
2. Most entries found
3. Highest confidence ratio

## Configuration (`config.yaml`)

### Core Detection Settings

```yaml
TOCDetector:
  # Scanning limits
  max_pages_to_scan: 1000 # Maximum pages to scan for TOC (performance limit)
  min_toc_entries: 3 # Minimum entries required to consider valid TOC

  # Pattern detection
  toc_keywords: # Keywords that indicate TOC start
    - "spis treści" # Polish
    - "treść"
    - "table of contents" # English
    - "contents"
    - "indice" # Spanish/Italian
    - "sommaire" # French
    - "chapter contents"
```

### LLM Verification Settings

```yaml
verification_processor: # PDFLLMProcessor configuration
  # Core LLM settings
  model: "claude-3.5-haiku" # Claude model for verification
  temperature: 0.0 # Deterministic output (0.0 = no randomness)
  max_tokens: null # Use model default (8192 for Haiku)

  # PDF processing
  clean_text: true # Clean extracted text (remove artifacts, normalize spaces)
  target_width_px: 900 # Screenshot width for vision processing
  jpg_quality: 75 # JPEG quality (75 = good balance of size/quality)

  # Performance & reliability
  max_concurrent: 1 # Parallel LLM calls (1 = sequential, safer for rate limits)
  rate_limit_backoff: 30.0 # Seconds to wait on rate limit (Claude: 30s recommended)

  # Processing limits (circuit breaker)
  max_candidates: 50 # Abort if too many candidates (token protection)
  max_rejected_count: 5 # Stop after N rejections (pattern detection failing)

  # LLM prompt template
  vision_prompt: | # Template sent to Claude (text replacement: {text_content})
    Analyze the extracted Table of Contents (TOC) section using text and images.
    EXTRACTED TEXT:
    {text_content}

    TASK: Parse all visible TOC entries into JSON...
```

### Configuration Explanations

| Setting              | Purpose                               | Recommended Value                  |
| -------------------- | ------------------------------------- | ---------------------------------- |
| `max_pages_to_scan`  | Performance limit for large documents | 1000 (covers most documents)       |
| `clean_text`         | Remove PDF extraction artifacts       | `true` (improves LLM parsing)      |
| `target_width_px`    | Screenshot resolution                 | 900 (good detail without bloat)    |
| `max_concurrent`     | Parallel LLM calls                    | 1 (avoid rate limits)              |
| `rate_limit_backoff` | Wait time on rate limits              | 30.0 (Claude's typical reset time) |
| `max_candidates`     | Token protection limit                | 50 (prevents runaway costs)        |

## Output Structure

### File Organization

```
output/
├── toc_processing/
│   ├── toc_heuristic_detector/
│   │   ├── toc_heuristic_detector.json    # Stage 1 results
│   │   └── debug/
│   │       ├── toc_certain_0_page_2_20250105_123456.png      # Debug screenshots
│   │       ├── toc_verification_candidate_123.pdf           # LLM input PDFs
│   │       ├── toc_detection_summary_20250105_123456.json   # Complete analysis
│   │       └── verification_candidate_123_20250105.json     # LLM responses
│   ├── toc_fallback_llm_strategy/
│   │   └── toc_fallback_llm_strategy.json  # Stage 2 results (TODO: Currently pass-through)
│   └── toc_orchestrator/
│       └── toc_orchestrator.json          # Final results
```

### JSON Output Format

#### Success Response

```json
{
  "task_name": "TOCOrchestrator",
  "input_file": "docs/document.pdf",
  "toc_found": true,
  "detection_method": "llm_processing",
  "coordinates": {
    "start_page": 2,
    "end_page": 3,
    "start_y": 150.5,
    "end_y": 750.2
  },
  "toc_entries": [
    {
      "title": "Ogólne warunki ubezpieczenia na życie",
      "page": 4,
      "level": 1,
      "type": "chapter"
    },
    {
      "title": "Art. 1 Co oznaczają używane pojęcia?",
      "page": 4,
      "level": 2,
      "type": "section"
    }
  ],
  "toc_entries_count": 15,
  "ready_for_splitting": true,
  "processing_stats": {
    "certain_count": 1,
    "uncertain_count": 2,
    "processed_count": 3,
    "rejected_count": 1
  }
}
```

#### Failure Response

```json
{
  "task_name": "TOCOrchestrator",
  "input_file": "docs/document.pdf",
  "toc_found": false,
  "reason": "no_confirmed_tocs_after_processing",
  "ready_for_splitting": false,
  "processing_stats": {
    "certain_count": 0,
    "uncertain_count": 3,
    "processed_count": 0,
    "rejected_count": 3
  }
}
```

## Debug Features

### Visual Debug Output

- **Screenshots** (`*.png`): Visual confirmation of detected TOC areas with margins
- **Verification PDFs** (`toc_verification_*.pdf`): Exact cropped sections sent to LLM
- **Detection Summary** (`toc_detection_summary_*.json`): Complete analysis with base64 images

### Processing Debug

- **Verification JSONs** (`verification_*.json`): LLM request/response pairs
- **Circuit Breaker Logs**: When and why processing was aborted
- **Timing Information**: Processing duration for performance analysis

## Error Handling

### Circuit Breakers

1. **Too Many Candidates** (>25): Pattern detection likely malfunctioning
2. **Too Many Rejections** (≥4): Pattern quality too low, LLM consistently rejecting
3. **Too Many Failures** (≥3): LLM/API issues, avoid token waste

### Common Failure Modes

| Scenario                | Cause                        | Debug Approach                               |
| ----------------------- | ---------------------------- | -------------------------------------------- |
| No candidates found     | Document has no standard TOC | Check debug screenshots, adjust keywords     |
| All candidates rejected | Poor pattern detection       | Review detection summary, tune patterns      |
| LLM failures            | API/rate limit issues        | Check verification JSONs, adjust backoff     |
| Empty entries extracted | LLM parsing issues           | Review vision_prompt, check PDF crop quality |

## Dependencies

### Core Dependencies

- **luigi_components**: `structured_task`, `pdf_llm_processor`
- **llm**: LLM client with Claude API support
- **PyMuPDF (fitz)**: PDF processing, text extraction, screenshots

### API Requirements

- **Claude API Key**: Set `ANTHROPIC_API_KEY` environment variable
- **Rate Limits**: Respects Claude's rate limits with automatic backoff

## Performance Considerations

### Token Usage

- **Average**: 1,000-3,000 tokens per candidate
- **Circuit Breaker**: Prevents runaway costs
- **Model Choice**: Haiku (fast/cheap) vs Sonnet (slower/better)

### Processing Time

- **Pattern Detection**: <1 second for most documents
- **LLM Verification**: 2-5 seconds per candidate
- **Total**: Usually 10-30 seconds for typical documents

### Scaling

- **Sequential Processing**: Avoids rate limits, more reliable
- **Concurrent Option**: Available but not recommended for production

## Future Improvements (TODOs)

1. **TOCFallbackLLMStrategy**: Currently pass-through, implement semantic fallback
2. **Built-in TOC Check**: Use `doc.get_toc()` before pattern detection
3. **Multi-page TOC**: Better handling of TOCs spanning multiple pages
4. **Confidence Scoring**: More sophisticated candidate ranking
5. **Custom Domains**: Domain-specific pattern tuning (legal, medical, etc.)
