import json
import uuid
from typing import List, Dict, Any, Optional
from src.api.db import get_connection, is_postgres
from src.ai.vector.types import DocumentDTO, ChunkDTO, ChunkResultDTO
from src.system.logger import setup_logger

logger = setup_logger("VectorRepository")


class DocumentRepository:
    @staticmethod
    def save(doc: DocumentDTO) -> str:
        """Insert or update a parent document."""
        conn = get_connection()
        try:
            doc_id = doc.id or str(uuid.uuid4())
            cursor = conn.cursor()
            
            # Upsert document record
            cursor.execute(
                """
                INSERT INTO public.documents (
                    id, namespace, source_type, source_id, checksum, version, is_latest, status,
                    embedding_provider, embedding_model, embedding_dimension, distance_metric, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO UPDATE SET
                    checksum = EXCLUDED.checksum,
                    version = EXCLUDED.version,
                    is_latest = EXCLUDED.is_latest,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    doc_id, doc.namespace, doc.source_type, doc.source_id, doc.checksum,
                    doc.version, doc.is_latest, doc.status, doc.embedding_provider,
                    doc.embedding_model, doc.embedding_dimension, doc.distance_metric
                )
            )
            conn.commit()
            doc.id = doc_id
            return doc_id
        finally:
            conn.close()

    @staticmethod
    def get_by_source(namespace: str, source_type: str, source_id: str) -> Optional[DocumentDTO]:
        """Fetch active document by source type and id."""
        conn = get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT id, namespace, source_type, source_id, checksum, version, is_latest, status,
                       embedding_provider, embedding_model, embedding_dimension, distance_metric
                FROM public.documents
                WHERE namespace = ? AND source_type = ? AND source_id = ? AND is_latest = TRUE
                """,
                (namespace, source_type, source_id)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            # Handle list/dict mappings based on db driver
            r = row if isinstance(row, dict) else dict(zip([col[0] for col in cursor.description], row))
            return DocumentDTO(
                id=r["id"],
                namespace=r["namespace"],
                source_type=r["source_type"],
                source_id=r["source_id"],
                checksum=r["checksum"],
                version=int(r["version"]),
                is_latest=bool(r["is_latest"]),
                status=r["status"],
                embedding_provider=r["embedding_provider"],
                embedding_model=r["embedding_model"],
                embedding_dimension=int(r["embedding_dimension"]),
                distance_metric=r["distance_metric"]
            )
        finally:
            conn.close()

    @staticmethod
    def update_status(doc_id: str, status: str):
        """Update indexing status of a document."""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE public.documents SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, doc_id)
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_by_source(namespace: str, source_type: str, source_id: str):
        """Hard delete a document and its referenced chunks."""
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM public.documents WHERE namespace = ? AND source_type = ? AND source_id = ?",
                (namespace, source_type, source_id)
            )
            conn.commit()
        finally:
            conn.close()


class VectorRepository:
    @staticmethod
    def save_chunks(chunks: List[ChunkDTO]):
        """Batch insert chunks with serialized embedding vectors."""
        if not chunks:
            return
        
        conn = get_connection()
        try:
            cursor = conn.cursor()
            records = []
            for chunk in chunks:
                chunk_id = chunk.id or str(uuid.uuid4())
                chunk.id = chunk_id
                
                # Format embedding as string array format for pgvector/SQLite
                emb_str = None
                if chunk.embedding:
                    emb_str = "[" + ",".join(map(str, chunk.embedding)) + "]"
                
                meta_str = json.dumps(chunk.chunk_metadata)
                records.append((
                    chunk_id, chunk.document_id, chunk.owner_type, chunk.owner_id,
                    chunk.chunk_index, chunk.chunk_checksum, meta_str,
                    chunk.content, emb_str, chunk.embedding_type
                ))
            
            cursor.executemany(
                """
                INSERT INTO public.vector_chunks (
                    id, document_id, owner_type, owner_id, chunk_index, chunk_checksum,
                    chunk_metadata, content, embedding, embedding_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_chunks_by_document(doc_id: str):
        """Clear chunks for a specific document version."""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM public.vector_chunks WHERE document_id = ?", (doc_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_chunk_by_checksum(checksum: str) -> Optional[List[float]]:
        """Fetch existing chunk embedding by checksum to skip re-embedding."""
        conn = get_connection()
        try:
            cursor = conn.execute(
                "SELECT embedding FROM public.vector_chunks WHERE chunk_checksum = ? LIMIT 1",
                (checksum,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            emb_str = row[0] if isinstance(row, tuple) else row["embedding"]
            if not emb_str:
                return None
            return json.loads(emb_str)
        finally:
            conn.close()

    @staticmethod
    def search_similarity(
        namespace: str,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.0,
        owner_type: Optional[str] = None,
        owner_id: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[ChunkResultDTO]:
        """Query nearest vector chunks using Cosine distance, supporting B-tree and JSONB filter rules."""
        postgres_mode = is_postgres()
        conn = get_connection()
        try:
            params = []
            
            # Format query embedding vector
            query_vector_str = "[" + ",".join(map(str, query_embedding)) + "]"
            
            if postgres_mode:
                # pgvector execution using HNSW cosine distance (<=> operator)
                # Score is 1 - Cosine Distance
                sql = """
                    SELECT vc.id, vc.document_id, vc.chunk_index, vc.content, vc.chunk_metadata,
                           (1 - (vc.embedding <=> %s::vector)) as score
                    FROM public.vector_chunks vc
                    JOIN public.documents d ON vc.document_id = d.id
                    WHERE d.namespace = %s AND d.is_latest = TRUE
                """
                params.extend([query_vector_str, namespace])
                
                if owner_type and owner_id:
                    sql += " AND vc.owner_type = %s AND vc.owner_id = %s"
                    params.extend([owner_type, owner_id])
                
                if metadata_filters:
                    sql += " AND vc.chunk_metadata @> %s::jsonb"
                    params.append(json.dumps(metadata_filters))
                
                sql += " ORDER BY vc.embedding <=> %s::vector LIMIT %s"
                params.extend([query_vector_str, limit])
                
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    r = row if isinstance(row, dict) else dict(zip([col[0] for col in cursor.description], row))
                    score = float(r["score"])
                    if score < score_threshold:
                        continue
                    
                    meta = r["chunk_metadata"]
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                        
                    results.append(ChunkResultDTO(
                        id=r["id"],
                        document_id=r["document_id"],
                        chunk_index=int(r["chunk_index"]),
                        content=r["content"],
                        chunk_metadata=meta,
                        score=score,
                        distance=1.0 - score
                    ))
                return results
            
            else:
                # SQLite fallback: fetch candidates, then compute cosine similarity in Python
                sql = """
                    SELECT vc.id, vc.document_id, vc.chunk_index, vc.content, vc.chunk_metadata, vc.embedding
                    FROM public.vector_chunks vc
                    JOIN public.documents d ON vc.document_id = d.id
                    WHERE d.namespace = ? AND d.is_latest = TRUE
                """
                params.append(namespace)
                
                if owner_type and owner_id:
                    sql += " AND vc.owner_type = ? AND vc.owner_id = ?"
                    params.extend([owner_type, owner_id])
                
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                
                candidates = []
                for row in rows:
                    r = row if isinstance(row, dict) else dict(zip([col[0] for col in cursor.description], row))
                    meta = r["chunk_metadata"]
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                    
                    # Apply local JSON filters in Python if metadata_filters specified
                    if metadata_filters:
                        matches = True
                        for k, v in metadata_filters.items():
                            if meta.get(k) != v:
                                matches = False
                                break
                        if not matches:
                            continue
                            
                    emb_str = r["embedding"]
                    if not emb_str:
                        continue
                    emb_vec = json.loads(emb_str)
                    candidates.append((r, emb_vec))
                
                # Compute Cosine Similarity
                def cosine_similarity(v1, v2):
                    dot = sum(x*y for x, y in zip(v1, v2))
                    mag1 = sum(x*x for x in v1) ** 0.5
                    mag2 = sum(x*x for x in v2) ** 0.5
                    if mag1 == 0.0 or mag2 == 0.0:
                        return 0.0
                    return dot / (mag1 * mag2)
                
                evaluated = []
                for r, emb in candidates:
                    sim = cosine_similarity(query_embedding, emb)
                    if sim < score_threshold:
                        continue
                    evaluated.append(ChunkResultDTO(
                        id=r["id"],
                        document_id=r["document_id"],
                        chunk_index=int(r["chunk_index"]),
                        content=r["content"],
                        chunk_metadata=r["chunk_metadata"] if isinstance(r["chunk_metadata"], dict) else json.loads(r["chunk_metadata"]),
                        score=sim,
                        distance=1.0 - sim
                    ))
                
                # Sort descending and apply limit
                evaluated.sort(key=lambda x: x.score, reverse=True)
                return evaluated[:limit]
        finally:
            conn.close()
