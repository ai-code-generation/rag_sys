# 🚀 Simple Deployment Guide (No Nginx)

Deploy HuggingFace Embedding Server with **direct Flask access** - no Nginx required.

## 🎯 Why Simple Deployment?

- ✅ **No Nginx complexity** - Direct Flask server access
- ✅ **Fewer moving parts** - Just one container
- ✅ **Easier debugging** - Direct logs and monitoring
- ✅ **Lower resource usage** - No reverse proxy overhead
- ✅ **Perfect for APIs** - Direct HTTP access

## 🚀 Quick Start

### **1. Deploy Simple Server:**
```bash
# Default deployment (port 8000, external access)
./deploy_simple.sh

# Custom model and port
./deploy_simple.sh --model sentence-transformers/all-MiniLM-L6-v2 --port 8001

# Bind to specific IP
./deploy_simple.sh --bind-ip 192.168.1.100 --port 8000
```

### **2. Test the Server:**
```bash
# Test with your public IP
./test_public_ip.sh --ip YOUR_PUBLIC_IP

# Manual test
curl http://YOUR_PUBLIC_IP:8000/health
```

### **3. Monitor the Server:**
```bash
# Check status
./monitor_simple.sh status

# Continuous monitoring
./monitor_simple.sh watch

# View logs
./monitor_simple.sh logs 50
```

## 📊 Deployment Options

### **Default (External Access):**
```bash
./deploy_simple.sh
```
- **Bind IP**: 0.0.0.0 (all interfaces)
- **Port**: 8000
- **Model**: sentence-transformers/all-mpnet-base-v2
- **Access**: http://YOUR_IP:8000

### **Custom Configuration:**
```bash
# Lightweight model
./deploy_simple.sh --model sentence-transformers/all-MiniLM-L6-v2

# Custom port
./deploy_simple.sh --port 8001

# Specific IP binding
./deploy_simple.sh --bind-ip 192.168.1.100

# Combined
./deploy_simple.sh --model all-MiniLM-L6-v2 --port 8001 --bind-ip 192.168.1.100
```

## 🧪 Testing

### **Health Check:**
```bash
curl http://YOUR_IP:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "model": "sentence-transformers/all-mpnet-base-v2",
  "ready": true
}
```

### **Single Embedding:**
```bash
curl -X POST http://YOUR_IP:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "Test text for embedding"}'
```

### **Batch Embeddings:**
```bash
curl -X POST http://YOUR_IP:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": ["Text 1", "Text 2", "Text 3"]}'
```

### **Automated Testing:**
```bash
# Test all endpoints
./test_public_ip.sh --ip YOUR_IP --port 8000

# Verbose output
./test_public_ip.sh --ip YOUR_IP --verbose
```

## 🔗 Integration

### **RAG System Integration:**
```bash
# Update your RAG system .env file:
APP_EMBEDDINGS_MODELENGINE="nvidia-ai-endpoints"
APP_EMBEDDINGS_SERVERURL="http://YOUR_IP:8000/v1"
APP_EMBEDDINGS_DIMENSIONS=768
```

### **Python Client:**
```python
import requests

class EmbeddingClient:
    def __init__(self, base_url="http://YOUR_IP:8000"):
        self.base_url = base_url
    
    def get_embedding(self, text):
        response = requests.post(
            f"{self.base_url}/v1/embeddings",
            json={"input": text},
            headers={"Content-Type": "application/json"}
        )
        return response.json()

# Usage
client = EmbeddingClient("http://192.168.1.100:8000")
result = client.get_embedding("Your text here")
embedding = result["data"][0]["embedding"]
```

### **JavaScript/Frontend:**
```javascript
async function getEmbedding(text) {
    const response = await fetch('http://YOUR_IP:8000/v1/embeddings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            input: text
        })
    });
    
    const data = await response.json();
    return data.data[0].embedding;
}
```

## 📊 Management Commands

### **Start/Stop:**
```bash
# Start (if stopped)
docker-compose -f docker-compose.simple.yml --env-file .env.simple up -d

# Stop
docker-compose -f docker-compose.simple.yml --env-file .env.simple down

# Restart
docker-compose -f docker-compose.simple.yml --env-file .env.simple restart
```

### **Logs:**
```bash
# View logs
docker-compose -f docker-compose.simple.yml --env-file .env.simple logs -f

# Or use monitor script
./monitor_simple.sh logs 100
```

### **Update Model:**
```bash
# Stop current deployment
docker-compose -f docker-compose.simple.yml --env-file .env.simple down

# Deploy with new model
./deploy_simple.sh --model sentence-transformers/all-MiniLM-L6-v2
```

## 🔧 Configuration Files

### **Generated Files:**
- **`.env.simple`** - Environment configuration
- **`docker-compose.simple.yml`** - Docker compose configuration

### **Environment Variables:**
```bash
# .env.simple
MODEL_NAME=sentence-transformers/all-mpnet-base-v2
PORT=8000
BIND_IP=0.0.0.0
WORKERS=1
MEMORY_LIMIT=2G
FLASK_HOST=0.0.0.0
```

## 🚨 Troubleshooting

### **Container won't start:**
```bash
# Check logs
./monitor_simple.sh logs

# Check Docker
docker ps -a
docker logs hf-embedding-server-simple
```

### **Can't access externally:**
```bash
# Check port binding
docker port hf-embedding-server-simple

# Check firewall
sudo ufw status
sudo ufw allow 8000

# Test locally first
curl http://localhost:8000/health
```

### **Performance issues:**
```bash
# Check resources
./monitor_simple.sh resources

# Check container stats
docker stats hf-embedding-server-simple
```

## 📈 Performance

### **Typical Performance:**
- **Startup time**: 30-60 seconds (model download + load)
- **Single embedding**: 50-100ms
- **Batch embedding**: 20-30ms per text
- **Memory usage**: 1-2GB
- **Concurrent requests**: 10-20/second

### **Resource Requirements:**
- **Minimum**: 2GB RAM, 1 CPU core
- **Recommended**: 4GB RAM, 2 CPU cores
- **Storage**: 2GB for model cache

## 🎯 Production Considerations

### **Security:**
- ✅ **Firewall**: Only open necessary ports
- ✅ **Updates**: Regular container updates
- ⚠️ **No rate limiting**: Consider adding if needed
- ⚠️ **No SSL**: Use load balancer for HTTPS

### **Monitoring:**
- ✅ **Health checks**: Built-in health endpoint
- ✅ **Logs**: Docker logging
- ✅ **Metrics**: Resource monitoring
- ⚠️ **Alerting**: Set up external monitoring

### **Scaling:**
- ✅ **Horizontal**: Run multiple containers
- ✅ **Load balancer**: Distribute requests
- ✅ **Resource limits**: Configure memory/CPU

## 🎉 Ready to Deploy!

Simple deployment gives you a **production-ready embedding server** without the complexity of Nginx:

```bash
# Deploy now
./deploy_simple.sh

# Test it
./test_public_ip.sh --ip YOUR_IP

# Monitor it
./monitor_simple.sh watch
```

Perfect for **API services**, **microservices**, and **direct integration**! 🚀
