# Book Agent - NER Knowledge Graph Builder

Automatyczne budowanie grafów wiedzy z dokumentów przy użyciu Named Entity Recognition (NER) z wieloma domenami i modelami LLM.

## 🚀 Szybki start

```bash
# Pojedynczy plik
poetry run app document.pdf

# Folder z dokumentami  
poetry run app folder/ --batch

# Z wybranym modelem
poetry run app text.txt --model claude-4-sonnet

```

## 📋 Dostępne modele

| Model               | Provider  | Context/Output | NER Quality | Cost | Opis |
|---------------------|-----------|----------------|-------------|------|------|
| `gpt-4o-mini`      | OpenAI    | 128K/16K      | ⭐⭐⭐       | $$   | **Default** - dobry balans |
| `gpt-4.1-mini`     | OpenAI    | 1M/32K        | ⭐⭐⭐       | $$   | Duży context window |
| `gpt-4.1-nano`     | OpenAI    | 1M/32K        | ⭐⭐⭐       | $   | Duży context window |
| `gpt-4o`           | OpenAI    | 128K/16K      | ⭐⭐⭐⭐     | $$$  | Wysoka jakość |
| `claude-4-sonnet`  | Anthropic | 200K/64K      | ⭐⭐⭐⭐⭐   | $$$  | **Najlepszy do kodowania** |
| `claude-4-opus`    | Anthropic | 200K/32K      | ⭐⭐⭐⭐⭐   | $$$$$ | **Najinteligentniejszy** |
| `claude-3.5-sonnet`| Anthropic | 200K/8K       | ⭐⭐⭐⭐     | $$$  | Szybki i niezawodny |
| `claude-3.5-haiku` | Anthropic | 200K/8K       | ⭐⭐⭐⭐     | $    | **Najlepszy do NER** |
| `claude-3-haiku`   | Anthropic | 200K/8K       | ⭐⭐⭐       | $    | Najtańszy Claude |
| `qwen2.5-coder`    | Ollama    | 32K/32K       | ⭐⭐         | Free | Lokalny, szybki |
| `qwen2.5-coder:32b`| Ollama    | 32K/32K       | ⭐⭐⭐       | Free | Większy, lepsza jakość |
| `codestral`        | Ollama    | 32K/32K       | ⭐⭐         | Free | Alternatywa lokalna |

### Rekomendacje

**📊 NER/Entity Extraction:**
- **Najlepszy stosunek jakości do ceny**: `claude-3.5-haiku`
- **Lokalnie/za darmo**: `qwen2.5-coder:32b`
- **Premium**: `claude-4-sonnet`

**💻 Duże dokumenty:**
- **Gigantyczne pliki**: `gpt-4.1-mini` (1M context)
- **Średnie/duże**: `claude-4-sonnet` (200K context)

## 🗂️ Domeny NER

- **`auto`** - automatyczna klasyfikacja domeny *(default)*
- **`literary`** - proza, narracja, dialogi, wspomnienia, autobiografia
- **`simple`** - podstawowe encje (osoby, miejsca, obiekty, wydarzenia)

## ⚙️ Dostępne flagi

### Podstawowe
```bash
--model, -m MODEL          # Model LLM (default: gpt-4o-mini)
--entities-dir, -e DIR      # Katalog na encje (default: entities)
--domains, -d DOMAIN...     # Domeny NER (default: auto)
```

### Przetwarzanie
```bash
--batch                     # Tryb wsadowy dla folderów
--pattern PATTERN          # Wzorzec plików (default: *)
```

### Output
```bash
--quiet, -q                # Minimalne logi
--verbose, -v              # Szczegółowe logi  
--json                     # Output w JSON
```

## 🧠 Inteligentny chunking

System automatycznie dostosowuje rozmiar fragmentów do możliwości modelu:

| Model | Input Limit | Chunk Size* | Opis |
|-------|-------------|-------------|------|
| GPT-4.1-mini | 1M | ~748K | Gigantyczne dokumenty |
| Claude 4 | 200K | ~149K | Duże dokumenty |
| GPT-4o | 128K | ~95K | Średnie dokumenty |
| Ollama | 32K | ~23K | Małe fragmenty |

*Po odjęciu overhead meta-promptów i buffer 25%

## 📊 Przykłady użycia

### Pojedyncze pliki
```bash
# Analiza książki z najlepszym modelem
poetry run app ksiazka.pdf --model claude-4-sonnet --domains literary

# Szybka analiza lokalnie
poetry run app dokument.txt --model qwen2.5-coder --quiet

# Gigantyczny plik z dużym kontekstem
poetry run app huge_book.txt --model gpt-4.1-mini
```

### Przetwarzanie wsadowe
```bash
# Folder z automatyczną klasyfikacją
poetry run app wiersze/ --batch --domains auto

# Tylko PDFy z szczegółowymi logami  
poetry run app library/ --batch --pattern "*.pdf" --verbose

# Wszystkie teksty z konkretną domeną
poetry run app texts/ --batch --pattern "*.txt" --domains simple
```

## 📄 Obsługiwane formaty

| Format | Extension | Opis | Uwagi |
|--------|-----------|------|-------|
| Plain Text | `.txt` | Zwykłe pliki tekstowe | UTF-8 preferowane |
| Markdown | `.md` | Dokumenty Markdown | Pełne wsparcie składni |
| PDF | `.pdf` | Dokumenty PDF | Tylko ekstrakcja tekstu |
| Word | `.docx` | Microsoft Word | Nowoczesny format |
| RTF | `.rtf` | Rich Text Format | Wieloplatformowy |

## 🔧 Struktura output

```
entities/YYYYMMDD-HHMM/
├── ent.123456789.abc123.json     # Pliki encji
├── ent.123456790.def456.json
├── knowledge_graph_book_*.json   # Graf wiedzy
└── log/                          # Logi promptów (debug)
    ├── meta_prompt_chunk0_*.txt
    └── extraction_response_*.txt
```

### Przykład pliku encji

```json
{
  "id": "ent.1234567890123456.abcd1234",
  "name": "Warszawa",
  "type": "MIEJSCE", 
  "description": "Stolica Polski, główne miasto kraju",
  "confidence": 0.95,
  "aliases": ["stolica", "WWA", "miasto"],
  "source_info": {
    "chunk_references": ["chunk_0"],
    "source_document": "document.pdf"
  },
  "metadata": {
    "created": "2025-01-15T14:30:22",
    "model_used": "claude-4-sonnet",
    "extraction_method": "llm",
    "domain_used": "literary"
  }
}
```

## 🎯 Model-aware processing

System automatycznie:
- ✅ Wykrywa limity INPUT/OUTPUT modelu
- ✅ Oblicza rzeczywisty overhead meta-promptów z domen
- ✅ Dostosowuje rozmiar chunków do możliwości modelu  
- ✅ Używa optymalnych temperatur (0.0) dla każdej fazy
- ✅ Deduplikuje encje z zachowaniem aliases

## 🚨 Różnice od starej wersji

**USUNIĘTE funkcje:**
- ❌ `--no-relationships` (relacje nie są już implementowane)
- ❌ `--resolve` (konflikt resolution jest placeholder)
- ❌ `--max-size` (automatyczne zarządzanie pamięcią)
- ❌ `--output` (automatyczne nazwy plików)
- ❌ `--config` (używa wbudowanego NERConfig)

**NOWE funkcje:**
- ✅ `--domains` - wybór strategii NER
- ✅ Model-aware chunking
- ✅ Auto-classification (`--domains auto`)
- ✅ Real-time overhead calculation
- ✅ Enhanced logging z model stats

## 🔧 Rozwiązywanie problemów

### Błędy LLM
```bash
# Sprawdź czy zmienne środowiskowe są ustawione
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

# Użyj lokalnego modelu
poetry run app file.txt --model qwen2.5-coder
```

### Problemy z pamięcią
```bash
# Użyj mniejszego modelu
poetry run app large.pdf --model claude-3.5-haiku

# Lokalny model z mniejszymi chunkami
poetry run app huge.txt --model qwen2.5-coder
```

### Model Ollama niedostępny
```bash
# Uruchom Ollama
ollama serve

# Pobierz model
ollama pull qwen2.5-coder

# Sprawdź dostępne modele
ollama list
```

## 📞 Pomoc

```bash
# Wszystkie opcje
poetry run app --help

# Test z prostym plikiem
echo "Jan Kowalski mieszka w Warszawie." > test.txt
poetry run app test.txt --verbose
```