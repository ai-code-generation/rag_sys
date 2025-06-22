"""
Custom Reranking Service
A FastAPI-based reranking service that implements the NVIDIA NIM reranking API interface.
Enhanced with accurate tokenization, flexible configuration, and improved error handling.
"""

import logging
import time
import os
import json
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from sentence_transformers import CrossEncoder
import torch
from transformers import AutoTokenizer
from dataclasses import dataclass
import hashlib
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration class for the reranking service."""
    model_name: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    cache_dir: str = os.getenv("CACHE_DIR", "/home/app/.cache")
    max_passages: int = int(os.getenv("MAX_PASSAGES", "512"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "32"))
    device: str = os.getenv("DEVICE", "auto")  # auto, cpu, cuda
    enable_caching: bool = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    cache_size: int = int(os.getenv("CACHE_SIZE", "1000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")

    def __post_init__(self):
        """Validate and adjust configuration after initialization."""
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # Set logging level
        logging.getLogger().setLevel(getattr(logging, self.log_level.upper()))

        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)

# Global configuration
config = ServiceConfig()

# Pydantic models for API
class QueryModel(BaseModel):
    text: str

    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Query text cannot be empty')
        return v.strip()

class PassageModel(BaseModel):
    text: str

    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Passage text cannot be empty')
        return v.strip()

class RankingRequest(BaseModel):
    model: str = Field(default=None, description="Model name (optional, uses service default)")
    query: QueryModel
    passages: List[PassageModel]
    truncate: Optional[str] = Field(default="NONE", description="Truncation strategy: NONE or END")

    @validator('model', pre=True, always=True)
    def set_default_model(cls, v):
        return v or config.model_name

    @validator('passages')
    def validate_passages(cls, v):
        if len(v) > config.max_passages:
            raise ValueError(f'Too many passages. Maximum {config.max_passages} passages allowed.')
        return v

class RankingResult(BaseModel):
    index: int
    logit: float

class RankingResponse(BaseModel):
    rankings: List[RankingResult]
    model: str = Field(description="Model used for ranking")
    processing_time_ms: Optional[float] = Field(description="Processing time in milliseconds")

class HealthResponse(BaseModel):
    status: str = "healthy"
    model_loaded: Optional[bool] = None
    device: Optional[str] = None
    model_name: Optional[str] = None

class ModelInfo(BaseModel):
    id: str
    max_length: Optional[int] = None
    device: Optional[str] = None

class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]

class ServiceMetrics(BaseModel):
    total_requests: int
    total_processing_time_ms: float
    average_processing_time_ms: float
    cache_hits: int
    cache_misses: int

# Global instances
reranker_model = None
tokenizer = None
service_metrics = {
    "total_requests": 0,
    "total_processing_time_ms": 0.0,
    "cache_hits": 0,
    "cache_misses": 0
}

def get_model_max_length(model_name: str) -> int:
    """Get the maximum sequence length for the model."""
    try:
        # Try to get from tokenizer config
        temp_tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=config.cache_dir
        )
        max_length = getattr(temp_tokenizer, 'model_max_length', 512)

        # Some models have very large max_length, cap it at reasonable value
        if max_length > 8192:
            max_length = 512

        logger.info(f"Model {model_name} max length: {max_length}")
        return max_length
    except Exception as e:
        logger.warning(f"Could not determine max length for {model_name}, using default 512: {e}")
        return 512

def load_reranker_model():
    """Load the cross-encoder model and tokenizer for reranking."""
    global reranker_model, tokenizer
    try:
        logger.info(f"Loading reranker model: {config.model_name}")
        logger.info(f"Using cache directory: {config.cache_dir}")
        logger.info(f"Using device: {config.device}")

        # Set environment variables for transformers cache
        os.environ['TRANSFORMERS_CACHE'] = config.cache_dir
        os.environ['HF_HOME'] = config.cache_dir

        # Load tokenizer for accurate token counting
        tokenizer = AutoTokenizer.from_pretrained(
            config.model_name,
            cache_dir=config.cache_dir
        )
        logger.info("Tokenizer loaded successfully")

        # Load cross-encoder model
        reranker_model = CrossEncoder(
            config.model_name,
            device=config.device
        )
        logger.info("Reranker model loaded successfully")

        # Log model information
        max_length = get_model_max_length(config.model_name)
        logger.info(f"Model max sequence length: {max_length}")

    except Exception as e:
        logger.error(f"Failed to load reranker model: {e}")
        raise

@lru_cache(maxsize=config.cache_size if config.enable_caching else 0)
def cached_rerank(query_hash: str, passages_hash: str, query: str, passages_tuple: tuple, truncate: str) -> str:
    """Cached reranking function to avoid recomputing identical requests."""
    return json.dumps(rerank_passages_internal(query, list(passages_tuple), truncate))

def get_content_hash(content: str) -> str:
    """Generate hash for content to use as cache key."""
    return hashlib.md5(content.encode()).hexdigest()

def count_tokens_accurately(text: str) -> int:
    """Count tokens using the model's tokenizer."""
    if tokenizer is None:
        # Fallback to word count if tokenizer not available
        return len(text.split())

    try:
        tokens = tokenizer.encode(text, add_special_tokens=True)
        return len(tokens)
    except Exception as e:
        logger.warning(f"Error counting tokens, falling back to word count: {e}")
        return len(text.split())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Enhanced Custom Reranking Service...")
    logger.info(f"Configuration: {config}")
    load_reranker_model()
    logger.info("Enhanced Custom Reranking Service started successfully")
    yield
    # Shutdown
    logger.info("Shutting down Enhanced Custom Reranking Service...")
    logger.info(f"Final metrics: {service_metrics}")

def truncate_text_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit."""
    if tokenizer is None:
        # Fallback: estimate by words (rough approximation)
        words = text.split()
        if len(words) <= max_tokens:
            return text
        return ' '.join(words[:max_tokens])

    try:
        tokens = tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= max_tokens:
            return text

        # Truncate tokens and decode back to text
        truncated_tokens = tokens[:max_tokens]
        return tokenizer.decode(truncated_tokens, skip_special_tokens=True)
    except Exception as e:
        logger.warning(f"Error truncating text, using word-based fallback: {e}")
        words = text.split()
        return ' '.join(words[:max_tokens])

def rerank_passages_internal(query: str, passages: List[str], truncate: str = "NONE") -> List[Dict[str, Any]]:
    """
    Internal reranking function (used by both cached and non-cached versions).
    """
    if not reranker_model:
        raise HTTPException(status_code=500, detail="Reranker model not loaded")

    if not passages:
        return []

    # Get model's actual max length
    model_max_length = get_model_max_length(config.model_name)

    # Reserve tokens for special tokens and query
    query_tokens = count_tokens_accurately(query)
    available_tokens_per_passage = model_max_length - query_tokens - 10  # 10 for special tokens

    try:
        # Prepare query-passage pairs for the cross-encoder
        pairs = []
        for i, passage in enumerate(passages):
            passage_tokens = count_tokens_accurately(passage)
            total_tokens = query_tokens + passage_tokens

            # Handle truncation based on strategy
            if truncate == "END" and total_tokens > model_max_length:
                # Truncate passage to fit
                truncated_passage = truncate_text_to_tokens(passage, available_tokens_per_passage)
                pairs.append([query, truncated_passage])
                logger.debug(f"Truncated passage {i} from {passage_tokens} to ~{available_tokens_per_passage} tokens")
            elif truncate == "NONE" and total_tokens > model_max_length:
                raise HTTPException(
                    status_code=400,
                    detail=f"Input too long for passage {i} ({total_tokens} tokens > {model_max_length} max). "
                           f"Use truncate='END' to handle long inputs."
                )
            else:
                pairs.append([query, passage])

        # Process in batches for memory efficiency
        all_scores = []
        batch_size = config.batch_size

        for i in range(0, len(pairs), batch_size):
            batch_pairs = pairs[i:i + batch_size]
            batch_scores = reranker_model.predict(batch_pairs)
            all_scores.extend(batch_scores)

        # Create ranking results with original indices
        rankings = []
        for idx, score in enumerate(all_scores):
            rankings.append({
                "index": idx,
                "logit": float(score)
            })

        # Sort by logit score in descending order
        rankings.sort(key=lambda x: x["logit"], reverse=True)

        return rankings

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during reranking: {e}")
        raise HTTPException(status_code=500, detail=f"Reranking failed: {str(e)}")

def rerank_passages(query: str, passages: List[str], truncate: str = "NONE") -> List[Dict[str, Any]]:
    """
    Rerank passages based on relevance to the query with caching support.

    Args:
        query: The search query
        passages: List of passage texts to rerank
        truncate: Truncation strategy ("NONE" or "END")

    Returns:
        List of ranking results with index and logit
    """
    if not config.enable_caching:
        return rerank_passages_internal(query, passages, truncate)

    # Use caching
    query_hash = get_content_hash(query)
    passages_hash = get_content_hash(''.join(passages) + truncate)

    try:
        result_json = cached_rerank(query_hash, passages_hash, query, tuple(passages), truncate)
        service_metrics["cache_hits"] += 1
        return json.loads(result_json)
    except Exception as e:
        logger.debug(f"Cache miss or error: {e}")
        service_metrics["cache_misses"] += 1
        return rerank_passages_internal(query, passages, truncate)

# Create FastAPI app
app = FastAPI(
    title="Enhanced Custom Reranking Service",
    description="An enhanced custom reranking service with accurate tokenization, flexible configuration, and caching",
    version="2.0.0",
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

# Exception handler for better error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )



@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with detailed information."""
    return HealthResponse(
        status="healthy",
        model_loaded=reranker_model is not None,
        device=config.device,
        model_name=config.model_name
    )

@app.get("/v1/health/ready", response_model=HealthResponse)
async def health_ready():
    """Health ready check endpoint (NIM compatible)."""
    if reranker_model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model or tokenizer not ready")
    return HealthResponse(
        status="ready",
        model_loaded=True,
        device=config.device,
        model_name=config.model_name
    )

@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    """List available models endpoint (NIM compatible)."""
    max_length = get_model_max_length(config.model_name) if reranker_model else None
    return ModelsResponse(
        object="list",
        data=[ModelInfo(
            id=config.model_name,
            max_length=max_length,
            device=config.device
        )]
    )

@app.get("/metrics", response_model=ServiceMetrics)
async def get_metrics():
    """Get service performance metrics."""
    total_requests = service_metrics["total_requests"]
    avg_time = (service_metrics["total_processing_time_ms"] / total_requests
                if total_requests > 0 else 0.0)

    return ServiceMetrics(
        total_requests=total_requests,
        total_processing_time_ms=service_metrics["total_processing_time_ms"],
        average_processing_time_ms=avg_time,
        cache_hits=service_metrics["cache_hits"],
        cache_misses=service_metrics["cache_misses"]
    )

@app.post("/v1/ranking", response_model=RankingResponse)
async def rank_passages(request: RankingRequest):
    """
    Rerank passages based on relevance to the query.
    Enhanced with accurate tokenization and flexible configuration.
    Compatible with NVIDIA NIM reranking API.
    """
    start_time = time.time()

    try:
        logger.info(f"Received ranking request for {len(request.passages)} passages using model {request.model}")

        # Extract text from passages (validation already done by Pydantic)
        passage_texts = [passage.text for passage in request.passages]
        query_text = request.query.text

        if len(passage_texts) == 0:
            return RankingResponse(
                rankings=[],
                model=request.model,
                processing_time_ms=0.0
            )

        # Perform reranking
        rankings = rerank_passages(query_text, passage_texts, request.truncate)

        # Convert to response format
        ranking_results = [RankingResult(index=r["index"], logit=r["logit"]) for r in rankings]

        processing_time_ms = (time.time() - start_time) * 1000

        # Update metrics
        service_metrics["total_requests"] += 1
        service_metrics["total_processing_time_ms"] += processing_time_ms

        logger.info(f"Reranking completed in {processing_time_ms:.1f}ms")

        return RankingResponse(
            rankings=ranking_results,
            model=request.model,
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in ranking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Enhanced Custom Reranking Service",
        "version": "2.0.0",
        "description": "An enhanced custom reranking service with accurate tokenization, flexible configuration, and caching",
        "model": config.model_name,
        "device": config.device,
        "max_passages": config.max_passages,
        "caching_enabled": config.enable_caching,
        "endpoints": {
            "health": "/health",
            "ready": "/v1/health/ready",
            "models": "/v1/models",
            "ranking": "/v1/ranking",
            "metrics": "/metrics"
        },
        "features": [
            "Accurate tokenization using model's tokenizer",
            "Dynamic max_length detection from model config",
            "Environment-based configuration",
            "Response caching for improved performance",
            "Batch processing for memory efficiency",
            "Comprehensive error handling",
            "Performance metrics tracking"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower()
    )
