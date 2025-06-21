#!/usr/bin/env python3
"""
Custom HuggingFace Embedding Server
NVIDIA NIM API Compatible Embedding Server using HuggingFace models
"""

import os
import time
import json
from typing import List, Union
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer

class HuggingFaceEmbeddingServer:
    """NVIDIA NIM API compatible embedding server using HuggingFace models"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2", port: int = 8000):
        self.model_name = model_name
        self.port = port
        self.model = None
        self.app = Flask(__name__)
        self.setup_routes()
        
    def load_model(self):
        """Load the HuggingFace embedding model"""
        print(f"🔄 Loading HuggingFace model: {self.model_name}")
        start_time = time.time()
        
        try:
            self.model = SentenceTransformer(self.model_name)
            load_time = time.time() - start_time
            print(f"✅ Model loaded successfully in {load_time:.2f} seconds")
            print(f"📊 Model dimensions: {self.model.get_sentence_embedding_dimension()}")
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {str(e)}")
            return False
        
    def setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "model": self.model_name,
                "ready": self.model is not None
            })
        
        @self.app.route('/v1/embeddings', methods=['POST'])
        def create_embeddings():
            """Create embeddings endpoint - NVIDIA NIM API compatible"""
            try:
                # Parse request
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data provided"}), 400
                
                # Extract input text
                input_data = data.get('input', '')
                if not input_data:
                    return jsonify({"error": "No input provided"}), 400
                
                # Handle both string and list inputs
                if isinstance(input_data, str):
                    texts = [input_data]
                elif isinstance(input_data, list):
                    texts = input_data
                else:
                    return jsonify({"error": "Input must be string or list of strings"}), 400
                
                # Check if model is loaded
                if not self.model:
                    return jsonify({"error": "Model not loaded"}), 503
                
                # Generate embeddings
                start_time = time.time()
                embeddings = self.model.encode(texts)
                processing_time = time.time() - start_time
                
                # Format response like NVIDIA NIM API
                response = {
                    "object": "list",
                    "data": [
                        {
                            "object": "embedding",
                            "embedding": embedding.tolist(),
                            "index": i
                        }
                        for i, embedding in enumerate(embeddings)
                    ],
                    "model": self.model_name,
                    "usage": {
                        "prompt_tokens": sum(len(text.split()) for text in texts),
                        "total_tokens": sum(len(text.split()) for text in texts)
                    }
                }
                
                print(f"📝 Processed {len(texts)} text(s) in {processing_time:.4f}s")
                return jsonify(response)
                
            except Exception as e:
                print(f"❌ Error in embeddings endpoint: {str(e)}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/v1/models', methods=['GET'])
        def list_models():
            """List available models endpoint"""
            return jsonify({
                "object": "list",
                "data": [
                    {
                        "id": self.model_name,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "huggingface",
                        "permission": [],
                        "root": self.model_name,
                        "parent": None
                    }
                ]
            })
        
        @self.app.route('/', methods=['GET'])
        def root():
            """Root endpoint with server info"""
            return jsonify({
                "message": "HuggingFace Embedding Server",
                "model": self.model_name,
                "api_version": "v1",
                "compatible_with": "NVIDIA NIM API",
                "endpoints": {
                    "health": "/health",
                    "embeddings": "/v1/embeddings",
                    "models": "/v1/models"
                }
            })
    
    def start_server(self, debug: bool = False):
        """Start the embedding server"""
        print("🚀 Starting HuggingFace Embedding Server")
        print("=" * 50)
        print(f"📦 Model: {self.model_name}")
        print(f"🌐 Port: {self.port}")
        print(f"🔗 API Compatibility: NVIDIA NIM")
        print()
        
        # Load model first
        if not self.load_model():
            print("❌ Failed to start server - model loading failed")
            return
        
        print("📡 Available Endpoints:")
        print(f"   GET  http://localhost:{self.port}/health")
        print(f"   POST http://localhost:{self.port}/v1/embeddings")
        print(f"   GET  http://localhost:{self.port}/v1/models")
        print()
        print("🎯 Ready to serve embedding requests!")
        print("=" * 50)
        
        try:
            # Get host from environment or default to 0.0.0.0 for external access
            host = os.getenv('FLASK_HOST', '0.0.0.0')
            self.app.run(
                host=host,
                port=self.port,
                debug=debug,
                threaded=True
            )
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
        except Exception as e:
            print(f"❌ Server error: {str(e)}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HuggingFace Embedding Server")
    parser.add_argument("--model", default="sentence-transformers/all-mpnet-base-v2", 
                       help="HuggingFace model name")
    parser.add_argument("--port", type=int, default=8000, 
                       help="Server port")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Create and start server
    server = HuggingFaceEmbeddingServer(
        model_name=args.model,
        port=args.port
    )
    
    server.start_server(debug=args.debug)

if __name__ == "__main__":
    main()
