#!/usr/bin/env python3
"""Test the exact user scenario: 'generate a code example of Python'"""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_playground'))

from frontend.code_extractor import CodeExtractor
from frontend.file_generator import FileGenerator

def test_user_scenario():
    """Test the exact scenario the user encountered."""
    print("🧪 Testing User Scenario: 'generate a code example of Python'")
    
    # Simulate various possible AI responses to "generate a code example of Python"
    possible_responses = [
        {
            "name": "Response with proper language tag",
            "response": """Here's a Python code example:

```python
def greet(name):
    return f"Hello, {name}!"

def main():
    user_name = input("Enter your name: ")
    message = greet(user_name)
    print(message)

if __name__ == "__main__":
    main()
```

This example demonstrates basic function definition, string formatting, and user input in Python."""
        },
        {
            "name": "Response without language tag",
            "response": """Here's a Python code example:

```
def greet(name):
    return f"Hello, {name}!"

def main():
    user_name = input("Enter your name: ")
    message = greet(user_name)
    print(message)

if __name__ == "__main__":
    main()
```

This example demonstrates basic function definition, string formatting, and user input in Python."""
        },
        {
            "name": "Simple Python example",
            "response": """Here's a simple Python example:

```
print("Hello, World!")
x = 10
y = 20
print(f"The sum is: {x + y}")
```
"""
        },
        {
            "name": "Python with minimal content",
            "response": """Here's a Python example:

```
def hello():
    print("Hello!")

hello()
```
"""
        }
    ]
    
    generator = FileGenerator()
    
    for i, test_case in enumerate(possible_responses, 1):
        print(f"\n{'='*60}")
        print(f"📝 Test {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        # Clean up any existing files
        generator.cleanup_all_files()
        
        # Generate file
        result = generator.generate_files_from_response(test_case['response'])
        
        print(f"📁 File Generation Result:")
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print(f"   Total files: {result.total_files}")
        
        if result.files:
            file_info = result.files[0]
            extension = os.path.splitext(file_info.filename)[1]
            
            print(f"   📄 Generated File:")
            print(f"      Filename: {file_info.filename}")
            print(f"      Extension: {extension}")
            print(f"      Language: '{file_info.language}'")
            print(f"      Size: {file_info.size} bytes")
            
            # Check result
            if extension == '.py':
                print(f"      ✅ SUCCESS: Correct .py extension!")
            elif extension == '.txt':
                print(f"      ❌ ISSUE: Got .txt instead of .py")
                
                # Debug why it failed
                extractor = CodeExtractor()
                extracted_code = extractor.extract_code_blocks(test_case['response'])
                print(f"      🔍 Debug info:")
                for j, block in enumerate(extracted_code.blocks, 1):
                    detected = generator._detect_language_from_content(block.content)
                    print(f"         Block {j}: original_lang='{block.language}', detected='{detected}', content_length={len(block.content)}")
            else:
                print(f"      ⚠️  Unexpected extension: {extension}")
            
            # Show file content
            if os.path.exists(file_info.filepath):
                with open(file_info.filepath, 'r') as f:
                    content = f.read()
                print(f"      📋 Content preview:")
                for j, line in enumerate(content.split('\n')[:3], 1):
                    print(f"         {j}: {line}")
        else:
            print(f"   ❌ No files generated!")
    
    # Cleanup
    generator.cleanup_all_files()
    print(f"\n🧹 Cleaned up all test files")
    
    print(f"\n🎯 Summary:")
    print(f"The improved language detection should now correctly identify Python code")
    print(f"even when no language tag is provided in the markdown code blocks.")

if __name__ == "__main__":
    try:
        test_user_scenario()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
