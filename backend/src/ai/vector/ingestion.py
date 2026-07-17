import hashlib
import time
from typing import List, Dict, Any, Optional
from src.ai.vector.types import DocumentDTO, ChunkDTO
from src.ai.vector.namespaces import VectorNamespaces
from src.ai.vector.namespace_config import get_namespace_config
from src.ai.embeddings.provider import get_embedding_provider
from src.ai.chunking.chunker import chunk_document
from src.ai.vector.repository import DocumentRepository, VectorRepository
from src.system.logger import setup_logger

logger = setup_logger("DocumentIngestionService")


class DocumentIngestionService:
    @staticmethod
    def ingest_document(
        namespace: str,
        source_type: str,
        source_id: str,
        content: str,
        owner_type: str,
        owner_id: str,
        doc_metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentDTO:
        """Run the ingestion pipeline: Parser -> Chunker -> Embedding -> Storage, keeping versioning and checksum matches."""
        start_time = time.time()
        logger.info(f"Starting ingestion pipeline for namespace={namespace}, source={source_type}/{source_id}")
        
        # 1. Resolve configuration
        config = get_namespace_config(namespace)
        provider_name = config["provider"]
        model_name = config["model"]
        dimensions = config["dimensions"]
        distance = config["distance"]
        chunk_strategy = config["chunk_strategy"]
        chunk_size = config["chunk_size"]
        overlap = config["overlap"]

        # Compute document checksum
        doc_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        
        # 2. Check if document exists and is unchanged
        existing_doc = DocumentRepository.get_by_source(namespace, source_type, source_id)
        if existing_doc and existing_doc.checksum == doc_hash:
            logger.info("Document checksum matches existing record. Skipping re-indexing.")
            return existing_doc

        # Resolve versioning
        next_version = 1
        if existing_doc:
            next_version = existing_doc.version + 1
            # Mark previous version as not latest
            existing_doc.is_latest = False
            DocumentRepository.save(existing_doc)

        # 3. Create document record
        new_doc = DocumentDTO(
            namespace=namespace,
            source_type=source_type,
            source_id=source_id,
            checksum=doc_hash,
            version=next_version,
            is_latest=True,
            status="QUEUED",
            embedding_provider=provider_name,
            embedding_model=model_name,
            embedding_dimension=dimensions,
            distance_metric=distance
        )
        doc_id = DocumentRepository.save(new_doc)
        
        # 4. Chunk document
        DocumentRepository.update_status(doc_id, "CHUNKING")
        chunk_dicts = chunk_document(content, strategy=chunk_strategy, chunk_size=chunk_size, overlap=overlap)
        
        # 5. Embed chunks
        DocumentRepository.update_status(doc_id, "EMBEDDING")
        embedder = get_embedding_provider(provider_name, model_name, dimensions)
        
        chunks_to_save: List[ChunkDTO] = []
        texts_to_embed: List[str] = []
        temp_chunks: List[ChunkDTO] = []
        
        # Calculate chunk checksums and check cache
        indices_needing_embedding = []
        for idx, item in enumerate(chunk_dicts):
            chunk_content = item["content"]
            chunk_hash = hashlib.md5(chunk_content.encode("utf-8")).hexdigest()
            
            # Populate chunk DTO
            chunk_meta = doc_metadata.copy() if doc_metadata else {}
            chunk_meta.update(item["metadata"])
            
            chunk_dto = ChunkDTO(
                document_id=doc_id,
                owner_type=owner_type,
                owner_id=owner_id,
                content=chunk_content,
                chunk_checksum=chunk_hash,
                chunk_index=idx,
                chunk_metadata=chunk_meta
            )
            
            # Attempt to reuse existing embedding by chunk checksum
            existing_emb = VectorRepository.get_chunk_by_checksum(chunk_hash)
            if existing_emb:
                chunk_dto.embedding = existing_emb
                logger.info(f"Reusing cached embedding for chunk index {idx} (checksum match).")
            else:
                indices_needing_embedding.append(len(temp_chunks))
                texts_to_embed.append(chunk_content)
                
            temp_chunks.append(chunk_dto)

        # Generate embeddings only for new/modified chunks
        if texts_to_embed:
            logger.info(f"Generating embeddings for {len(texts_to_embed)} new/modified chunks...")
            embeddings = embedder.embed_batch(texts_to_embed)
            for sub_idx, emb in enumerate(embeddings):
                target_chunk_idx = indices_needing_embedding[sub_idx]
                temp_chunks[target_chunk_idx].embedding = emb

        chunks_to_save = temp_chunks

        # 6. Save chunks and finalize status
        DocumentRepository.update_status(doc_id, "INDEXING")
        VectorRepository.save_chunks(chunks_to_save)
        DocumentRepository.update_status(doc_id, "READY")
        
        latency = time.time() - start_time
        logger.info(f"Completed ingestion pipeline for doc_id={doc_id} in {latency:.3f} seconds.")
        
        new_doc.status = "READY"
        return new_doc
