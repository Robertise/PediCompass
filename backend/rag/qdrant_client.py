"""
Qdrant vector database manager.

Responsibilities:
  - Connect to the local Qdrant instance (localhost:6333 by default).
  - Auto-create the knowledge-base collection (384 dims, cosine distance)
    if it does not already exist.
  - Enable payload index on `age_group` for fast metadata filtering.
  - Expose search() and upsert() methods used by the retriever and
    ingestion pipeline.
"""

import logging
from functools import lru_cache
from typing import Optional

from common.embedder import EMBEDDING_DIM
from config import settings
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

logger = logging.getLogger(__name__)


class QdrantManager:
    """
    Thin wrapper around QdrantClient with auto-collection-creation and
    payload indexing.
    """

    def __init__(self, host: str, port: int, collection_name: str) -> None:
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port)
        logger.info("QdrantManager connected to %s:%d", host, port)

    def ensure_collection(self) -> None:
        """
        Create the Qdrant collection if it does not already exist.

        Configuration:
          - Vector size: 384 (all-MiniLM-L6-v2)
          - Distance metric: Cosine
          - Payload index: keyword index on `age_group` for O(1) filtering
        """
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name in existing:
            logger.info("Qdrant collection '%s' already exists.", self.collection_name)
            return

        logger.info("Creating Qdrant collection '%s'…", self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=EMBEDDING_DIM,
                distance=qdrant_models.Distance.COSINE,
            ),
        )

        # Payload index on age_group enables fast metadata pre-filtering
        self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="age_group",
            field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        )
        logger.info("Collection '%s' created with payload index on age_group.", self.collection_name)

    def search(
        self,
        query_vector: list[float],
        age_group_filter: Optional[list[str]] = None,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Search for relevant chunks with optional metadata filter.

        Args:
            query_vector: Embedding of the query (384-dim float list).
            age_group_filter: List of age_group values to include
                              (e.g. ["infant", "all"]). None means no filter.
            top_k: Number of candidates to retrieve before reranking.

        Returns:
            List of chunk dicts with id, score, and payload fields.
        """
        query_filter = None
        if age_group_filter:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="age_group",
                        match=qdrant_models.MatchAny(any=age_group_filter),
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        chunks = []
        for hit in results:
            payload = hit.payload or {}
            chunks.append({
                "chunk_id": str(hit.id),
                "score": hit.score,
                "text": payload.get("text", ""),
                "source_authority": payload.get("source_authority", "Unknown"),
                "age_group": payload.get("age_group", "all"),
                "content_type": payload.get("content_type", ""),
                "doc_id": payload.get("doc_id", ""),
            })
        return chunks

    def upsert(self, points: list[dict]) -> None:
        """
        Upsert vectors and payloads into the collection.

        Each point dict must have: id, vector (list[float]), payload (dict).
        """
        qdrant_points = [
            qdrant_models.PointStruct(
                id=p["id"],
                vector=p["vector"],
                payload=p["payload"],
            )
            for p in points
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points,
        )
        logger.info("Upserted %d points into '%s'.", len(points), self.collection_name)

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all chunks belonging to a document (by doc_id payload)."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="doc_id",
                            match=qdrant_models.MatchValue(value=doc_id),
                        )
                    ]
                )
            ),
        )
        logger.info("Deleted chunks for doc_id=%s from Qdrant.", doc_id)


@lru_cache(maxsize=1)
def get_qdrant_manager() -> QdrantManager:
    """Singleton QdrantManager — instantiated once per process."""
    return QdrantManager(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        collection_name=settings.qdrant_collection,
    )
