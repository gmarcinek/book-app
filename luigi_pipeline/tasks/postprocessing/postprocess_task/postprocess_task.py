import luigi
import json
import subprocess
import time
import os
from datetime import datetime
from pathlib import Path

from luigi_components.structured_task import StructuredTask
from luigi_pipeline.tasks.preprocessing.batch_result_combiner.batch_result_combiner import BatchResultCombiner


class PostprocessTask(StructuredTask):
    """
    Postprocessing: combine markdown from preprocessing + run NER pipeline
    """
    file_path = luigi.Parameter()
    
    @property
    def pipeline_name(self) -> str:
        return "postprocessing"
    
    @property
    def task_name(self) -> str:
        return "postprocess_task"
    
    def requires(self):
        return BatchResultCombiner(file_path=self.file_path)
    
    def run(self):
        # Load preprocessing results
        with self.input().open('r') as f:
            preprocessing_data = json.load(f)
        
        # Create task-specific directory
        task_dir = Path("output") / self.pipeline_name / self.task_name
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract and combine markdown
        combined_markdown = self._extract_and_combine_markdown(preprocessing_data)
        
        # Save combined markdown file in task directory
        markdown_file = self._save_combined_markdown(combined_markdown, task_dir)
        
        # Wait for file system
        time.sleep(0.5)
        
        # Run NER pipeline
        ner_results = self._run_ner_pipeline(markdown_file)
        
        # Create output
        result = {
            "task_name": "PostprocessTask",
            "input_file": str(self.file_path),
            "markdown_file_created": str(markdown_file),
            "ner_command_executed": True,
            "ner_results": ner_results,
            "created_at": datetime.now().isoformat()
        }
        
        with self.output().open('w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Postprocessing complete: {markdown_file.name}")
        print(f"✅ NER pipeline executed")
    
    def _extract_and_combine_markdown(self, preprocessing_data):
        """Extract markdown content from BatchResultCombiner output"""
        # ZMIENIONE: Bezpośrednio z BatchResultCombiner
        combined_result = preprocessing_data.get("combined_result", {})
        success_results = combined_result.get("success_results", [])
        
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
    
    def _save_combined_markdown(self, content, task_dir):
        """Save combined markdown to task directory"""
        # Create filename
        source_name = Path(self.file_path).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_postprocess_{timestamp}.md"
        
        # Save file in task directory
        markdown_file = task_dir / filename
        markdown_file.write_text(content, encoding='utf-8')
        
        print(f"📝 Combined markdown saved: {filename}")
        return markdown_file
    
    def _run_ner_pipeline(self, markdown_file):
        """Run NER pipeline on combined markdown"""
        try:
            cmd = [
                "poetry", "run", "app", 
                str(markdown_file),
                "-m", "claude-4-sonnet",
                # "-m", "gpt-4.1-nano",
                "--domains", "literary"
            ]
            
            print(f"🚀 Running NER: {' '.join(cmd)}")
            
            # Set UTF-8 encoding for Windows
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
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