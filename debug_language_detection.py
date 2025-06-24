#!/usr/bin/env python3
"""Debug script to test language detection."""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_playground'))

from frontend.code_extractor import CodeExtractor
from frontend.file_generator import FileGenerator

def debug_language_detection():
    """Debug language detection for Python code."""
    print("🔍 Debugging Language Detection...")
    
    # Test response that should generate Python
    test_response = """
Here's a Python example:

```python
def hello_world():
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    result = hello_world()
    print(f"Result: {result}")
```
"""
    
    print("📝 Test Response:")
    print(test_response)
    print("\n" + "="*50)
    
    # Test code extraction first
    extractor = CodeExtractor()
    extracted_code = extractor.extract_code_blocks(test_response)
    
    print(f"\n🔍 Code Extraction Results:")
    print(f"   Has code: {extracted_code.has_code}")
    print(f"   Total blocks: {extracted_code.total_blocks}")
    
    for i, block in enumerate(extracted_code.blocks, 1):
        print(f"\n   📄 Block {i}:")
        print(f"      Language: '{block.language}'")
        print(f"      Content length: {len(block.content)} chars")
        print(f"      Content preview: {repr(block.content[:50])}...")
        
        # Test file extension generation
        extension = extractor.get_file_extension(block.language)
        print(f"      Expected extension: {extension}")
    
    print("\n" + "="*50)
    
    # Test file generation
    generator = FileGenerator()
    generator.cleanup_all_files()
    
    result = generator.generate_files_from_response(test_response)
    
    print(f"\n📁 File Generation Results:")
    print(f"   Success: {result.success}")
    print(f"   Message: {result.message}")
    print(f"   Total files: {result.total_files}")
    
    if result.files:
        file_info = result.files[0]
        print(f"\n   📄 Generated File:")
        print(f"      Filename: {file_info.filename}")
        print(f"      Language: '{file_info.language}'")
        print(f"      Size: {file_info.size} bytes")
        print(f"      Extension: {os.path.splitext(file_info.filename)[1]}")
        
        # Check if file exists and show content
        if os.path.exists(file_info.filepath):
            with open(file_info.filepath, 'r') as f:
                content = f.read()
            print(f"      Content preview:")
            for i, line in enumerate(content.split('\n')[:5], 1):
                print(f"         {i}: {line}")
    
    # Test language normalization specifically
    print(f"\n🔧 Language Normalization Test:")
    test_languages = ['python', 'py', 'Python', 'PYTHON', 'java', 'javascript', 'js']
    
    for lang in test_languages:
        normalized = generator._normalize_language_name(lang)
        extension = extractor.get_file_extension(normalized)
        print(f"   '{lang}' → '{normalized}' → {extension}")
    
    # Cleanup
    generator.cleanup_all_files()
    print(f"\n🧹 Cleaned up test files")

if __name__ == "__main__":
    try:
        debug_language_detection()
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
