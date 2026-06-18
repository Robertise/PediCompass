"""
Shared embedding module for PediCompass.

Used by BOTH backend (query embedding) and ingestion pipeline (document embedding).
Having a single module with fixed config prevents embedding space mismatch —
if backend uses normalize_embeddings=True and ingestion uses False, all cosine
similarity scores will be wrong in a way that's very hard to debug.

Config is intentionally hard-coded here, not configurable via env, to prevent
accidental divergence between ingest and query time.
"""

from functools import lru_cache
from typing import Union

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
_NORMALIZE = True  # Fixed: both ingest and query must use the same value


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """
    Load the embedding model once and cache it for the process lifetime.
    lru_cache(maxsize=1) acts as a singleton — subsequent calls return the
    already-loaded model without re-initialising.
    """
    return SentenceTransformer(MODEL_NAME)


def embed(text: str) -> list[float]:
    """
    Embed a single text string into a 384-dimensional vector.

    Args:
        text: Input text to embed.

    Returns:
        List of 384 floats (L2-normalised).
    """
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=_NORMALIZE)
    return vector.tolist()


def embed_batch(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Embed a list of texts efficiently in batches.

    Args:
        texts: List of input texts.
        batch_size: Number of texts to embed per forward pass.

    Returns:
        List of embedding vectors, one per input text.
    """
    model = _get_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=_NORMALIZE,
        batch_size=batch_size,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]
