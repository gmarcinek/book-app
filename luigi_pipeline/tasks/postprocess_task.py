import luigi
import json
import hashlib
import subprocess
import time
import os  # ← ADD THIS IMPORT
from datetime import datetime
from pathlib import Path

from .preprocessing_task import PreprocessingTask


class PostprocessTask(luigi.Task):
    """
    Postprocessing: combine markdown from JSON + run NER pipeline
    """
    file_path = luigi.Parameter()
    
    def requires(self):
        return PreprocessingTask(file_path=self.file_path)
    
    def output(self):
        file_hash = hashlib.md5(str(self.file_path).encode()).hexdigest()[:8]
        return luigi.LocalTarget(f"output/postprocess_{file_hash}.json")
    
    def run(self):
        # Load preprocessing results
        with self.input().open('r') as f:
            preprocessing_data = json.load(f)
        
        # Extract batch results and combine markdown
        combined_markdown = self._extract_and_combine_markdown(preprocessing_data)
        
        # Save combined markdown file
        markdown_file = self._save_combined_markdown(combined_markdown)
        
        # Wait 0.5 sec for file system
        time.sleep(0.5)
        
        # Run NER pipeline
        ner_results = self._run_ner_pipeline(markdown_file)
        
        # Create output
        output = {
            "task_name": "PostprocessTask",
            "input_file": str(self.file_path),
            "markdown_file_created": str(markdown_file),
            "ner_command_executed": True,
            "ner_results": ner_results,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✅ Postprocessing complete: {markdown_file.name}")
        print(f"✅ NER pipeline executed")
    
    def _extract_and_combine_markdown(self, preprocessing_data):
        """Extract markdown content from preprocessing JSON and combine"""
        # Navigate nested structure: combined_result.combined_result
        combined_result = preprocessing_data.get("combined_result", {})
        inner_combined_result = combined_result.get("combined_result", {})
        
        # Get success_results from inner structure
        success_results = inner_combined_result.get("success_results", [])
        
        if not success_results:
            raise ValueError(f"No successful pages found in preprocessing data")
        
        print(f"📝 Combining {len(success_results)} successful pages")
        
        # Sort by page number and combine
        sorted_pages = sorted(success_results, key=lambda x: x.get("page_num", 0))
        
        combined_parts = []
        for page_result in sorted_pages:
            content = page_result.get("markdown_content", "")
            if content.strip():
                combined_parts.append(content.strip())
        
        return "\n\n".join(combined_parts) + "\n"
    
    def _save_combined_markdown(self, content):
        """Save combined markdown to file"""
        # Create filename
        source_name = Path(self.file_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_postprocess_{timestamp}.md"
        
        # Save file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        markdown_file = output_dir / filename
        
        markdown_file.write_text(content, encoding='utf-8')
        print(f"📝 Combined markdown saved: {filename}")
        
        return markdown_file
    
    def _run_ner_pipeline(self, markdown_file):
        """Run NER pipeline on combined markdown"""
        try:
            cmd = [
                "poetry", "run", "app", 
                str(markdown_file),
                "-m", "gpt-4.1-nano",
                "-d", "owu"
            ]
            
            print(f"🚀 Running NER: {' '.join(cmd)}")
            
            # Set UTF-8 encoding for Windows
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',  # ← EXPLICIT ENCODING
                errors='replace',  # ← HANDLE BAD CHARS
                cwd=Path.cwd(),
                timeout=600,
                env=env
            )
            
            return {
                "command": ' '.join(cmd),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "command": ' '.join(cmd),
                "error": "NER pipeline timeout (10 minutes)",
                "success": False
            }
        except Exception as e:
            return {
                "command": ' '.join(cmd),
                "error": str(e),
                "success": False
            }