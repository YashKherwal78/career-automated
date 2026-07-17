import os
import pytest
from src.ai.vector.namespaces import VectorNamespaces
from src.ai.vector.types import DocumentDTO, ChunkDTO
from src.ai.vector.repository import DocumentRepository, VectorRepository
from src.ai.vector.ingestion import DocumentIngestionService
from src.ai.vector.retrieval import VectorRetrievalService
from src.ai.embeddings.provider import get_embedding_provider
from src.api.db import get_connection, is_postgres



def test_embedding_providers():
    # Test Mock Provider
    mock_provider = get_embedding_provider("mock", "any-model", dimensions=1536)
    emb = mock_provider.embed_text("Hello, world!")
    assert len(emb) == 1536
    # Verify mock vectors are normalized (magnitude is close to 1)
    magnitude = sum(x*x for x in emb) ** 0.5
    assert abs(magnitude - 1.0) < 1e-5

    batch_embs = mock_provider.embed_batch(["text 1", "text 2"])
    assert len(batch_embs) == 2
    assert len(batch_embs[0]) == 1536


def test_document_and_chunk_lifecycle():
    import time
    namespace = VectorNamespaces.RESUME_KB.value
    source_type = "test_resume"
    source_id = f"doc_{int(time.time())}"
    owner_type = "user"
    owner_id = f"owner_{int(time.time())}"
    content = "This is a resume bullet point detailing AI engineering and pgvector search systems."

    # Force using the mock provider in settings/environment for tests to run offline
    os.environ["VECTOR_PROVIDER"] = "mock"

    # Pre-clean existing records
    DocumentRepository.delete_by_source(namespace, source_type, source_id)

    # Ingest document version 1
    doc_v1 = DocumentIngestionService.ingest_document(
        namespace=namespace,
        source_type=source_type,
        source_id=source_id,
        content=content,
        owner_type=owner_type,
        owner_id=owner_id,
        doc_metadata={"language": "en"}
    )
    
    assert doc_v1.id is not None
    assert doc_v1.version == 1
    assert doc_v1.is_latest is True
    assert doc_v1.status == "READY"

    # Verify parent document can be retrieved
    db_doc = DocumentRepository.get_by_source(namespace, source_type, source_id)
    assert db_doc is not None
    assert str(db_doc.id) == str(doc_v1.id)
    assert db_doc.checksum is not None

    # Ingest updated document version 2
    updated_content = "This is a revised resume bullet detailing pgvector index tuning and OpenAI embeddings."
    doc_v2 = DocumentIngestionService.ingest_document(
        namespace=namespace,
        source_type=source_type,
        source_id=source_id,
        content=updated_content,
        owner_type=owner_type,
        owner_id=owner_id,
        doc_metadata={"language": "en"}
    )

    assert doc_v2.id is not None
    assert doc_v2.version == 2
    assert doc_v2.is_latest is True


    # Retrieve semantic match
    results = VectorRetrievalService.retrieve(
        query="pgvector indexes and engineering",
        namespace=namespace,
        owner_type=owner_type,
        owner_id=owner_id,
        limit=5,
        score_threshold=-1.0
    )

    assert len(results) > 0
    match = results[0]
    assert str(match.document_id) == str(doc_v2.id)
    assert match.score > 0.0
    assert match.distance == 1.0 - match.score
    assert "revised resume" in match.content

    # Retrieve with non-matching owner filters and ensure it returns empty
    empty_results = VectorRetrievalService.retrieve(
        query="pgvector",
        namespace=namespace,
        owner_type=owner_type,
        owner_id="non_existent_owner",
        limit=5
    )
    assert len(empty_results) == 0

    # Retrieve with matching metadata filters
    matching_metadata = VectorRetrievalService.retrieve(
        query="pgvector",
        namespace=namespace,
        owner_type=owner_type,
        owner_id=owner_id,
        score_threshold=-1.0,
        metadata_filters={"language": "en"}
    )
    assert len(matching_metadata) > 0

    # Clean up test records
    DocumentRepository.delete_by_source(namespace, source_type, source_id)
    
    # Verify cleanup succeeded
    cleared_doc = DocumentRepository.get_by_source(namespace, source_type, source_id)
    assert cleared_doc is None
