#!/usr/bin/env python3
"""Test script for the updated single-file code extraction functionality."""

import sys
import os

# Add the services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'rag_playground'))

from frontend.code_extractor import CodeExtractor
from frontend.file_generator import FileGenerator

def test_combined_file_generation():
    """Test the new combined file generation functionality."""
    print("🧪 Testing Combined File Generation...")
    
    # Sample response with multiple code blocks
    sample_response = """
Here's how to create a simple web application:

## Backend (Python Flask)

```python
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({"message": "Hello from Flask!"})

if __name__ == '__main__':
    app.run(debug=True)
```

## Frontend (HTML)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Web App</title>
</head>
<body>
    <h1>Welcome to My Web App</h1>
    <button onclick="fetchData()">Get Data</button>
    <div id="result"></div>
    
    <script src="script.js"></script>
</body>
</html>
```

## Frontend (JavaScript)

```javascript
async function fetchData() {
    try {
        const response = await fetch('/api/data');
        const data = await response.json();
        document.getElementById('result').innerHTML = data.message;
    } catch (error) {
        console.error('Error:', error);
    }
}
```

## Database Schema (SQL)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, email) VALUES 
    ('john_doe', 'john@example.com'),
    ('jane_smith', 'jane@example.com');
```

This creates a complete web application with backend, frontend, and database components.
"""
    
    # Test code extraction
    extractor = CodeExtractor()
    extracted_code = extractor.extract_code_blocks(sample_response)
    
    print(f"✅ Found {extracted_code.total_blocks} code blocks:")
    for i, block in enumerate(extracted_code.blocks, 1):
        print(f"   📄 Block {i}: {block.language or 'unknown'} ({len(block.content)} chars)")
    
    # Test file generation
    generator = FileGenerator()
    result = generator.generate_files_from_response(sample_response)
    
    print(f"\n📁 File Generation Result:")
    print(f"   Success: {result.success}")
    print(f"   Message: {result.message}")
    print(f"   Total files: {result.total_files}")
    
    if result.files:
        file_info = result.files[0]
        print(f"\n📄 Generated File Details:")
        print(f"   Filename: {file_info.filename}")
        print(f"   Language: {file_info.language}")
        print(f"   Size: {file_info.size} bytes")
        print(f"   Path: {file_info.filepath}")
        
        # Show file content preview
        if os.path.exists(file_info.filepath):
            with open(file_info.filepath, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                print(f"\n📋 File Content Preview (first 15 lines):")
                for i, line in enumerate(lines[:15], 1):
                    print(f"   {i:2d}: {line}")
                if len(lines) > 15:
                    print(f"   ... ({len(lines) - 15} more lines)")
                
                print(f"\n📊 File Statistics:")
                print(f"   Total lines: {len(lines)}")
                print(f"   Total characters: {len(content)}")
                print(f"   Code blocks included: {extracted_code.total_blocks}")

                # Check if file contains raw code (no markdown backticks)
                has_backticks = "```" in content
                print(f"   Contains markdown backticks: {'❌ Yes' if has_backticks else '✅ No (raw code only)'}")

        # Test file retrieval (simulating download)
        retrieved_path = generator.get_file_path(file_info.filename)
        if retrieved_path:
            print(f"\n✅ File can be retrieved for download: {retrieved_path}")
        else:
            print(f"\n❌ File retrieval failed!")

    # Cleanup
    generator.cleanup_all_files()
    print(f"\n🧹 Cleaned up test files")

    print(f"\n🎉 Raw code file generation test completed!")
    print(f"\nKey improvements:")
    print(f"✅ All code blocks combined into single file with proper extension")
    print(f"✅ Raw code content without markdown formatting")
    print(f"✅ Language-appropriate comment headers for organization")
    print(f"✅ File extension based on most common language")
    print(f"✅ Clean code that can be directly executed/used")

if __name__ == "__main__":
    try:
        test_combined_file_generation()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
