import time
from typing import List, Dict, Any, Optional
from src.ai.vector.types import ChunkResultDTO
from src.ai.vector.namespaces import VectorNamespaces
from src.ai.vector.namespace_config import get_namespace_config
from src.ai.embeddings.provider import get_embedding_provider
from src.ai.vector.repository import VectorRepository
from src.system.logger import setup_logger

logger = setup_logger("VectorRetrievalService")


class VectorRetrievalService:
    @staticmethod
    def retrieve(
        query: str,
        namespace: str,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 1.0,
        keyword_weight: float = 0.0
    ) -> List[ChunkResultDTO]:
        """Run retrieval pipeline: query normalized -> embed -> similarity search -> filters -> scoring -> return."""
        start_time = time.time()
        
        # 1. Resolve namespace config
        config = get_namespace_config(namespace)
        provider_name = config["provider"]
        model_name = config["model"]
        dimensions = config["dimensions"]
        
        # Apply defaults if not specified by caller
        search_limit = limit if limit is not None else config.get("top_k", 10)
        threshold = score_threshold if score_threshold is not None else config.get("score_threshold", 0.0)

        logger.info(
            f"Retrieving from namespace={namespace} for query='{query[:30]}...' "
            f"limit={search_limit}, threshold={threshold}"
        )

        # 2. Normalize and embed query
        normalized_query = query.strip().lower()
        if not normalized_query:
            return []

        embedder = get_embedding_provider(provider_name, model_name, dimensions)
        query_embedding = embedder.embed_text(normalized_query)

        # 3. Fetch similarity matches from repository
        results = VectorRepository.search_similarity(
            namespace=namespace,
            query_embedding=query_embedding,
            limit=search_limit,
            score_threshold=threshold,
            owner_type=owner_type,
            owner_id=owner_id,
            metadata_filters=metadata_filters
        )

        latency = time.time() - start_time
        logger.info(f"Retrieved {len(results)} chunks from namespace={namespace} in {latency:.3f} seconds.")
        return results

    @staticmethod
    def hybrid_search(
        query: str,
        namespace: str,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: Optional[int] = None,
        score_threshold: Optional[float] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.8,
        keyword_weight: float = 0.2
    ) -> List[ChunkResultDTO]:
        """Placeholder for future hybrid search engine integration."""
        # Today we fall back to pure semantic search as hybrid weight logic is reserved for later
        return VectorRetrievalService.retrieve(
            query=query,
            namespace=namespace,
            owner_type=owner_type,
            owner_id=owner_id,
            limit=limit,
            score_threshold=score_threshold,
            metadata_filters=metadata_filters,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )

    @staticmethod
    def rerank(
        query: str,
        chunks: List[ChunkResultDTO],
        top_n: int = 5
    ) -> List[ChunkResultDTO]:
        """Placeholder for future cross-encoder reranker engine integrations."""
        # Returns top N chunks sorted by score
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_n]
