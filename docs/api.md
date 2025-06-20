# API Documentation

## Chain Server REST API

The Chain Server provides a comprehensive REST API for RAG operations.

### Base URL
```
http://localhost:8081
```

### Authentication
All endpoints require a valid `NVIDIA_API_KEY` to be set in the environment.

## Endpoints

### Health Check

#### GET /health
Check service health status.

**Response:**
```json
{
  "message": "Service is up."
}
```

### Document Management

#### POST /documents
Upload and ingest a document into the vector store.

**Request:**
- Content-Type: `multipart/form-data`
- Body: File upload

**Supported file types:** `.txt`, `.pdf`, `.md`

**Response:**
```json
{
  "message": "File uploaded successfully"
}
```

#### GET /documents
Retrieve list of ingested documents.

**Response:**
```json
{
  "documents": ["document1.pdf", "document2.txt"]
}
```

#### DELETE /documents
Delete a specific document from the vector store.

**Query Parameters:**
- `filename` (string): Name of the file to delete

**Response:**
```json
{
  "message": "Document filename.pdf deleted successfully"
}
```

### Generation

#### POST /generate
Generate responses using LLM with optional RAG.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is this document about?"
    }
  ],
  "use_knowledge_base": true,
  "temperature": 0.2,
  "top_p": 0.7,
  "max_tokens": 1024,
  "stop": []
}
```

**Parameters:**
- `messages` (array): Conversation history
- `use_knowledge_base` (boolean): Enable RAG mode
- `temperature` (float): Sampling temperature (0.1-1.0)
- `top_p` (float): Top-p sampling (0.1-1.0)
- `max_tokens` (integer): Maximum response tokens (0-1024)
- `stop` (array): Stop sequences

**Response:**
Server-sent events stream with JSON chunks:
```json
{
  "id": "response-uuid",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response chunk..."
      },
      "finish_reason": ""
    }
  ]
}
```

### Document Search

#### POST /search
Search for relevant documents based on query.

**Request Body:**
```json
{
  "query": "search terms",
  "top_k": 4
}
```

**Parameters:**
- `query` (string): Search query
- `top_k` (integer): Number of results to return (0-25)

**Response:**
```json
{
  "chunks": [
    {
      "content": "Document content...",
      "filename": "document.pdf",
      "score": 0.85
    }
  ]
}
```

## Error Responses

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "field"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "message": "Error description"
}
```

## Usage Examples

### Python
```python
import requests

# Upload document
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8081/documents',
        files={'file': f}
    )

# Generate response
response = requests.post(
    'http://localhost:8081/generate',
    json={
        'messages': [{'role': 'user', 'content': 'Summarize this document'}],
        'use_knowledge_base': True
    }
)
```

### cURL
```bash
# Upload document
curl -X POST "http://localhost:8081/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"

# Generate response
curl -X POST "http://localhost:8081/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is this about?"}],
    "use_knowledge_base": true
  }'
```

### JavaScript
```javascript
// Upload document
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8081/documents', {
  method: 'POST',
  body: formData
});

// Generate response
fetch('http://localhost:8081/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    messages: [{role: 'user', content: 'Explain this document'}],
    use_knowledge_base: true
  })
});
```
