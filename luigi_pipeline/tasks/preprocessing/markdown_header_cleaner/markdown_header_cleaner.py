import luigi
import json
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from llm import LLMClient, LLMConfig
from luigi_pipeline.config import load_config
from luigi_pipeline.tasks.base.structured_task import StructuredTask
from luigi_pipeline.tasks.preprocessing.llm_markdown_processor.llm_markdown_processor import LLMMarkdownProcessor


class MarkdownHeaderCleaner(StructuredTask):
    """
    AI-powered header/footer removal from markdown pages
    """
    file_path = luigi.Parameter()
    preset = luigi.Parameter(default="default")
    
    @property
    def pipeline_name(self) -> str:
        return "preprocessing"
    
    @property
    def task_name(self) -> str:
        return "markdown_header_cleaner"
    
    def requires(self):
        return LLMMarkdownProcessor(file_path=self.file_path, preset=self.preset)
    
    def run(self):
        print("🤖 Starting AI-powered markdown header cleaning...")
        
        # Load LLM markdown results
        with self.input().open('r') as f:
            llm_data = json.load(f)
        
        if llm_data.get("task_name") != "LLMMarkdownProcessor":
            raise ValueError("Expected LLMMarkdownProcessor input data")
        
        # Extract successful markdown pages
        success_results = [r for r in llm_data.get("batch_results", []) if r.get("status") == "success"]
        
        if len(success_results) < 2:
            print("⚠️ Less than 2 successful pages, skipping AI cleaning")
            self._output_unchanged(llm_data)
            return
        
        print(f"🤖 AI analyzing {len(success_results)} markdown pages...")
        
        # AI-powered detection
        headers_to_remove = self._ai_detect_headers(success_results)
        
        if not headers_to_remove:
            print("✅ AI found no headers to remove")
            self._output_unchanged(llm_data)
            return
        
        print(f"🎯 AI found {len(headers_to_remove)} fragments to remove")
        
        # Remove AI-detected headers
        cleaned_results = self._remove_ai_headers(success_results, headers_to_remove)
        
        # Output with AI metadata
        self._output_ai_cleaned_results(llm_data, cleaned_results, headers_to_remove)
        
        print(f"✅ AI header cleaning complete!")
    
    def _ai_detect_headers(self, results: List[Dict]) -> List[str]:
        """Use AI to detect headers/footers to remove"""
        # Load AI config
        config = load_config()
        model = config.get_task_setting("AIHeaderDetector", "model", "gpt-4.1-mini")
        max_tokens = config.get_max_tokens_for_model(model)
        temperature = config.get_task_setting("AIHeaderDetector", "temperature", 0.0)
        
        # Setup AI client
        llm_client = LLMClient(model)
        llm_config = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        
        # Sample max 5 pages for AI analysis
        sample_pages = [r["markdown_content"] for r in results[:5]]
        
        try:
            prompt = self._build_ai_prompt(sample_pages)
            response = llm_client.chat(prompt, llm_config)
            headers_array = self._parse_ai_response(response)
            
            # Verify headers exist in actual pages
            verified_headers = self._verify_headers_exist(headers_array, results)
            
            return verified_headers
            
        except Exception as e:
            print(f"❌ AI detection failed: {e}")
            return []
    
    def _build_ai_prompt(self, sample_pages: List[str]) -> str:
        """Build AI detection prompt"""
        pages_text = ""
        for i, page in enumerate(sample_pages, 1):
            pages_text += f"\n=== STRONA {i} ===\n{page}\n"
        
        prompt = f"""Analizujesz strony dokumentu PDF po konwersji na markdown.

ZADANIE: Znajdź DOKŁADNE fragmenty tekstu które się POWTARZAJĄ i są NAGŁÓWKAMI/STOPKAMI do usunięcia.

STRONY:
{pages_text}

USUŃ TYLKO:
✅ Numery stron: "Strona 1", "Page 15"
✅ Dane kontaktowe w stopkach: "Tel: 123", "email@firma.pl"  
✅ Metadane: "Wersja 1.2", "Data: 2024-01-15"
✅ Formularze: "Dokument nr XYZ"

ZACHOWAJ:
❌ Struktury: "## Artykuł 1", "### Rozdział 2" 
❌ Listy: "1. Punkt", "a) Pozycja"
❌ Treść merytoryczną

ZWRÓĆ TABLICĘ DOKŁADNYCH TEKSTÓW:
[
  "dokładny fragment 1",
  "dokładny fragment 2"
]

TYLKO JSON TABLICA!"""
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> List[str]:
        """Parse AI JSON response"""
        try:
            clean_response = response.strip()
            
            # Handle code blocks
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                parts = clean_response.split('```')
                if len(parts) >= 3:
                    clean_response = parts[1]
            
            # Parse JSON
            headers_array = json.loads(clean_response.strip())
            
            if not isinstance(headers_array, list):
                return []
            
            # Filter valid strings
            valid_headers = []
            for item in headers_array:
                if isinstance(item, str) and len(item.strip()) >= 5:
                    valid_headers.append(item.strip())
            
            return valid_headers
            
        except Exception as e:
            print(f"❌ Failed to parse AI response: {e}")
            return []
    
    def _verify_headers_exist(self, headers_array: List[str], results: List[Dict]) -> List[str]:
        """Verify AI headers actually exist in pages"""
        verified = []
        all_pages = [r["markdown_content"] for r in results]
        
        for header in headers_array:
            count = sum(1 for page in all_pages if header in page)
            if count >= 2:  # Must appear in 2+ pages
                verified.append(header)
                print(f"   ✅ '{header[:50]}...' (found in {count} pages)")
            else:
                print(f"   ❌ '{header[:50]}...' (only {count} pages)")
        
        return verified
    
    def _remove_ai_headers(self, results: List[Dict], headers: List[str]) -> List[Dict]:
        """Remove AI-detected headers from markdown"""
        cleaned_results = []
        
        for result in results:
            original_content = result["markdown_content"]
            cleaned_content = original_content
            removed_count = 0
            
            # Remove each header
            for header in headers:
                if header in cleaned_content:
                    cleaned_content = cleaned_content.replace(header, '')
                    removed_count += 1
            
            # Clean whitespace
            cleaned_content = self._cleanup_whitespace(cleaned_content)
            
            # Create cleaned result
            cleaned_result = result.copy()
            cleaned_result.update({
                "markdown_content": cleaned_content,
                "original_length": len(original_content),
                "cleaned_length": len(cleaned_content),
                "bytes_removed": len(original_content) - len(cleaned_content),
                "headers_removed_count": removed_count,
                "ai_cleaned": True
            })
            
            cleaned_results.append(cleaned_result)
        
        return cleaned_results
    
    def _cleanup_whitespace(self, content: str) -> str:
        """Clean excessive whitespace"""
        # Remove multiple newlines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Remove trailing whitespace
        lines = [line.rstrip() for line in content.split('\n')]
        
        # Remove empty lines at start/end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        return '\n'.join(lines).strip()
    
    def _output_unchanged(self, original_data: Dict):
        """Output when no cleaning applied"""
        output_data = original_data.copy()
        output_data.update({
            "task_name": "MarkdownHeaderCleaner",
            "ai_cleaning_applied": False,
            "headers_removed": 0,
            "cleaning_timestamp": datetime.now().isoformat()
        })
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def _output_ai_cleaned_results(self, original_data: Dict, cleaned_results: List[Dict], headers: List[str]):
        """Output AI-cleaned results"""
        # Statistics
        total_bytes_removed = sum(r.get("bytes_removed", 0) for r in cleaned_results)
        pages_cleaned = sum(1 for r in cleaned_results if r.get("bytes_removed", 0) > 0)
        
        # Update batch results
        updated_batch_results = []
        cleaned_index = 0
        
        for result in original_data.get("batch_results", []):
            if result.get("status") == "success":
                updated_batch_results.append(cleaned_results[cleaned_index])
                cleaned_index += 1
            else:
                updated_batch_results.append(result)
        
        # Create output
        output_data = original_data.copy()
        output_data.update({
            "task_name": "MarkdownHeaderCleaner",
            "batch_results": updated_batch_results,
            "ai_cleaning_applied": True,
            "ai_statistics": {
                "headers_detected": len(headers),
                "pages_cleaned": pages_cleaned,
                "total_pages": len(cleaned_results),
                "total_bytes_removed": total_bytes_removed,
                "cleaning_efficiency": total_bytes_removed / sum(r.get("original_length", 1) for r in cleaned_results)
            },
            "detected_headers": [h[:100] + "..." if len(h) > 100 else h for h in headers[:10]],
            "cleaning_timestamp": datetime.now().isoformat()
        })
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"📊 AI CLEANING STATS:")
        print(f"   🤖 {len(headers)} headers detected by AI")
        print(f"   🧹 {pages_cleaned}/{len(cleaned_results)} pages cleaned")
        print(f"   📉 {total_bytes_removed:,} bytes removed")
        print(f"   ⚡ {output_data['ai_statistics']['cleaning_efficiency']:.1%} efficiency")