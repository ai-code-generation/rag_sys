#!/usr/bin/env python3
"""Test script to verify that each request generates separate files."""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_playground'))

from frontend.code_extractor import CodeExtractor
from frontend.file_generator import FileGenerator, get_file_generator

def test_separate_requests():
    """Test that each request generates separate files."""
    print("🧪 Testing Separate Request File Generation...")
    
    # First request - Python code
    python_response = """
Here's a Python example:

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))
```
"""
    
    # Second request - Java code
    java_response = """
Here's a Java example:

```java
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```
"""
    
    # Get the global file generator (simulating the actual usage)
    file_generator = get_file_generator()
    
    print("\n📝 Processing First Request (Python)...")
    
    # Clean up any existing files (simulating what happens in the UI)
    file_generator.cleanup_all_files()
    
    # Process first request
    result1 = file_generator.generate_files_from_response(python_response)
    
    print(f"✅ First request result:")
    print(f"   Success: {result1.success}")
    print(f"   Message: {result1.message}")
    print(f"   Files generated: {result1.total_files}")
    
    if result1.files:
        file1 = result1.files[0]
        print(f"   Filename: {file1.filename}")
        print(f"   Language: {file1.language}")
        
        # Read and check content
        if os.path.exists(file1.filepath):
            with open(file1.filepath, 'r') as f:
                content1 = f.read()
            print(f"   Content contains 'fibonacci': {'fibonacci' in content1}")
            print(f"   Content contains 'HelloWorld': {'HelloWorld' in content1}")
    
    print("\n📝 Processing Second Request (Java)...")
    
    # Clean up files from previous request (simulating what happens in the UI)
    file_generator.cleanup_all_files()
    
    # Process second request
    result2 = file_generator.generate_files_from_response(java_response)
    
    print(f"✅ Second request result:")
    print(f"   Success: {result2.success}")
    print(f"   Message: {result2.message}")
    print(f"   Files generated: {result2.total_files}")
    
    if result2.files:
        file2 = result2.files[0]
        print(f"   Filename: {file2.filename}")
        print(f"   Language: {file2.language}")
        
        # Read and check content
        if os.path.exists(file2.filepath):
            with open(file2.filepath, 'r') as f:
                content2 = f.read()
            print(f"   Content contains 'fibonacci': {'fibonacci' in content2}")
            print(f"   Content contains 'HelloWorld': {'HelloWorld' in content2}")
    
    # Verify separation
    print(f"\n🔍 Verification:")
    if result1.files and result2.files:
        file1 = result1.files[0]
        file2 = result2.files[0]
        
        # Check if first file still exists (it shouldn't after cleanup)
        file1_exists = os.path.exists(file1.filepath)
        file2_exists = os.path.exists(file2.filepath)
        
        print(f"   First file still exists: {'❌ Yes' if file1_exists else '✅ No (cleaned up)'}")
        print(f"   Second file exists: {'✅ Yes' if file2_exists else '❌ No'}")
        
        if file2_exists:
            with open(file2.filepath, 'r') as f:
                final_content = f.read()
            
            has_python = 'fibonacci' in final_content
            has_java = 'HelloWorld' in final_content
            
            print(f"   Final file contains Python code: {'❌ Yes' if has_python else '✅ No'}")
            print(f"   Final file contains Java code: {'✅ Yes' if has_java else '❌ No'}")
            
            if not has_python and has_java:
                print(f"   ✅ SUCCESS: Each request generates separate files!")
            else:
                print(f"   ❌ ISSUE: Files are being combined across requests")
    
    # Final cleanup
    file_generator.cleanup_all_files()
    print(f"\n🧹 Cleaned up test files")
    
    print(f"\n🎉 Separate request test completed!")

if __name__ == "__main__":
    try:
        test_separate_requests()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
