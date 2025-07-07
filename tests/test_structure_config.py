#!/usr/bin/env python3
"""
Test różnych ustawień config dla structure detection
Uruchom: python tests/test_structure_config.py docs/mandat.pdf
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
import fitz
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import io

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.structure.tasks.semantic_structure_detector import SemanticStructureDetector
from pipeline.structure.tasks.structure_splitter import StructureSplitter
import yaml


class StructureConfigTester:
    """Test structure pipeline z różnymi config ustawieniami + visualizations"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.config_file = Path("pipeline/structure/config.yaml")
        self.base_output = Path("test_output") / "structure_tests"
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    def test_config(self, test_name: str, detector_config: dict, splitter_config: dict):
        """Test single config combination + create visualization"""
        print(f"\n🧪 Testing: {test_name}")
        print("=" * 50)
        
        # Create test output directory
        test_output = self.base_output / test_name
        test_output.mkdir(parents=True, exist_ok=True)
        
        # Backup original config
        original_config = self._backup_config()
        
        try:
            # Update config
            self._update_config(detector_config, splitter_config)
            
            # Run detection
            print("🔍 Running StructureDetector...")
            detector = SemanticStructureDetector(file_path=str(self.pdf_path))
            
            # Manual run (bypass Luigi)
            detector_result = self._run_detector_direct(detector, test_output)
            
            if detector_result:
                # Create visualization PDF with bboxes
                print("📊 Creating visualization...")
                self._create_bbox_visualization(detector_result, test_output, test_name)
                
                # Run splitter
                print("✂️ Running StructureSplitter...")
                splitter_result = self._run_splitter_direct(detector_result, test_output)
                
                # Save test summary
                self._save_test_summary(test_name, detector_config, splitter_config, 
                                      detector_result, splitter_result, test_output)
                
                print(f"✅ Test complete: {len(detector_result.get('large_blocks', []))} blocks → {len(splitter_result.get('sections', []))} sections")
                print(f"📄 Visualization saved: {test_output / f'{test_name}_visualization.pdf'}")
            else:
                print("❌ Detection failed")
        
        finally:
            # Restore original config
            self._restore_config(original_config)
    
    def _create_bbox_visualization(self, detector_result, test_output, test_name):
        """Create PDF with bbox overlays"""
        large_blocks = detector_result.get('large_blocks', [])
        
        if not large_blocks:
            print("⚠️ No blocks to visualize")
            return
        
        # Open source PDF
        doc = fitz.open(self.pdf_path)
        
        # Group blocks by page
        blocks_by_page = {}
        for block in large_blocks:
            page_num = block['page']
            if page_num not in blocks_by_page:
                blocks_by_page[page_num] = []
            blocks_by_page[page_num].append(block)
        
        # Create visualization PDF
        viz_doc = fitz.open()
        
        for page_num in sorted(blocks_by_page.keys()):
            if page_num - 1 >= len(doc):
                continue
                
            page = doc[page_num - 1]
            blocks = blocks_by_page[page_num]
            
            # Create page image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(12, 16))
            
            # Load image
            image = Image.open(io.BytesIO(img_bytes))
            ax.imshow(image)
            
            # Draw bboxes
            colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
            
            for i, block in enumerate(blocks):
                bbox = block['bbox']
                color = colors[i % len(colors)]
                
                # Scale bbox by zoom factor
                x1, y1, x2, y2 = [coord * 2.0 for coord in bbox]
                
                # Draw rectangle
                rect = patches.Rectangle(
                    (x1, y1), x2 - x1, y2 - y1,
                    linewidth=3, edgecolor=color, facecolor='none'
                )
                ax.add_patch(rect)
                
                # Add label
                label_text = f"B{i}\nArea: {block.get('area', 0):.0f}"
                if 'merged_count' in block:
                    label_text += f"\nMerged: {block['merged_count']}"
                
                ax.text(x1, y1 - 10, label_text, 
                       fontsize=8, color=color, weight='bold',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))
            
            # Set title and remove axes
            ax.set_title(f'{test_name.upper()} - Page {page_num} - {len(blocks)} blocks detected', 
                        fontsize=14, weight='bold')
            ax.axis('off')
            
            # Save as temp image
            temp_img = test_output / f"page_{page_num}_viz.png"
            plt.savefig(temp_img, dpi=150, bbox_inches='tight', pad_inches=0.1)
            plt.close()
            
            # Convert to PDF page
            viz_page = viz_doc.new_page(width=page.rect.width, height=page.rect.height + 100)
            
            # Insert image
            img_rect = fitz.Rect(0, 50, page.rect.width, page.rect.height + 50)
            viz_page.insert_image(img_rect, filename=str(temp_img))
            
            # Add text header
            viz_page.insert_text(
                (10, 30), 
                f"{test_name.upper()} - Page {page_num} - {len(blocks)} blocks detected",
                fontsize=12, color=(0, 0, 0)
            )
            
            # Cleanup temp image
            temp_img.unlink()
        
        # Save visualization PDF
        viz_path = test_output / f"{test_name}_visualization.pdf"
        viz_doc.save(str(viz_path))
        viz_doc.close()
        doc.close()
    
    def _run_detector_direct(self, detector, test_output):
        """Run detector without Luigi"""
        try:
            config = detector._load_config()
            large_blocks = detector._extract_large_blocks(config)
            
            result = {
                "task_name": "StructureDetector",
                "input_file": str(self.pdf_path),
                "status": "success",
                "large_blocks": large_blocks,
                "blocks_count": len(large_blocks),
                "config_used": config,
                "created_at": datetime.now().isoformat()
            }
            
            # Save result
            result_file = test_output / "detector_result.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
            
        except Exception as e:
            print(f"❌ Detector failed: {e}")
            return None
    
    def _run_splitter_direct(self, detector_result, test_output):
        """Run splitter without Luigi"""
        try:
            from pipeline.structure.config import get_splitter_config
            
            config = get_splitter_config()
            
            # Create splitter instance
            splitter = StructureSplitter(file_path=str(self.pdf_path))
            
            # Override output to test directory
            sections_dir = test_output / "sections"
            sections_dir.mkdir(exist_ok=True)
            
            # Run splitting logic
            sections = self._run_splitting_logic(detector_result, config, sections_dir)
            
            result = {
                "task_name": "StructureSplitter",
                "input_file": str(self.pdf_path),
                "status": "success",
                "sections_created": len(sections),
                "sections": sections,
                "splitting_method": "test_direct",
                "created_at": datetime.now().isoformat()
            }
            
            # Save result
            result_file = test_output / "splitter_result.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
            
        except Exception as e:
            print(f"❌ Splitter failed: {e}")
            return None
    
    def _run_splitting_logic(self, detector_result, config, sections_dir):
        """Run actual splitting logic"""
        import fitz
        
        large_blocks = detector_result["large_blocks"]
        
        if not large_blocks:
            return []
        
        sections = []
        doc = fitz.open(self.pdf_path)
        
        try:
            for i, block in enumerate(large_blocks):
                page_num = block["page"]
                bbox = block["bbox"]
                
                # Create filename
                filename = f"section_{i:03d}_block_{i}.pdf"
                file_path = sections_dir / filename
                
                # Extract with full width
                success = self._extract_block_pdf_direct(doc, page_num, bbox, file_path)
                
                if success:
                    sections.append({
                        "title": f"block_{i}",
                        "filename": filename,
                        "file_path": str(file_path),
                        "page": page_num,
                        "bbox": bbox,
                        "block_index": i,
                        "block_area": block.get("area", 0)
                    })
        finally:
            doc.close()
        
        return sections
    
    def _extract_block_pdf_direct(self, source_doc, page_num, bbox, output_path):
        """Extract block PDF with full width"""
        try:
            page_idx = page_num - 1
            source_page = source_doc[page_idx]
            page_rect = source_page.rect
            
            # Full width, Y from bbox
            x1, y1, x2, y2 = bbox
            safe_x1 = 0
            safe_x2 = page_rect.width
            safe_y1 = max(0, y1)
            safe_y2 = min(page_rect.height, y2)
            
            crop_rect = fitz.Rect(safe_x1, safe_y1, safe_x2, safe_y2)
            
            section_doc = fitz.open()
            new_page = section_doc.new_page(width=safe_x2 - safe_x1, height=safe_y2 - safe_y1)
            new_page.show_pdf_page(new_page.rect, source_doc, page_idx, clip=crop_rect)
            
            section_doc.save(str(output_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Extract failed: {e}")
            return False
    
    def _backup_config(self):
        """Backup original config"""
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _update_config(self, detector_config, splitter_config):
        """Update config file"""
        config = {
            "StructureDetector": detector_config,
            "StructureSplitter": splitter_config
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, indent=2)
    
    def _restore_config(self, original_config):
        """Restore original config"""
        with open(self.config_file, 'w') as f:
            yaml.dump(original_config, f, indent=2)
    
    def _save_test_summary(self, test_name, detector_config, splitter_config, 
                          detector_result, splitter_result, test_output):
        """Save test summary"""
        summary = {
            "test_name": test_name,
            "pdf_file": str(self.pdf_path),
            "config": {
                "detector": detector_config,
                "splitter": splitter_config
            },
            "results": {
                "blocks_found": len(detector_result.get('large_blocks', [])),
                "sections_created": len(splitter_result.get('sections', [])),
                "detector_status": detector_result.get('status'),
                "splitter_status": splitter_result.get('status')
            },
            "timestamp": datetime.now().isoformat()
        }
        
        summary_file = test_output / "test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
    
    def _run_detector_direct(self, detector, test_output):
        """Run detector without Luigi"""
        try:
            config = detector._load_config()
            large_blocks = detector._extract_large_blocks(config)
            
            result = {
                "task_name": "StructureDetector",
                "input_file": str(self.pdf_path),
                "status": "success",
                "large_blocks": large_blocks,
                "blocks_count": len(large_blocks),
                "config_used": config,
                "created_at": datetime.now().isoformat()
            }
            
            # Save result
            result_file = test_output / "detector_result.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
            
        except Exception as e:
            print(f"❌ Detector failed: {e}")
            return None
    
    def _run_splitter_direct(self, detector_result, test_output):
        """Run splitter without Luigi"""
        try:
            from pipeline.structure.config import get_splitter_config
            
            config = get_splitter_config()
            
            # Create splitter instance
            splitter = StructureSplitter(file_path=str(self.pdf_path))
            
            # Override output to test directory
            sections_dir = test_output / "sections"
            sections_dir.mkdir(exist_ok=True)
            
            # Run splitting logic
            sections = self._run_splitting_logic(detector_result, config, sections_dir)
            
            result = {
                "task_name": "StructureSplitter",
                "input_file": str(self.pdf_path),
                "status": "success",
                "sections_created": len(sections),
                "sections": sections,
                "splitting_method": "test_direct",
                "created_at": datetime.now().isoformat()
            }
            
            # Save result
            result_file = test_output / "splitter_result.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            return result
            
        except Exception as e:
            print(f"❌ Splitter failed: {e}")
            return None
    
    def _run_splitting_logic(self, detector_result, config, sections_dir):
        """Run actual splitting logic"""
        import fitz
        
        large_blocks = detector_result["large_blocks"]
        
        if not large_blocks:
            return []
        
        sections = []
        doc = fitz.open(self.pdf_path)
        
        try:
            for i, block in enumerate(large_blocks):
                page_num = block["page"]
                bbox = block["bbox"]
                
                # Create filename
                filename = f"section_{i:03d}_block_{i}.pdf"
                file_path = sections_dir / filename
                
                # Extract with full width
                success = self._extract_block_pdf_direct(doc, page_num, bbox, file_path)
                
                if success:
                    sections.append({
                        "title": f"block_{i}",
                        "filename": filename,
                        "file_path": str(file_path),
                        "page": page_num,
                        "bbox": bbox,
                        "block_index": i,
                        "block_area": block.get("area", 0)
                    })
        finally:
            doc.close()
        
        return sections
    
    def _extract_block_pdf_direct(self, source_doc, page_num, bbox, output_path):
        """Extract block PDF with full width"""
        try:
            page_idx = page_num - 1
            source_page = source_doc[page_idx]
            page_rect = source_page.rect
            
            # Full width, Y from bbox
            x1, y1, x2, y2 = bbox
            safe_x1 = 0
            safe_x2 = page_rect.width
            safe_y1 = max(0, y1)
            safe_y2 = min(page_rect.height, y2)
            
            crop_rect = fitz.Rect(safe_x1, safe_y1, safe_x2, safe_y2)
            
            section_doc = fitz.open()
            new_page = section_doc.new_page(width=safe_x2 - safe_x1, height=safe_y2 - safe_y1)
            new_page.show_pdf_page(new_page.rect, source_doc, page_idx, clip=crop_rect)
            
            section_doc.save(str(output_path), garbage=3, clean=True, ascii=False)
            section_doc.close()
            
            return True
            
        except Exception as e:
            print(f"❌ Extract failed: {e}")
            return False
    
    def _backup_config(self):
        """Backup original config"""
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _update_config(self, detector_config, splitter_config):
        """Update config file"""
        config = {
            "StructureDetector": detector_config,
            "StructureSplitter": splitter_config
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(config, f, indent=2)
    
    def _restore_config(self, original_config):
        """Restore original config"""
        with open(self.config_file, 'w') as f:
            yaml.dump(original_config, f, indent=2)
    
    def _save_test_summary(self, test_name, detector_config, splitter_config, 
                          detector_result, splitter_result, test_output):
        """Save test summary"""
        summary = {
            "test_name": test_name,
            "pdf_file": str(self.pdf_path),
            "config": {
                "detector": detector_config,
                "splitter": splitter_config
            },
            "results": {
                "blocks_found": len(detector_result.get('large_blocks', [])),
                "sections_created": len(splitter_result.get('sections', [])),
                "detector_status": detector_result.get('status'),
                "splitter_status": splitter_result.get('status')
            },
            "timestamp": datetime.now().isoformat()
        }
        
        summary_file = test_output / "test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) != 2:
        print("Usage: python tests/test_structure_config.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    tester = StructureConfigTester(pdf_path)
    
    print(f"🧪 Structure Config Tester")
    print(f"📄 Testing PDF: {pdf_path}")
    print(f"📁 Output: {tester.base_output}")

    tester.test_config("ultra_sensitive",
        detector_config={
            "min_block_area": 100,
            "zoom_factor": 1.0,
            "merge_gap_px": 5,
            "max_pages": 1000
        },
        splitter_config={
            "min_section_height_px": 10,
            "max_filename_length": 50,
            "output_format": "pdf"
        })
    
    print(f"\n✅ All tests complete! Check results in: {tester.base_output}")
    print(f"📊 Compare test_summary.json files to find best settings")


if __name__ == "__main__":
    main()