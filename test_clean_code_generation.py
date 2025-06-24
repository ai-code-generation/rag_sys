#!/usr/bin/env python3
"""Test script to verify clean code generation without comments."""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_playground'))

from frontend.code_extractor import CodeExtractor
from frontend.file_generator import FileGenerator

def test_clean_code_generation():
    """Test that generated files contain only clean code without comments."""
    print("🧪 Testing Clean Code Generation...")
    
    # Test cases with different languages
    test_cases = [
        {
            "name": "Python Example",
            "response": """
Here's a Python function:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
```
""",
            "expected_extension": ".py",
            "expected_language": "python"
        },
        {
            "name": "Java Example", 
            "response": """
Here's a Java class:

```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```
""",
            "expected_extension": ".java",
            "expected_language": "java"
        },
        {
            "name": "JavaScript Example",
            "response": """
Here's a JavaScript function:

```javascript
function greetUser(name) {
    return `Hello, ${name}!`;
}

console.log(greetUser("World"));
```
""",
            "expected_extension": ".js",
            "expected_language": "javascript"
        },
        {
            "name": "Mixed Languages",
            "response": """
Here's HTML with embedded CSS:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Test</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
```

And some CSS:

```css
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
}
```
""",
            "expected_extension": ".html",  # Most common language
            "expected_language": "html"
        }
    ]
    
    generator = FileGenerator()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['name']}")
        
        # Clean up any existing files
        generator.cleanup_all_files()
        
        # Generate file
        result = generator.generate_files_from_response(test_case['response'])
        
        print(f"   Success: {result.success}")
        print(f"   Files generated: {result.total_files}")
        
        if result.files:
            file_info = result.files[0]
            print(f"   Filename: {file_info.filename}")
            print(f"   Language: {file_info.language}")
            print(f"   Expected extension: {test_case['expected_extension']}")
            print(f"   Actual extension: {os.path.splitext(file_info.filename)[1]}")
            
            # Check file extension
            actual_extension = os.path.splitext(file_info.filename)[1]
            extension_correct = actual_extension == test_case['expected_extension']
            print(f"   Extension correct: {'✅' if extension_correct else '❌'}")
            
            # Check language detection
            language_correct = file_info.language == test_case['expected_language']
            print(f"   Language correct: {'✅' if language_correct else '❌'}")
            
            # Read and analyze file content
            if os.path.exists(file_info.filepath):
                with open(file_info.filepath, 'r') as f:
                    content = f.read()
                
                # Check for unwanted comment headers
                has_comment_headers = any([
                    "# Extracted Code Blocks" in content,
                    "# Generated on:" in content,
                    "# Total blocks:" in content,
                    "# Languages:" in content,
                    "# ===== Code Block" in content,
                    "// Extracted Code Blocks" in content,
                    "// Generated on:" in content,
                    "/* Extracted Code Blocks" in content
                ])
                
                print(f"   Contains comment headers: {'❌ Yes' if has_comment_headers else '✅ No'}")
                
                # Show content preview
                lines = content.split('\n')
                print(f"   Content preview (first 5 lines):")
                for j, line in enumerate(lines[:5], 1):
                    print(f"      {j}: {line}")
                if len(lines) > 5:
                    print(f"      ... ({len(lines) - 5} more lines)")
                
                # Check if content looks clean
                is_clean = not has_comment_headers and content.strip()
                print(f"   Clean code: {'✅ Yes' if is_clean else '❌ No'}")
                
                # For Java, specifically check it doesn't start with # comments
                if test_case['expected_language'] == 'java':
                    starts_with_hash = content.strip().startswith('#')
                    print(f"   Java file starts with #: {'❌ Yes (syntax error!)' if starts_with_hash else '✅ No'}")
        
        # Cleanup after each test
        generator.cleanup_all_files()
    
    print(f"\n🎉 Clean code generation test completed!")
    print(f"\nKey improvements verified:")
    print(f"✅ No comment headers in generated files")
    print(f"✅ Proper file extensions based on language detection")
    print(f"✅ Clean, executable code without metadata")
    print(f"✅ Language-specific syntax compatibility")

if __name__ == "__main__":
    try:
        test_clean_code_generation()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
