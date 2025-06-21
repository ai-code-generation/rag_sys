"""
Custom Reranking Service
A FastAPI-based reranking service that implements the NVIDIA NIM reranking API interface.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sentence_transformers import CrossEncoder
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API
class QueryModel(BaseModel):
    text: str

class PassageModel(BaseModel):
    text: str

class RankingRequest(BaseModel):
    model: str = Field(default="custom-reranker", description="Model name")
    query: QueryModel
    passages: List[PassageModel]
    truncate: Optional[str] = Field(default="NONE", description="Truncation strategy: NONE or END")

class RankingResult(BaseModel):
    index: int
    logit: float

class RankingResponse(BaseModel):
    rankings: List[RankingResult]

class HealthResponse(BaseModel):
    status: str = "healthy"

# Global model instance
reranker_model = None

def load_reranker_model():
    """Load the cross-encoder model for reranking."""
    global reranker_model
    try:
        # Using a lightweight cross-encoder model
        # You can replace this with any cross-encoder model from sentence-transformers
        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        logger.info(f"Loading reranker model: {model_name}")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")

        reranker_model = CrossEncoder(model_name, device=device)
        logger.info("Reranker model loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load reranker model: {e}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Custom Reranking Service...")
    load_reranker_model()
    logger.info("Custom Reranking Service started successfully")
    yield
    # Shutdown
    logger.info("Shutting down Custom Reranking Service...")

def rerank_passages(query: str, passages: List[str], truncate: str = "NONE") -> List[Dict[str, Any]]:
    """
    Rerank passages based on relevance to the query.
    
    Args:
        query: The search query
        passages: List of passage texts to rerank
        truncate: Truncation strategy ("NONE" or "END")
    
    Returns:
        List of ranking results with index and logit
    """
    if not reranker_model:
        raise HTTPException(status_code=500, detail="Reranker model not loaded")
    
    if not passages:
        return []
    
    try:
        # Prepare query-passage pairs for the cross-encoder
        pairs = [[query, passage] for passage in passages]
        
        # Handle truncation if needed
        if truncate == "END":
            # For simplicity, we'll let the model handle truncation internally
            # In a production system, you might want to implement custom truncation
            pass
        elif truncate == "NONE":
            # Check if any input is too long (simplified check)
            max_length = 512  # Typical transformer limit
            for i, (q, p) in enumerate(pairs):
                if len(q.split()) + len(p.split()) > max_length:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Input too long for passage {i}. Use truncate='END' to handle long inputs."
                    )
        
        # Get scores from the cross-encoder
        scores = reranker_model.predict(pairs)
        
        # Convert scores to logits (cross-encoder already returns logits)
        # Create ranking results with original indices
        rankings = []
        for idx, score in enumerate(scores):
            rankings.append({
                "index": idx,
                "logit": float(score)
            })
        
        # Sort by logit score in descending order
        rankings.sort(key=lambda x: x["logit"], reverse=True)
        
        return rankings
        
    except Exception as e:
        logger.error(f"Error during reranking: {e}")
        raise HTTPException(status_code=500, detail=f"Reranking failed: {str(e)}")

# Create FastAPI app
app = FastAPI(
    title="Custom Reranking Service",
    description="A custom reranking service compatible with NVIDIA NIM reranking API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy")

@app.get("/v1/health/ready", response_model=HealthResponse)
async def health_ready():
    """Health ready check endpoint (NIM compatible)."""
    if reranker_model is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return HealthResponse(status="ready")

@app.post("/v1/ranking", response_model=RankingResponse)
async def rank_passages(request: RankingRequest):
    """
    Rerank passages based on relevance to the query.
    Compatible with NVIDIA NIM reranking API.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Received ranking request for {len(request.passages)} passages")
        
        # Extract text from passages
        passage_texts = [passage.text for passage in request.passages]
        query_text = request.query.text
        
        # Validate input
        if not query_text.strip():
            raise HTTPException(status_code=400, detail="Query text cannot be empty")
        
        if len(passage_texts) == 0:
            return RankingResponse(rankings=[])
        
        if len(passage_texts) > 512:
            raise HTTPException(status_code=400, detail="Too many passages. Maximum 512 passages allowed.")
        
        # Perform reranking
        rankings = rerank_passages(query_text, passage_texts, request.truncate)
        
        # Convert to response format
        ranking_results = [RankingResult(index=r["index"], logit=r["logit"]) for r in rankings]
        
        processing_time = time.time() - start_time
        logger.info(f"Reranking completed in {processing_time:.3f} seconds")
        
        return RankingResponse(rankings=ranking_results)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ranking: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Custom Reranking Service",
        "version": "1.0.0",
        "description": "A custom reranking service compatible with NVIDIA NIM reranking API",
        "endpoints": {
            "health": "/health",
            "ready": "/v1/health/ready", 
            "ranking": "/v1/ranking"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
