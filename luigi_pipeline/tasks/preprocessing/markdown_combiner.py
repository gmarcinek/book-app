import luigi
import json
import glob
from pathlib import Path
from datetime import datetime


class MarkdownCombiner(luigi.Task):
    """
    Combines pages from ALL LLMMarkdownProcessor outputs into separate clean markdowns
    
    For each llm_markdown_*.json creates one combined document.md
    """
    input_pattern = luigi.Parameter(default="output/llm_markdown_*.json")
    
    def output(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return luigi.LocalTarget(f"output/markdown_combiner_{timestamp}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Find all LLM markdown files
        llm_files = glob.glob(self.input_pattern)
        
        if not llm_files:
            raise ValueError(f"No files found matching: {self.input_pattern}")
        
        print(f"📁 Found {len(llm_files)} LLM markdown files to process")
        
        processed_files = []
        
        for llm_file_path in llm_files:
            try:
                result = self._process_single_llm_file(llm_file_path)
                processed_files.append(result)
                
            except Exception as e:
                print(f"❌ Failed to process {llm_file_path}: {e}")
                processed_files.append({
                    "llm_file": llm_file_path,
                    "status": "error",
                    "error": str(e)
                })
        
        # Create summary output
        successful = len([f for f in processed_files if f.get("status") == "success"])
        failed = len(processed_files) - successful
        
        output_data = {
            "task_name": "MarkdownCombiner",
            "status": "success",
            "input_pattern": self.input_pattern,
            "files_found": len(llm_files),
            "files_successful": successful,
            "files_failed": failed,
            "processed_files": processed_files,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"🎉 Processed {len(llm_files)} files: {successful} success, {failed} failed")
    
    def _process_single_llm_file(self, llm_file_path):
        """Process single LLM markdown JSON into combined markdown"""
        
        # Load LLM markdown data
        with open(llm_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get("task_name") != "LLMMarkdownProcessor":
            raise ValueError(f"Not an LLM markdown file: {llm_file_path}")
        
        # Extract document info
        source_file = data.get("input_file", "unknown")
        doc_name = Path(source_file).stem
        pages_count = data.get("pages_count", 0)
        pages_with_tables = data.get("pages_with_tables", 0)
        model_used = data.get("model_used", "unknown")
        
        print(f"📖 Processing: {doc_name} ({pages_count} pages, {pages_with_tables} tables)")
        
        # Create combined markdown content
        combined_markdown = self._build_combined_markdown(data, doc_name)
        
        # Save combined markdown file
        markdown_file_path = self._save_combined_markdown(combined_markdown, doc_name, llm_file_path)
        
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
    
    def _build_combined_markdown(self, llm_data, doc_name):
        """Build combined markdown from all pages"""
        
        # Document header
        source_file = llm_data.get("input_file", "unknown")
        model_used = llm_data.get("model_used", "unknown")
        pages_count = llm_data.get("pages_count", 0)
        pages_with_tables = llm_data.get("pages_with_tables", 0)
        processing_time = llm_data.get("total_processing_time_seconds", 0)
        
        header_parts = [
            f"# {doc_name}",
            "",
            f"**Source:** {source_file}",
            f"**Model:** {model_used}",
            f"**Pages:** {pages_count}",
            f"**Tables:** {pages_with_tables}",
            f"**Processing Time:** {processing_time/60:.1f} minutes" if processing_time else "**Processing Time:** Unknown",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            ""
        ]
        
        # Combine all pages
        content_parts = ["\n".join(header_parts)]
        
        for page_data in llm_data.get("markdown_pages", []):
            page_num = page_data.get("page_num", "?")
            page_markdown = page_data.get("markdown", "")
            has_tables = page_data.get("has_tables", False)
            processing_time = page_data.get("processing_time_seconds", 0)
            
            # Fix escaped newlines
            if '\\n' in page_markdown:
                page_markdown = page_markdown.replace('\\n', '\n')
            
            # Page header
            page_header = f"## Page {page_num}"
            if has_tables:
                page_header += " 📊"
            if "error" in page_data:
                page_header += " ❌ ERROR"
            if processing_time:
                page_header += f" *({processing_time:.1f}s)*"
            
            # Add page content
            content_parts.extend([
                page_header,
                "",
                page_markdown,
                "",
                "---",
                ""
            ])
        
        return "\n".join(content_parts)
    
    def _save_combined_markdown(self, markdown_content, doc_name, llm_file_path):
        """Save combined markdown to file"""
        try:
            # Create output filename
            llm_file_base = Path(llm_file_path).stem  # "llm_markdown_5281a67c"
            hash_part = llm_file_base.split('_')[-1]  # "5281a67c"
            
            output_filename = f"{doc_name}_COMBINED_{hash_part}.md"
            output_path = Path("output") / output_filename
            
            # Save file
            output_path.write_text(markdown_content, encoding='utf-8')
            
            print(f"📝 Saved: {output_filename}")
            return output_path
            
        except Exception as e:
            print(f"⚠️ Failed to save markdown for {doc_name}: {e}")
            return None


class MarkdownCombinerSingle(luigi.Task):
    """
    Combines pages from ONE specific LLMMarkdownProcessor output
    """
    llm_markdown_file = luigi.Parameter()  # "output/llm_markdown_5281a67c.json"
    
    def output(self):
        input_path = Path(self.llm_markdown_file)
        base_name = input_path.stem
        return luigi.LocalTarget(f"output/combined_single_{base_name}.json", format=luigi.format.UTF8)
    
    def run(self):
        # Use same logic but for single file
        combiner = MarkdownCombiner()
        result = combiner._process_single_llm_file(self.llm_markdown_file)
        
        output_data = {
            "task_name": "MarkdownCombinerSingle",
            "input_file": self.llm_markdown_file,
            "result": result,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)