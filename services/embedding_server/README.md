# 🐳 HuggingFace Embedding Server

A **simple containerized embedding service** using HuggingFace models with NVIDIA NIM API compatibility.

## 📁 Files

```
embedding_test/
├── 🐳 Dockerfile                    # Optimized container image
├── 🌐 embedding_server.py          # Main embedding server
├── 🚀 deploy_simple.sh             # Simple deployment script
├── 🧪 test_public_ip.sh            # Public IP testing
├── 📊 monitor_simple.sh            # Simple monitoring tools
├── 📋 requirements.txt             # Dependencies
├── 📖 README.md                    # This file
└── 📖 SIMPLE_DEPLOYMENT.md         # Detailed deployment guide
```

## 🎯 Features

- **Simple & Clean**: Direct Flask server access (no Nginx complexity)
- **NVIDIA NIM Compatible**: Drop-in replacement for NVIDIA embedding services
- **HuggingFace Models**: Use any sentence-transformers model
- **External Access**: Public IP support for API calls
- **Easy Monitoring**: Simple monitoring and testing tools

## 🚀 Quick Start

```bash
# 1. Deploy embedding server
./deploy_simple.sh

# 2. Test with your public IP
./test_public_ip.sh --ip YOUR_PUBLIC_IP

# 3. Monitor the server
./monitor_simple.sh status
```

## 📡 API Endpoints

### **Health Check:**
```bash
curl http://YOUR_IP:8000/health
```

### **Generate Embeddings:**
```bash
curl -X POST http://YOUR_IP:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "Your text here"}'
```

### **Batch Embeddings:**
```bash
curl -X POST http://YOUR_IP:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": ["Text 1", "Text 2", "Text 3"]}'
```

## 🔗 Integration with RAG System

Replace NVIDIA NIM in your RAG system:

```bash
# Update .env file:
APP_EMBEDDINGS_MODELENGINE="nvidia-ai-endpoints"
APP_EMBEDDINGS_SERVERURL="http://YOUR_PUBLIC_IP:8000/v1"
APP_EMBEDDINGS_DIMENSIONS=768
```

## 📊 Benefits

- ✅ **Free** - No API costs
- ✅ **Private** - Local processing
- ✅ **Simple** - No Nginx complexity
- ✅ **External Access** - Public IP support
- ✅ **Compatible** - NVIDIA NIM API format

## 🔧 Configuration

### **Custom Model:**
```bash
./deploy_simple.sh --model sentence-transformers/all-MiniLM-L6-v2
```

### **Custom Port:**
```bash
./deploy_simple.sh --port 8001
```

### **Specific IP:**
```bash
./deploy_simple.sh --bind-ip 192.168.1.100
```

## 📊 Management

### **Stop/Start:**
```bash
# Stop
docker-compose -f docker-compose.simple.yml --env-file .env.simple down

# Start
docker-compose -f docker-compose.simple.yml --env-file .env.simple up -d
```

### **Monitor:**
```bash
# Status
./monitor_simple.sh status

# Logs
./monitor_simple.sh logs

# Continuous monitoring
./monitor_simple.sh watch
```

## 🚨 Troubleshooting

### **Can't access externally:**
```bash
# Check container
docker ps

# Check firewall
sudo ufw allow 8000

# Test locally first
curl http://localhost:8000/health
```

For detailed documentation, see [SIMPLE_DEPLOYMENT.md](SIMPLE_DEPLOYMENT.md)
