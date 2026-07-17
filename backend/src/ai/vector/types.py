from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class DocumentDTO:
    namespace: str
    source_type: str
    source_id: str
    checksum: Optional[str] = None
    id: Optional[str] = None
    version: int = 1
    is_latest: bool = True
    status: str = "PENDING"
    embedding_provider: str = "gemini"
    embedding_model: str = "models/text-embedding-004"
    embedding_dimension: int = 1536
    distance_metric: str = "cosine"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ChunkDTO:
    document_id: str
    owner_type: str
    owner_id: str
    content: str
    chunk_checksum: str
    chunk_index: int = 0
    id: Optional[str] = None
    chunk_metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    embedding_type: str = "semantic"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ChunkResultDTO:
    id: str
    document_id: str
    chunk_index: int
    content: str
    chunk_metadata: Dict[str, Any]
    score: float
    distance: float
