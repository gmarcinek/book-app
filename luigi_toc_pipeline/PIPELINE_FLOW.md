# Luigi TOC Pipeline - Dokumentacja Flow

## Przegląd

Pipeline `luigi_toc_pipeline` służy do automatycznej detekcji i ekstrakcji spisu treści (Table of Contents) z dokumentów PDF. Pipeline wykorzystuje podejście hybrydowe łączące heurystyki wzorcowe z weryfikacją LLM.

## Architektura Pipeline'u

Pipeline składa się z 4 głównych modułów Luigi połączonych w łańcuch zależności:

```
run_toc_pipeline.py
    ↓
TOCOrchestrator
    ↓
TOCFallbackLLMStrategy
    ↓
TOCHeuristicDetector
    ↓
    ├── TOCPatternDetector (Stage 1)
    └── TOCVerificationEngine (Stage 2)
```

---

## Moduł 1: `run_toc_pipeline.py` - Punkt Wejścia

**Lokalizacja:** `luigi_toc_pipeline/run_toc_pipeline.py`

### Zadanie
Inicjalizuje pipeline Luigi dla pojedynczego pliku PDF.

### Proces
1. Waliduje argument wiersza poleceń (ścieżka do PDF)
2. Sprawdza czy plik istnieje
3. Uruchamia Luigi scheduler z taskiem `TOCOrchestrator`

### Użycie
```bash
python run_toc_pipeline.py <pdf_file>
```

### Wyjście
- ✅ Sukces: "Pipeline completed successfully" (exit code 0)
- ❌ Błąd: "Pipeline failed" (exit code 1)

---

## Moduł 2: `TOCOrchestrator` - Orkiestrator Główny

**Lokalizacja:** `luigi_toc_pipeline/tasks/toc_orchestrator.py`

### Zadanie
Agreguje wyniki z wcześniejszych etapów i tworzy finalne podsumowanie procesu detekcji TOC.

### Proces
1. Odbiera wyniki z `TOCFallbackLLMStrategy`
2. Jeśli TOC znaleziony (`toc_found: true`):
   - Ekstrahuje strukturalne dane TOC
   - Wydobywa współrzędne (start_page, end_page, start_y, end_y)
   - Przygotowuje listę entries z licznikami
3. Jeśli TOC nie znaleziony:
   - Tworzy raport negatywny z powodem

### Wyjście JSON

**Sukces (TOC znaleziony):**
```json
{
  "task_name": "TOCOrchestrator",
  "input_file": "/path/to/file.pdf",
  "toc_found": true,
  "detection_method": "llm_processing_merged",
  "coordinates": {
    "start_page": 2,
    "end_page": 4,
    "start_y": 150.5,
    "end_y": 780.2
  },
  "toc_entries": [...],
  "toc_entries_count": 25,
  "ready_for_splitting": true,
  "processing_stats": {
    "certain_count": 1,
    "uncertain_count": 0,
    "processed_count": 1,
    "rejected_count": 3
  }
}
```

**Niepowodzenie (brak TOC):**
```json
{
  "task_name": "TOCOrchestrator",
  "input_file": "/path/to/file.pdf",
  "toc_found": false,
  "reason": "no_confirmed_tocs_after_processing",
  "ready_for_splitting": false,
  "processing_stats": {...}
}
```

### Logi konsoli
```
✅ TOC orchestration complete: 25 entries found
   Method: llm_processing_merged
   Coverage: pages 2-4
```

---

## Moduł 3: `TOCFallbackLLMStrategy` - Strategia Fallback

**Lokalizacja:** `luigi_toc_pipeline/tasks/toc_fallback_llm_strategy/toc_fallback_llm_strategy.py`

### Zadanie
Warstwa strategii fallback - w przyszłości ma implementować łańcuch:
1. Built-in TOC (PDF metadata)
2. Heuristic detection (obecne)
3. Semantic fallback (TODO)

### Obecna Implementacja
**Preleotka (pass-through)** - przekazuje wynik z `TOCHeuristicDetector` bez zmian.

### Planowane rozszerzenia (TODO)
```python
# Planowany flow:
1. doc.get_toc() → jeśli found, return
2. TOCHeuristicDetector → jeśli found, return
3. Semantic LLM fallback → jeśli found, return
4. Return toc_found: false
```

### Wyjście
Przekazuje niezmieniony JSON z `TOCHeuristicDetector`, dodaje pole `method`.

---

## Moduł 4: `TOCHeuristicDetector` - Główny Silnik Detekcji

**Lokalizacja:** `luigi_toc_pipeline/tasks/toc_heuristic_detector/toc_heuristic_detector.py`

### Zadanie
Dwuetapowa detekcja TOC:
- **Stage 1:** Heurystyczna detekcja wzorców (TOCPatternDetector)
- **Stage 2:** Weryfikacja LLM (TOCVerificationEngine)

### Proces

#### Krok 1: Inicjalizacja
```python
config = load_config()  # Wczytuje config.yaml
doc = fitz.open(self.file_path)  # PyMuPDF
max_pages = min(config.max_pages_to_scan, len(doc))  # Domyślnie: 1000
```

#### Krok 2: Stage 1 - Pattern Detection
```python
pattern_detector = TOCPatternDetector(doc, max_pages, config)
toc_candidates = pattern_detector.find_all_toc_candidates()
```

**Wynik:** Słownik z 3 kategoriami:
```python
{
  'certain': [...],      # Pewne TOC (high confidence)
  'uncertain': [...],    # Niepewne (do weryfikacji LLM)
  'rejected': [...]      # Odrzucone false positives
}
```

**Logi:**
```
🔍 Found 1 certain TOCs
🔍 Found 2 uncertain TOCs
🔍 Rejected 3 false positives
```

#### Krok 3: Debug Export
```python
debug_utils.save_detection_summary(toc_candidates, self.file_path)
```
Zapisuje debug PDFs do `output/{document_name}/debug/`.

#### Krok 4: Stage 2 - LLM Processing
```python
all_candidates = certain + uncertain
verification_engine = TOCVerificationEngine(pdf_path, config)
processed_tocs = verification_engine.process_all_candidates(all_candidates)
```

**Warunki przerwania:**
- Zbyt wiele kandydatów: `len(all_candidates) > 25`
- Zbyt wiele odrzuceń LLM: `rejected_count >= 4`
- Zbyt wiele błędów LLM: `failure_count >= 3`

**Logi:**
```
🤖 Starting LLM processing for 3 TOC candidates...
   ✅ Processed TOC at page 2
   ❌ Rejected TOC at page 15
🎯 Processed 1/3 TOCs
```

#### Krok 5: Merging Multiple TOCs
```python
final_result = self._merge_all_tocs(processed_tocs)
```

**Co robi:**
- Łączy entries z wszystkich potwierdzonych TOC
- Usuwa duplikaty (po title + page)
- Sortuje po numerze strony
- Oblicza globalne współrzędne (min start_page → max end_page)

**Logi:**
```
🔗 Merging 2 TOC sections...
   TOC at page 2: 15 entries
   TOC at page 5: 12 entries
📋 Merged result: 25 unique entries
   Coverage: pages 2-5
```

### Wyjście JSON

**Sukces:**
```json
{
  "status": "success",
  "toc_found": true,
  "start_page": 2,
  "start_y": 150.5,
  "end_page": 5,
  "end_y": 780.2,
  "confidence": "high",
  "detection_method": "llm_processing_merged",
  "entry_count": 25,
  "toc_entries": [...],
  "merged_sections": 2,
  "certain_count": 1,
  "uncertain_count": 2,
  "processed_count": 2,
  "rejected_count": 1
}
```

**Niepowodzenie:**
```json
{
  "status": "success",
  "toc_found": false,
  "reason": "no_confirmed_tocs_after_processing",
  "certain_count": 0,
  "uncertain_count": 0,
  "processed_count": 0,
  "rejected_count": 5
}
```

---

## Stage 1: `TOCPatternDetector` - Detekcja Wzorców

**Lokalizacja:** `luigi_toc_pipeline/tasks/toc_heuristic_detector/pattern_detector.py`

### Zadanie
Znajdź wszystkie potencjalne TOC używając heurystyk wzorcowych i kategoryzuj według pewności.

### Proces

#### Krok 1: Znajdź TOC Start
```python
for page_num in range(max_pages):
    toc_start = _find_toc_start_on_page(page_num)
```

**Wzorce TOC (z config.yaml):**
```yaml
toc_keywords:
  - "spis treści"
  - "treść"
  - "table of contents"
  - "contents"
  - "indice"
  - "sommaire"
  - "chapter contents"
```

**Regex matching:**
```python
pattern = r'\b{keyword}\b'  # Word boundary matching
```

#### Krok 2: Znajdź TOC End
```python
toc_end = _find_toc_end_from_start(toc_start)
```

**Strategia:**
- Skanuj do 3 stron od startu
- Liczy linie wyglądające jak TOC entries
- Liczy wszystkie linie (total_lines)
- Oblicza `toc_ratio = toc_entries / total_lines`

**Wzorce TOC Entry:**
```python
patterns = [
    r'.+\.{3,}\s*\d+\s*$',           # "Title....... 25"
    r'.+\s{3,}\d+\s*$',              # "Title    25"
    r'.+\t+\d+\s*$',                 # "Title\t\t25"
    r'^\d+\.?\d*\.?\s*.+\s+\d+\s*$', # "1.1 Title 25"
    r'^(chapter|rozdział).*\d+\s*$', # "Chapter 1 ... 25"
    r'.+\s*\(\d+\)\s*$',             # "Title (25)"
]
```

**Koniec TOC wykrywany przez:**
- Content start patterns (np. "Rozdział 1", "Introduction")
- Lub fallback: po 3 stronach lub po ostatnim entry

**Content Start Patterns:**
```python
patterns = [
    r'^(rozdział|rozdzial)\s+\d+',
    r'^(część|czesc)\s+\d+',
    r'^(wprowadzenie|wstęp|wstep)',
    r'^(chapter|part)\s+\d+',
    r'^(introduction|preface)',
    # ... i więcej
]
```

#### Krok 3: Kategoryzacja Kandydatów
```python
return _categorize_candidates(all_candidates)
```

**Kryteria kategoryzacji:**

**CERTAIN (pewne):**
- `proximity_ok = True` (TOC blisko swojego content)
- `page_distance <= 1` (TOC na max 1 stronie)

**UNCERTAIN (niepewne):**
- `proximity_ok = True`
- `page_distance <= 5` (TOC do 5 stron)

**REJECTED (odrzucone):**
- `proximity_ok = False` OR `page_distance > 5`

**Logi kategoryzacji:**
```
🔍 Categorizing 5 candidates...
   Candidate 0: page 2, entries=15, total=18, ratio=0.83, proximity=True
     → CERTAIN
   Candidate 1: page 15, entries=5, total=20, ratio=0.25, proximity=True
     → UNCERTAIN
   Candidate 2: page 50, entries=2, total=10, ratio=0.20, proximity=False
     → REJECTED: bad_proximity
```

### Wyjście
```python
{
  'certain': [
    {
      'start_page': 2,
      'start_y': 150.5,
      'end_page': 3,
      'end_y': 780.2,
      'entry_count': 15,
      'total_lines': 18,
      'toc_ratio': 0.83,
      'pattern_matched': r'\bspis treści\b',
      'matched_text': 'spis treści',
      'method': 'pattern',
      'candidate_id': 'toc_2_150'
    }
  ],
  'uncertain': [...],
  'rejected': [...]
}
```

---

## Stage 2: `TOCVerificationEngine` - Weryfikacja LLM

**Lokalizacja:** `luigi_toc_pipeline/tasks/toc_heuristic_detector/verification_engine.py`

### Zadanie
Weryfikuj kandydatów TOC używając LLM (GPT-4.1) do ekstrakcji strukturalnych danych.

### Proces

#### Krok 1: Walidacja liczby kandydatów
```python
if len(all_candidates) > 25:
    print("🚨 Too many candidates - aborting")
    return []
```

#### Krok 2: Przetwarzanie każdego kandydata
```python
for candidate in all_candidates:
    is_valid = _verify_single_candidate_with_processor(candidate)
```

**Dla każdego kandydata:**

##### 2a. Utwórz Temp PDF
```python
temp_pdf_path = _create_temp_toc_pdf(candidate)
```

**Cropping strategia:**
- Górny margines: `start_y - 100px` (100px przed TOC)
- Dolny margines: `start_y + 600px` (600px po TOC)
- Pełna szerokość strony
- PDF zapisywany do `output/{doc_name}/debug/toc_verification_{candidate_id}.pdf`

##### 2b. PDFLLMProcessor Config (z config.yaml)
```yaml
verification_processor:
  model: "gpt-4.1"
  clean_text: true
  temperature: 1.0
  reasoning_effort: "low"
  target_width_px: 700
  jpg_quality: 65
  max_concurrent: 1
  rate_limit_backoff: 30.0
```

##### 2c. Vision Prompt (używany przez LLM)

**Pełny prompt z config.yaml:**
```
Analyze the extracted Table of Contents (TOC) section using text and images.
EXTRACTED TEXT:
{text_content}

NOTE: This PDF contains only a fragment (middle or continuation) of the full TOC.
Page numbers refer to the original document.

TASK: Parse all visible TOC entries into a JSON object with a key "entries",
each entry having:

- "title": string — entry title
- "page": integer or null — original page number
- "level": integer — hierarchy level (1 = chapter, 2 = subsection, etc.)
- "type": string — one of "chapter", "section", or "article"

Example:

{
  "entries": [
    {"title": "Rozdział 1 - Wprowadzenie", "page": 15, "level": 1, "type": "chapter"},
    {"title": "1.1 Podstawowe pojęcia", "page": 17, "level": 2, "type": "section"}
  ]
}

RULES:
- Include all visible entries, even if incomplete.
- Use images to verify text accuracy.
- Do not assume missing context; parse only visible data.
- Respond ONLY with valid JSON, no markdown, no explanations.
- Use standard ASCII double quotes and ESCAPE THEM PROPERLY.
- Escape all other special JSON characters as required.
```

##### 2d. Przetwarzanie odpowiedzi LLM
```python
processor = PDFLLMProcessor(processor_config, "TOCVerification")
results = processor.process_pdf(temp_pdf_path, parse_json_with_markdown_blocks)
```

**Filtrowanie entries:**
- ✅ Akceptuj: `entry.level is not None`
- ❌ Odrzuć: `entry.level is None` (brak hierarchii)

**Logi filtrowania:**
```
⚠️ Discarding entry 'Some Random Text' - no level detected
📋 Entry filtering: 15 valid, 2 discarded (NULL level)
📋 PDFLLMProcessor extracted 15 valid entries
```

##### 2e. Circuit Breakers (zabezpieczenia)

**Zbyt wiele odrzuceń:**
```python
if rejected_count >= 4:
    print("🚨 Too many rejections - pattern detection likely failing")
    break
```

**Zbyt wiele błędów:**
```python
if failure_count >= 3:
    print("🚨 Too many PDFLLMProcessor failures - aborting")
    break
```

#### Krok 3: Zapisz entries do candidate
```python
if all_entries:
    candidate['toc_entries'] = all_entries
    candidate['toc_entries_count'] = len(all_entries)
    candidate['confidence'] = 'llm_processed'
    candidate['method'] = 'llm_processing'
    processed_tocs.append(candidate)
```

### Wyjście

**Dla każdego przetworzonego TOC:**
```python
{
  'start_page': 2,
  'start_y': 150.5,
  'end_page': 3,
  'end_y': 780.2,
  'confidence': 'llm_processed',
  'method': 'llm_processing',
  'toc_entries': [
    {
      'title': 'Rozdział 1 - Wprowadzenie',
      'page': 15,
      'level': 1,
      'type': 'chapter'
    },
    {
      'title': '1.1 Podstawowe pojęcia',
      'page': 17,
      'level': 2,
      'type': 'section'
    }
  ],
  'toc_entries_count': 15
}
```

**Lista zwracana:**
```python
processed_tocs = [
  { ... TOC 1 ... },
  { ... TOC 2 ... },
]
```

**Logi końcowe:**
```
🎯 Processed 2/3 TOCs
```

---

## Przykładowy Flow - End-to-End

### Scenariusz: PDF z 2 sekcjami TOC

**Input:**
```bash
python run_toc_pipeline.py documents/book.pdf
```

**Konsola Output:**
```
🚀 Starting TOC pipeline for: book.pdf

🔍 Categorizing 5 candidates...
   Candidate 0: page 2, entries=15, total=18, ratio=0.83, proximity=True
     → CERTAIN
   Candidate 1: page 5, entries=12, total=15, ratio=0.80, proximity=True
     → CERTAIN
   Candidate 2: page 15, entries=3, total=20, ratio=0.15, proximity=True
     → UNCERTAIN
   Candidate 3: page 50, entries=2, total=10, ratio=0.20, proximity=False
     → REJECTED: bad_proximity
   Candidate 4: page 100, entries=1, total=5, ratio=0.20, proximity=False
     → REJECTED: too_far

🔍 Found 2 certain TOCs
🔍 Found 1 uncertain TOCs
🔍 Rejected 2 false positives

🤖 Starting LLM processing for 3 TOC candidates...

📄 Saved verification PDF: toc_verification_toc_2_150.pdf
📋 Entry filtering: 15 valid, 0 discarded (NULL level)
📋 PDFLLMProcessor extracted 15 valid entries
   ✅ Processed TOC at page 2

📄 Saved verification PDF: toc_verification_toc_5_200.pdf
📋 Entry filtering: 12 valid, 1 discarded (NULL level)
📋 PDFLLMProcessor extracted 12 valid entries
   ✅ Processed TOC at page 5

📄 Saved verification PDF: toc_verification_toc_15_300.pdf
⚠️ Discarding entry 'Random Text' - no level detected
⚠️ Discarding entry 'Another Text' - no level detected
⚠️ Discarding entry 'More Text' - no level detected
⚠️ No valid entries after filtering
   ❌ Rejected TOC at page 15

🎯 Processed 2/3 TOCs

🔗 Merging 2 TOC sections...
   TOC at page 2: 15 entries
   TOC at page 5: 12 entries
📋 Merged result: 25 unique entries
   Coverage: pages 2-5

🎯 Selected best TOC: page 2-5

🔄 TOCFallbackLLMStrategy: passing through llm_processing_merged result

✅ TOC orchestration complete: 25 entries found
   Method: llm_processing_merged
   Coverage: pages 2-5

✅ Pipeline completed successfully
```

**Output JSON:**
```json
{
  "task_name": "TOCOrchestrator",
  "input_file": "documents/book.pdf",
  "toc_found": true,
  "detection_method": "llm_processing_merged",
  "coordinates": {
    "start_page": 2,
    "end_page": 5,
    "start_y": 150.5,
    "end_y": 780.2
  },
  "toc_entries": [
    {
      "title": "Rozdział 1 - Wprowadzenie",
      "page": 15,
      "level": 1,
      "type": "chapter"
    },
    {
      "title": "1.1 Podstawowe pojęcia",
      "page": 17,
      "level": 2,
      "type": "section"
    }
    // ... 23 more entries
  ],
  "toc_entries_count": 25,
  "ready_for_splitting": true,
  "processing_stats": {
    "certain_count": 2,
    "uncertain_count": 1,
    "processed_count": 2,
    "rejected_count": 2
  }
}
```

**Debug Files Created:**
```
output/book/debug/
  ├── toc_verification_toc_2_150.pdf
  ├── toc_verification_toc_5_200.pdf
  ├── toc_verification_toc_15_300.pdf
  └── detection_summary.json
```

---

## Spodziewane Efekty

### Sukces (TOC znaleziony)
- ✅ JSON z `toc_found: true`
- ✅ Lista entries z title, page, level, type
- ✅ Współrzędne PDF (do późniejszego croppingu)
- ✅ Statystyki procesowania
- ✅ Debug PDFs w `output/{doc}/debug/`

### Częściowy sukces
- ⚠️ TOC znaleziony ale niektóre entries odrzucone (brak level)
- ⚠️ Wielosekcyjny TOC zmergowany (może zawierać duplikaty)

### Niepowodzenie
- ❌ Brak TOC pattern match
- ❌ Za dużo kandydatów (> 25)
- ❌ Za dużo odrzuceń LLM (>= 4)
- ❌ Za dużo błędów LLM (>= 3)
- ❌ Wszystkie entries odrzucone (NULL level)

### Błędy krytyczne
- 💥 Brak dostępu do API LLM
- 💥 Przekroczony rate limit
- 💥 Nieważny JSON z LLM
- 💥 Brak pliku PDF

---

## Konfiguracja (config.yaml)

### Parametry heurystyczne
```yaml
max_pages_to_scan: 1000      # Max stron do skanowania
min_toc_entries: 3           # Min entries w TOC
toc_keywords: [...]          # Słowa kluczowe TOC start
```

### Parametry LLM
```yaml
model: "gpt-4.1"             # Model OpenAI
temperature: 1.0             # Temperatura (default)
reasoning_effort: "low"      # Poziom reasoning
target_width_px: 700         # Szerokość obrazu
jpg_quality: 65              # Jakość JPEG
max_concurrent: 1            # Równoległe requesty
rate_limit_backoff: 30.0     # Backoff po rate limit
```

### Limity bezpieczeństwa
```yaml
max_candidates: 50           # Nie używane (TODO)
max_rejected_count: 5        # Nie używane (TODO)
```
*Uwaga: Faktyczne limity w kodzie: 25 kandydatów, 4 odrzucenia, 3 błędy*

---

## Pliki Output

### Luigi Output (task results)
```
output/toc_processing/toc_orchestrator/{file_hash}/output.json
output/toc_processing/toc_fallback_llm_strategy/{file_hash}/output.json
output/toc_processing/toc_heuristic_detector/{file_hash}/output.json
```

### Debug Files
```
output/{document_name}/debug/
  ├── toc_verification_toc_{page}_{y}.pdf  # Cropped TOC dla LLM
  └── detection_summary.json                # Podsumowanie detekcji
```

---

## Przykłady Real-World

### Przypadek 1: Prosty TOC (1 sekcja)
```
Input: technical_book.pdf
Pattern match: "Table of Contents" na stronie 3
Heurystyka: 20 entries, toc_ratio=0.95 → CERTAIN
LLM: 20/20 entries valid
Output: toc_found=true, 20 entries, pages 3-4
```

### Przypadek 2: Multi-section TOC
```
Input: large_manual.pdf
Pattern matches:
  - "Contents" na stronie 2 (15 entries)
  - "Contents (continued)" na stronie 5 (12 entries)
Heurystyka: Oba CERTAIN
LLM: 15/15 + 12/13 valid (1 odrzucony)
Merge: 27 unique entries
Output: toc_found=true, 27 entries, pages 2-5
```

### Przypadek 3: False Positives
```
Input: mixed_document.pdf
Pattern matches: 5 kandydatów
Kategoryzacja:
  - 1 CERTAIN (strona 3)
  - 2 UNCERTAIN (strony 15, 50)
  - 2 REJECTED (strony 100, 200)
LLM processing:
  - Strona 3: ✅ 18 entries
  - Strona 15: ❌ wszystkie NULL level
  - Strona 50: ❌ odrzucony (4 rejections)
Output: toc_found=true, 18 entries, page 3
```

### Przypadek 4: Brak TOC
```
Input: article.pdf
Pattern match: Brak
Output: toc_found=false, reason="no_pattern_match"
```

### Przypadek 5: Za dużo kandydatów
```
Input: messy_scanned.pdf
Pattern matches: 50 kandydatów (skanowane "Contents" wszędzie)
Kategoryzacja: 30 CERTAIN, 20 UNCERTAIN
LLM: ABORTED (> 25 kandydatów)
Output: toc_found=false, reason="too_many_candidates"
```

---

## Podsumowanie

Pipeline `luigi_toc_pipeline` to solidny, dwuetapowy system detekcji TOC:

1. **Stage 1 (Heuristic):** Szybka, wzorcowa detekcja + kategoryzacja
2. **Stage 2 (LLM):** Precyzyjna ekstrakcja strukturalna z GPT-4.1

**Mocne strony:**
- ✅ Hybrydowe podejście (speed + accuracy)
- ✅ Multi-section TOC merging
- ✅ Solidne circuit breakers (zabezpieczenia)
- ✅ Debug visibility (PDFs + logs)

**Ograniczenia:**
- ⚠️ Brak built-in TOC extraction (TODO w TOCFallbackLLMStrategy)
- ⚠️ Proximity validation wyłączona (zawsze True)
- ⚠️ Rate limiting może być agresywne (30s backoff)

**Use case:**
Idealny do automatycznej ekstrakcji TOC z PDF przed document splitting/chunking.
