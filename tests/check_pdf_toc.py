#!/usr/bin/env python3
"""
Check if PDF has built-in Table of Contents
Usage: python check_pdf_toc.py <pdf_file>
"""

import sys
import fitz
from pathlib import Path


def check_pdf_toc(pdf_path: str):
    """Check PDF for built-in TOC and basic info"""
    
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        return False
    
    try:
        doc = fitz.open(pdf_path)
        
        # Basic PDF info
        print(f"📄 PDF: {Path(pdf_path).name}")
        print(f"📊 Pages: {len(doc)}")
        print(f"📝 Title: {doc.metadata.get('title', 'N/A')}")
        print(f"👤 Author: {doc.metadata.get('author', 'N/A')}")
        print()
        
        # Check built-in TOC
        toc = doc.get_toc()
        
        if toc:
            print(f"✅ Built-in TOC found: {len(toc)} entries")
            print("📋 TOC Structure:")
            
            for i, (level, title, page) in enumerate(toc):
                indent = "  " * (level - 1)
                # Truncate long titles
                title_short = title[:60] + "..." if len(title) > 60 else title
                print(f"{indent}Level {level}: {title_short} (page {page})")
                
                # Limit output for large TOCs
                if i >= 20:
                    print(f"{indent}... and {len(toc) - 21} more entries")
                    break
            
            print()
            print("🎯 TOC Statistics:")
            levels = [entry[0] for entry in toc]
            print(f"   Max depth: {max(levels)} levels")
            print(f"   Level distribution: {dict((l, levels.count(l)) for l in set(levels))}")
            
        else:
            print("❌ No built-in TOC found")
            print("💡 PDF may have visual TOC that needs extraction")
        
        doc.close()
        return len(toc) > 0
        
    except Exception as e:
        print(f"💥 Error reading PDF: {e}")
        return False


def main():
    """Main CLI entry point"""
    if len(sys.argv) != 2:
        print("Usage: python check_pdf_toc.py <pdf_file>")
        print()
        print("Examples:")
        print("  python check_pdf_toc.py docs/owu2.pdf")
        print("  python check_pdf_toc.py docs/cardiology.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    has_toc = check_pdf_toc(pdf_path)
    
    print()
    if has_toc:
        print("🚀 Built-in TOC available - could use doc.get_toc() directly")
    else:
        print("🔍 Manual TOC extraction needed - use luigi_toc_pipeline")
    
    sys.exit(0 if has_toc else 1)


if __name__ == "__main__":
    main()