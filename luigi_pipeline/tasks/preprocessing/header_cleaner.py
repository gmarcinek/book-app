# PLIK: luigi_pipeline/tasks/conditional_processor.py
import luigi
import hashlib
import json
from pathlib import Path
from luigi_pipeline.tasks.preprocessing.pdf_processing import PDFProcessing

class HeaderCleaner(luigi.Task):
    file_path = luigi.Parameter()

    def requires(self):
        return PDFProcessing(file_path=self.file_path)

    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/header_cleaned_{file_hash}.json")

    def run(self):
        with self.input().open('r') as f:
            data = json.load(f)

        pages = data["pages"]
        min_prefix_len = 20
        max_probe_len = 500
        ref_text = pages[0]["extracted_text"][:max_probe_len]

        found = False
        start = 0
        matches = []

        while start + min_prefix_len <= len(ref_text):
            prefix = ref_text[start:start + min_prefix_len]
            print(f"🔍 Próba prefixu (offset {start}): '{prefix}'")
            if not prefix or len(prefix) < min_prefix_len:
                break
            new_matches = [p["extracted_text"].find(prefix) for p in pages]
            print(f"📎 Pozycje dopasowania: {new_matches}")
            for idx, (p, m) in enumerate(zip(pages, new_matches)):
                actual = p['extracted_text'][m:m+len(prefix)] if m >= 0 else ''
                print(f"📐 Strona {idx}: '{actual}' == '{prefix}' → {actual == prefix}")
            if all(i >= 0 for i in new_matches):
                matches = new_matches
                found = True
                break
            start += 1

        if not found:
            data["header_cleaning"] = {"detected": False}
            with open(self.output().path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return

        chunk_len = min_prefix_len
        max_chunk_len = len(ref_text) - start

        # Rozszerzaj chunk znak po znaku przy zachowaniu offsetów
        while chunk_len < max_chunk_len:
            next_try = ref_text[start:start + chunk_len + 1]
            if all(p["extracted_text"].find(next_try, m) == m for p, m in zip(pages, matches)):
                chunk_len += 1
                print(f"➕ Rozszerzono do {chunk_len} znaków")
            else:
                print(f"❌ Rozszerzenie do {chunk_len + 1} nie powiodło się")
                break

        # Binarna optymalizacja
        low, high = chunk_len, max_chunk_len
        while low <= high:
            mid = (low + high) // 2
            trial = ref_text[start:start + mid]
            if all(p["extracted_text"].find(trial, m) == m for p, m in zip(pages, matches)):
                chunk_len = mid
                low = mid + 1
            else:
                high = mid - 1

        final_chunk = ref_text[start:start + chunk_len]
        print(f"✅ Ostateczny usuwany chunk: '{final_chunk}' (offset: {start}, length: {chunk_len})")

        for idx, page in enumerate(pages):
            m = matches[idx]
            if m >= 0:
                page["extracted_text"] = page["extracted_text"][:m] + page["extracted_text"][m + chunk_len:]
                page["header_removed"] = True

        data["header_cleaning"] = {
            "detected": True,
            "chunk": final_chunk,
            "start_offset": start,
            "length": chunk_len,
            "matched_offsets": matches
        }

        with open(self.output().path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
