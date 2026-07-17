import os
from typing import Dict, Any
from src.ai.vector.namespaces import VectorNamespaces

NAMESPACE_CONFIGS: Dict[VectorNamespaces, Dict[str, Any]] = {
    VectorNamespaces.RESUME_KB: {
        "provider": "gemini",
        "model": "models/text-embedding-004",
        "dimensions": 1536,
        "distance": "cosine",
        "chunk_strategy": "hierarchical",
        "chunk_size": 600,
        "overlap": 75,
        "top_k": 20,
        "score_threshold": 0.75,
        "max_context_chunks": 10,
        "reranker": None,
        "enable_hybrid": False,
        "enable_metadata_filter": True,
        "enable_keyword_search": False,
    },
    VectorNamespaces.CAREER_KB: {
        "provider": "gemini",
        "model": "models/text-embedding-004",
        "dimensions": 1536,
        "distance": "cosine",
        "chunk_strategy": "hierarchical",
        "chunk_size": 600,
        "overlap": 75,
        "top_k": 20,
        "score_threshold": 0.75,
        "max_context_chunks": 10,
        "reranker": None,
        "enable_hybrid": False,
        "enable_metadata_filter": True,
        "enable_keyword_search": False,
    },
    VectorNamespaces.USER_MEMORY: {
        "provider": "gemini",
        "model": "models/text-embedding-004",
        "dimensions": 1536,
        "distance": "cosine",
        "chunk_strategy": "plain_text",
        "chunk_size": 400,
        "overlap": 50,
        "top_k": 10,
        "score_threshold": 0.70,
        "max_context_chunks": 5,
        "reranker": None,
        "enable_hybrid": False,
        "enable_metadata_filter": True,
        "enable_keyword_search": False,
    },
    VectorNamespaces.DOCUMENTS: {
        "provider": "gemini",
        "model": "models/text-embedding-004",
        "dimensions": 1536,
        "distance": "cosine",
        "chunk_strategy": "hierarchical",
        "chunk_size": 600,
        "overlap": 75,
        "top_k": 15,
        "score_threshold": 0.75,
        "max_context_chunks": 8,
        "reranker": None,
        "enable_hybrid": False,
        "enable_metadata_filter": True,
        "enable_keyword_search": False,
    },
    VectorNamespaces.JOBS: {
        "provider": "gemini",
        "model": "models/text-embedding-004",
        "dimensions": 1536,
        "distance": "cosine",
        "chunk_strategy": "hierarchical",
        "chunk_size": 600,
        "overlap": 75,
        "top_k": 30,
        "score_threshold": 0.70,
        "max_context_chunks": 15,
        "reranker": None,
        "enable_hybrid": False,
        "enable_metadata_filter": True,
        "enable_keyword_search": False,
    },
    VectorNamespaces.COMPANIES: {
        "provider": "gemini",
        "model": "models/text-embedding-004",
        "dimensions": 1536,
        "distance": "cosine",
        "chunk_strategy": "hierarchical",
        "chunk_size": 600,
        "overlap": 75,
        "top_k": 15,
        "score_threshold": 0.75,
        "max_context_chunks": 8,
        "reranker": None,
        "enable_hybrid": False,
        "enable_metadata_filter": True,
        "enable_keyword_search": False,
    },
}

def get_namespace_config(namespace: str) -> Dict[str, Any]:
    try:
        ns = VectorNamespaces(namespace)
    except ValueError:
        raise ValueError(f"Unknown namespace: {namespace}")
    config = NAMESPACE_CONFIGS[ns].copy()
    
    # Prioritize environment variable overrides where configured
    env_provider = os.getenv("VECTOR_PROVIDER")
    if env_provider:
        config["provider"] = env_provider.lower()
        if env_provider.lower() == "mock":
            config["model"] = "mock-model"
            
    env_model = os.getenv("VECTOR_MODEL")
    if env_model:
        config["model"] = env_model
        
    return config
