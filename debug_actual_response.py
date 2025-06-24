#!/usr/bin/env python3
"""Debug script to test with various response formats."""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_playground'))

from frontend.code_extractor import CodeExtractor
from frontend.file_generator import FileGenerator

def test_various_response_formats():
    """Test various response formats that might come from the AI."""
    print("🔍 Testing Various Response Formats...")
    
    test_cases = [
        {
            "name": "Standard Python with language tag",
            "response": """Here's a Python example:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
```

This function calculates the Fibonacci sequence recursively."""
        },
        {
            "name": "Python without language tag",
            "response": """Here's a Python example:

```
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
```

This function calculates the Fibonacci sequence recursively."""
        },
        {
            "name": "Python with 'py' tag",
            "response": """Here's a Python example:

```py
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
```

This function calculates the Fibonacci sequence recursively."""
        },
        {
            "name": "Indented code block (no backticks)",
            "response": """Here's a Python example:

    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)

    print(fibonacci(10))

This function calculates the Fibonacci sequence recursively."""
        },
        {
            "name": "Mixed content with Python",
            "response": """I'll show you a Python function for calculating Fibonacci numbers.

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
```

You can also implement this iteratively for better performance."""
        }
    ]
    
    generator = FileGenerator()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"📝 Test Case {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        # Clean up any existing files
        generator.cleanup_all_files()
        
        # Show the response
        print(f"Response content:")
        print(repr(test_case['response']))
        print()
        
        # Test code extraction
        extractor = CodeExtractor()
        extracted_code = extractor.extract_code_blocks(test_case['response'])
        
        print(f"🔍 Extraction Results:")
        print(f"   Has code: {extracted_code.has_code}")
        print(f"   Total blocks: {extracted_code.total_blocks}")
        
        for j, block in enumerate(extracted_code.blocks, 1):
            print(f"   Block {j}: language='{block.language}', length={len(block.content)}")
        
        # Test file generation
        result = generator.generate_files_from_response(test_case['response'])
        
        print(f"\n📁 File Generation:")
        print(f"   Success: {result.success}")
        print(f"   Total files: {result.total_files}")
        
        if result.files:
            file_info = result.files[0]
            extension = os.path.splitext(file_info.filename)[1]
            print(f"   Filename: {file_info.filename}")
            print(f"   Extension: {extension}")
            print(f"   Language: '{file_info.language}'")
            
            # Check if we got the expected .py extension
            if extension == '.py':
                print(f"   ✅ Correct Python extension!")
            elif extension == '.txt':
                print(f"   ❌ Got .txt instead of .py - language detection failed!")
            else:
                print(f"   ⚠️  Got unexpected extension: {extension}")
        else:
            print(f"   ❌ No files generated!")
    
    # Cleanup
    generator.cleanup_all_files()
    print(f"\n🧹 Cleaned up all test files")

if __name__ == "__main__":
    try:
        test_various_response_formats()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
