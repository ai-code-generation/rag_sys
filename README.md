# Custom Basic RAG - Modular Architecture

A modular, production-ready implementation of NVIDIA's Basic RAG example with clean service separation and modern deployment practices.

## 🏗️ Architecture Overview

This project follows a microservices architecture with clear separation of concerns:

```
custom_basic_rag_modular/
├── services/                    # Microservices
│   ├── chain-server/           # RAG backend API
│   └── rag-playground/         # Web UI frontend
├── infrastructure/             # Infrastructure components
│   ├── vectordb/              # Vector database (Milvus)
│   └── nim-services/          # NVIDIA NIM services
├── docs/                      # Documentation
└── docker-compose.yml         # Main orchestration
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- NVIDIA API Key ([Get one free](https://build.nvidia.com/explore/discover))
- 8GB+ RAM recommended

### 1. Set Environment Variables
```bash
export NVIDIA_API_KEY="nvapi-your-key-here"
```

### 2. Deploy the Stack
```bash
# Clone and navigate
cd custom_basic_rag_modular

# Start all services
docker compose up -d --build
```

### 3. Access the Application
- **RAG Playground**: http://localhost:8090
- **Chain Server API**: http://localhost:8081
- **API Documentation**: http://localhost:8081/docs

## 📋 Services

### Chain Server (Backend)
- **Port**: 8081
- **Purpose**: RAG operations, document ingestion, LLM interactions
- **Technology**: FastAPI, LangChain, PyMilvus
- **Documentation**: [services/chain-server/README.md](services/chain-server/README.md)

### RAG Playground (Frontend)
- **Port**: 8090
- **Purpose**: Web UI for document management and chat
- **Technology**: Streamlit
- **Documentation**: [services/rag-playground/README.md](services/rag-playground/README.md)

### Infrastructure Components
- **Milvus**: Vector database for embeddings
- **NVIDIA NIM**: Optional local model serving
- **Observability**: OpenTelemetry (configurable)

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and customize:

```bash
# Required
NVIDIA_API_KEY=nvapi-your-key-here

# Model Configuration
APP_LLM_MODELNAME=meta/llama3-8b-instruct
APP_EMBEDDINGS_MODELNAME=nvidia/nv-embedqa-e5-v5

# Retrieval Settings
APP_RETRIEVER_TOPK=4
APP_RETRIEVER_SCORETHRESHOLD=0.25

# UI Mode
PLAYGROUND_MODE=default  # or 'speech' for voice features
```

### Service-Specific Configuration
Each service has its own configuration options. See individual service READMEs for details.

## 📖 Usage

### Document Management
1. Open http://localhost:8090
2. Navigate to "Knowledge Base" tab
3. Upload TXT, PDF, or MD files
4. Wait for processing confirmation

### Chat with Documents
1. Go to "Chat" tab
2. Enable "Use knowledge base"
3. Ask questions about your uploaded documents
4. Get real-time streaming responses

### API Access
Use the REST API directly:
```bash
# Upload document
curl -X POST "http://localhost:8081/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"

# Generate response
curl -X POST "http://localhost:8081/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is this document about?"}],
    "use_knowledge_base": true
  }'
```

## 🛠️ Development

### Service Development
Each service can be developed independently:

```bash
# Chain Server
cd services/chain-server
pip install -r requirements.txt
uvicorn src.server:app --reload

# RAG Playground
cd services/rag-playground
pip install -r requirements.txt
streamlit run src/default/__main__.py
```

### Adding New Features
- **New Chain Types**: Add to `services/chain-server/src/chains/`
- **UI Components**: Modify `services/rag-playground/src/`
- **Infrastructure**: Add to `infrastructure/`

## 📊 Monitoring & Observability

The stack includes optional observability features:
- OpenTelemetry tracing
- Service health checks
- Structured logging

Enable by setting `ENABLE_TRACING=true` in your environment.

## 🔒 Production Considerations

### Security
- Set strong API keys
- Use HTTPS in production
- Implement authentication for the UI
- Network isolation between services

### Scaling
- Scale services independently with Docker Compose
- Use external vector database for production
- Implement load balancing for high availability

### Backup & Recovery
- Regular vector database backups
- Document storage redundancy
- Configuration management

## 🐛 Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   # Check logs
   docker compose logs chain-server
   docker compose logs rag-playground
   ```

2. **API key issues**
   ```bash
   # Verify key is set
   echo $NVIDIA_API_KEY
   ```

3. **Port conflicts**
   ```bash
   # Check what's using ports
   netstat -tulpn | grep :8081
   netstat -tulpn | grep :8090
   ```

### Getting Help
- Check service-specific READMEs
- Review Docker Compose logs
- Verify environment variables
- Ensure all prerequisites are met

## 📚 Documentation

- [Chain Server Documentation](services/chain-server/README.md)
- [RAG Playground Documentation](services/rag-playground/README.md)
- [API Documentation](http://localhost:8081/docs) (when running)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is based on NVIDIA's GenerativeAIExamples and follows the same Apache 2.0 license.
