"""
PDF utils with sequential start points cutting
"""

import fitz
from pathlib import Path
from .start_points_detector import StartPointsDetector


class PDFUtils:
    """Sequential cutting based on sorted start points"""
    
    @staticmethod
    def split_by_individual_entities(entries, doc, base_output_dir, doc_name, entry_format="detected"):
        """Compatibility method - routes to sequential start points"""
        return PDFUtils.split_by_sequential_start_points(entries, doc, base_output_dir, doc_name, entry_format)
    
    @staticmethod
    def split_by_sequential_start_points(entries, doc, base_output_dir, doc_name, entry_format="detected"):
        """Split using sequential start points approach"""
        from .section_creator import SectionCreator
        
        print(f"🔪 Sequential start points cutting:")
        print(f"   Total entries: {len(entries)}")
        print(f"   Entry format: {entry_format}")
        
        # Step 1: Find all start points and sort
        detector = StartPointsDetector()
        start_points = detector.find_all_start_points(doc, entries, entry_format)
        
        if not start_points:
            print("❌ No start points found")
            return []
        
        # Step 2: Create output directory
        output_dir = base_output_dir / doc_name / "sections"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        all_sections = []
        
        # Step 3: Cut sequential ranges
        for i, start_point in enumerate(start_points):
            page, start_y, entity_index, title, level = start_point
            
            # Find next boundary
            if i + 1 < len(start_points):
                next_page, next_y, _, _, _ = start_points[i + 1]
                end_boundary = (next_page, next_y)
            else:
                end_boundary = (len(doc), 0)  # Document end
            
            # Create section
            section = SectionCreator.create_sequential_section(
                doc, title, (page, start_y), end_boundary, level, entity_index, output_dir
            )
            
            if section:
                all_sections.append(section)
                print(f"📄 Created: {section['filename']}")
        
        print(f"✅ Created {len(all_sections)} sequential sections")
        return all_sections
    
    # UTILITY METHODS
    
    @staticmethod
    def get_base_output_dir():
        """Get base output directory"""
        return Path("output")
    
    @staticmethod
    def get_doc_name(file_path):
        """Get document name from file path"""
        return Path(file_path).stem