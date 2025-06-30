import luigi
import json
import hashlib
from datetime import datetime
from pathlib import Path


class MarkdownCombiner(luigi.Task):
    """
    Combines multiple LLMMarkdownProcessor outputs into single Markdown files
    """
    llm_files_pattern = luigi.Parameter()  # e.g., "output/llm_markdown_*.json"
    
    def output(self):
        pattern_hash = hashlib.md5(str(self.llm_files_pattern).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/markdown_combiner_{pattern_hash}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Find all matching LLM files
        from glob import glob
        llm_files = glob(str(self.llm_files_pattern))
        
        if not llm_files:
            raise ValueError(f"No LLM files found matching: {self.llm_files_pattern}")
        
        print(f"🔗 Combining {len(llm_files)} LLM markdown files...")
        
        results = []
        for llm_file in sorted(llm_files):
            result = self._process_single_llm_file(llm_file)
            results.append(result)
        
        output_data = {
            "task_name": "MarkdownCombiner",
            "input_pattern": self.llm_files_pattern,
            "files_processed": len(llm_files),
            "results": results,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    def _process_single_llm_file(self, llm_file_path):
        """Process single LLM markdown file and create combined output"""
        print(f"📄 Processing: {llm_file_path}")
        
        # Load LLM data
        with open(llm_file_path, 'r', encoding='utf-8') as f:
            llm_data = json.load(f)
        
        # Extract document info
        source_file = llm_data.get("input_file", "unknown")
        doc_name = Path(source_file).stem
        model_used = llm_data.get("model_used", "unknown")
        pages_count = llm_data.get("pages_count", 0)
        pages_with_tables = llm_data.get("pages_with_tables", 0)
        
        # Build clean combined markdown
        markdown_content = self._build_combined_markdown(llm_data)
        
        # Save combined markdown file
        markdown_file_path = self._save_combined_markdown(markdown_content, doc_name, llm_file_path)
        
        print(f"✅ Combined: {doc_name} ({pages_count} pages) → {markdown_file_path}")
        
        return {
            "llm_file": llm_file_path,
            "source_document": source_file,
            "document_name": doc_name,
            "combined_markdown_file": str(markdown_file_path) if markdown_file_path else None,
            "pages_count": pages_count,
            "pages_with_tables": pages_with_tables,
            "model_used": model_used,
            "status": "success"
        }
    
    def _build_combined_markdown(self, llm_data):
        """Build combined markdown from all pages - CLEAN CONTENT ONLY"""
        
        # Combine all pages without any metadata or page headers
        content_parts = []
        
        for page_data in llm_data.get("markdown_pages", []):
            page_markdown = page_data.get("markdown", "")
            
            # Fix escaped newlines
            if '\\n' in page_markdown:
                page_markdown = page_markdown.replace('\\n', '\n')
            
            # Skip error pages or add clean content only
            if "error" in page_data:
                continue  # Skip error pages completely
            
            # Add clean content without any page headers
            if page_markdown.strip():
                content_parts.append(page_markdown.strip())
        
        # Join with simple separator
        return "\n\n---\n\n".join(content_parts)
    
    def _save_combined_markdown(self, markdown_content, doc_name, llm_file_path):
        """Save combined markdown to file - CLEAN CONTENT ONLY"""
        try:
            # Create output filename
            llm_file_base = Path(llm_file_path).stem  # "llm_markdown_5281a67c"
            hash_part = llm_file_base.split('_')[-1]  # "5281a67c"
            
            output_filename = f"{doc_name}_COMBINED_{hash_part}.md"
            output_path = Path("output") / output_filename
            
            # Save clean content only
            output_path.write_text(markdown_content, encoding='utf-8')
            
            print(f"📝 Saved: {output_filename}")
            return output_path
            
        except Exception as e:
            print(f"⚠️ Failed to save markdown for {doc_name}: {e}")
            return None


class MarkdownCombinerSingle(luigi.Task):
    """
    Combines pages from ONE specific LLMMarkdownProcessor output - CLEAN CONTENT ONLY
    """
    llm_markdown_file = luigi.Parameter()  # "output/llm_markdown_5281a67c.json"
    
    def output(self):
        input_path = Path(self.llm_markdown_file)
        base_name = input_path.stem
        return luigi.LocalTarget(f"output/combined_single_{base_name}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Use same logic but for single file
        combiner = MarkdownCombiner(llm_files_pattern="dummy")  # Pattern not used for single file
        result = combiner._process_single_llm_file(self.llm_markdown_file)
        
        output_data = {
            "task_name": "MarkdownCombinerSingle",
            "input_file": self.llm_markdown_file,
            "result": result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)