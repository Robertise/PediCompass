"""
run_ingestion.py — CLI entry point for PediCompass ingestion pipeline.

Usage::

    # Full ingest
    python run_ingestion.py --file data/nice_cg160.pdf --source NICE

    # Dry run (parse + chunk only, no writes to Qdrant or DynamoDB)
    python run_ingestion.py --file data/nice_cg160.pdf --source NICE --dry-run

    # Skip contextual retrieval (faster, useful for quick testing)
    python run_ingestion.py --file data/nice_cg160.pdf --source NICE --skip-context

Pipeline stages (in order):
    1. Parse PDF (PyMuPDF) → ParsedDocument
    2. Semantic chunking → list[Chunk]
    3. Metadata tagging  → list[ChunkMetadata]
    4. Contextual Retrieval (Bedrock Haiku) → enriched text per chunk
    5. Embedding (common/embedder.py) → 384-dim vectors
    6. Upsert to Qdrant
    7. Update pedicompass_documents in DynamoDB

Exit codes:
    0 — success
    1 — argument / configuration error
    2 — runtime error (partial success possible; check logs)
"""

# ── Path setup (must be first) ────────────────────────────────────────────────
import os
import sys

# Add the `code/` directory to sys.path so `from common.embedder import ...` works
# regardless of where the script is invoked from.
_INGESTION_DIR = os.path.dirname(os.path.abspath(__file__))
_CODE_DIR = os.path.dirname(_INGESTION_DIR)
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)

# ── Standard library ──────────────────────────────────────────────────────────
import argparse
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Third-party ───────────────────────────────────────────────────────────────
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv
from tqdm import tqdm

# ── Qdrant ────────────────────────────────────────────────────────────────────
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

# ── Local pipeline modules ────────────────────────────────────────────────────
from parser import PDFParser, ParsedDocument
from chunker import SemanticChunker, Chunk
from metadata_tagger import MetadataTagger, ChunkMetadata
from contextual_retrieval import ContextualRetrieval

# ── Common embedder (via sys.path set above) ──────────────────────────────────
from common.embedder import embed_batch, EMBEDDING_DIM

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_ingestion")

# ── Constants ─────────────────────────────────────────────────────────────────

VALID_SOURCES = {"NICE", "WHO", "CDC", "AAP"}
DYNAMODB_DOCUMENTS_TABLE = "pedicompass_documents"
QDRANT_UPSERT_BATCH_SIZE = 64   # vectors per Qdrant upsert call
EMBED_BATCH_SIZE = 32           # texts per embedding forward pass


# ═════════════════════════════════════════════════════════════════════════════
# CLI argument parsing
# ═════════════════════════════════════════════════════════════════════════════

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_ingestion",
        description="Ingest a pediatric guideline PDF into the PediCompass vector database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_ingestion.py --file data/nice_cg160.pdf --source NICE
  python run_ingestion.py --file data/who_imci.pdf --source WHO --dry-run
  python run_ingestion.py --file data/aap_fever.pdf --source AAP --skip-context
        """,
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        type=Path,
        help="Path to the PDF file to ingest (absolute or relative to CWD).",
    )
    parser.add_argument(
        "--source", "-s",
        required=True,
        choices=list(VALID_SOURCES) + [s.lower() for s in VALID_SOURCES],
        help="Source authority: NICE | WHO | CDC | AAP (case-insensitive).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help=(
            "Parse and chunk the PDF but do NOT write to Qdrant or DynamoDB. "
            "Prints chunk statistics to stdout."
        ),
    )
    parser.add_argument(
        "--skip-context",
        action="store_true",
        default=False,
        help=(
            "Skip the Bedrock Contextual Retrieval step. "
            "Useful for rapid testing or when Bedrock credentials are unavailable."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Path to a .env file. Defaults to code/.env relative to this script.",
    )
    parser.add_argument(
        "--qdrant-host",
        default=None,
        help="Qdrant host (overrides QDRANT_HOST env var). Default: localhost",
    )
    parser.add_argument(
        "--qdrant-port",
        type=int,
        default=None,
        help="Qdrant port (overrides QDRANT_PORT env var). Default: 6333",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Qdrant collection name (overrides QDRANT_COLLECTION env var).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    return parser


# ═════════════════════════════════════════════════════════════════════════════
# Qdrant helpers
# ═════════════════════════════════════════════════════════════════════════════

def get_or_create_qdrant_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = EMBEDDING_DIM,
) -> None:
    """
    Ensure the Qdrant collection exists with the correct configuration.

    Creates the collection if it doesn't exist. If it already exists,
    validates the vector dimension. Also enables payload indexing on
    `age_group` for fast filtering.
    """
    try:
        info = client.get_collection(collection_name)
        existing_dim = info.config.params.vectors.size
        if existing_dim != vector_size:
            raise RuntimeError(
                f"Collection '{collection_name}' already exists with vector size "
                f"{existing_dim}, but embedder produces {vector_size}-dim vectors. "
                f"Drop the collection manually and re-run if this is intentional."
            )
        logger.info(
            "Collection '%s' already exists (%d dims) — reusing.",
            collection_name, existing_dim,
        )
    except UnexpectedResponse as exc:
        if exc.status_code == 404:
            logger.info("Creating Qdrant collection '%s' (%d dims)...", collection_name, vector_size)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
            # Enable payload index on age_group for fast pre-filter
            client.create_payload_index(
                collection_name=collection_name,
                field_name="age_group",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )
            logger.info("Collection created with age_group keyword index.")
        else:
            raise


def upsert_chunks_to_qdrant(
    client: QdrantClient,
    collection_name: str,
    doc_id: str,
    chunks: list[Chunk],
    enriched_texts: list[str],
    metadatas: list[ChunkMetadata],
    vectors: list[list[float]],
) -> list[str]:
    """
    Upsert all chunks into Qdrant in batches.

    Args:
        client:          Qdrant client.
        collection_name: Target collection.
        doc_id:          UUID for this document (used in point ID generation).
        chunks:          Original chunk objects (for index / page info).
        enriched_texts:  Contextually enriched text strings (what gets stored).
        metadatas:       Metadata objects, one per chunk.
        vectors:         Embedding vectors, one per chunk.

    Returns:
        List of Qdrant point IDs (UUID strings) for all successfully upserted chunks.
    """
    assert len(chunks) == len(enriched_texts) == len(metadatas) == len(vectors), (
        "Mismatched list lengths in upsert_chunks_to_qdrant"
    )

    point_ids: list[str] = []
    failed_indices: list[int] = []

    # Build all points first
    points: list[qdrant_models.PointStruct] = []
    for i, (chunk, text, meta, vec) in enumerate(zip(chunks, enriched_texts, metadatas, vectors)):
        # Deterministic point ID from doc_id + chunk_index
        point_id = str(uuid.uuid5(uuid.UUID(doc_id), f"chunk_{chunk.chunk_index}"))
        payload = {
            "text": text,
            "age_group": meta.age_group,
            "urgency_relevance": meta.urgency_relevance,
            "source_authority": meta.source_authority,
            "content_type": meta.content_type,
            "publication_date": meta.publication_date,
            "source_doc": meta.source_doc,
            "chunk_index": chunk.chunk_index,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "section_title": chunk.section_title,
            "doc_id": doc_id,
        }
        points.append(qdrant_models.PointStruct(
            id=point_id,
            vector=vec,
            payload=payload,
        ))
        point_ids.append(point_id)

    # Upsert in batches
    total_batches = (len(points) + QDRANT_UPSERT_BATCH_SIZE - 1) // QDRANT_UPSERT_BATCH_SIZE
    with tqdm(total=len(points), desc="Upserting to Qdrant", unit="chunk") as pbar:
        for batch_start in range(0, len(points), QDRANT_UPSERT_BATCH_SIZE):
            batch = points[batch_start: batch_start + QDRANT_UPSERT_BATCH_SIZE]
            batch_indices = list(range(batch_start, batch_start + len(batch)))
            try:
                client.upsert(
                    collection_name=collection_name,
                    points=batch,
                    wait=True,
                )
                pbar.update(len(batch))
            except Exception as exc:
                logger.warning(
                    "Failed to upsert batch [%d:%d]: %s — skipping these chunks.",
                    batch_start, batch_start + len(batch), exc,
                )
                for idx in batch_indices:
                    failed_indices.append(idx)
                pbar.update(len(batch))

    if failed_indices:
        logger.warning(
            "%d chunk(s) failed to upsert: indices %s",
            len(failed_indices), failed_indices,
        )
        # Remove failed point IDs from the return list
        successful_ids = [pid for i, pid in enumerate(point_ids) if i not in set(failed_indices)]
        return successful_ids

    logger.info("Successfully upserted %d chunks to Qdrant.", len(point_ids))
    return point_ids


# ═════════════════════════════════════════════════════════════════════════════
# DynamoDB helpers
# ═════════════════════════════════════════════════════════════════════════════

def register_document_in_dynamodb(
    dynamodb_resource,
    table_name: str,
    doc_id: str,
    filename: str,
    source_authority: str,
    chunk_count: int,
    qdrant_ids: list[str],
    status: str = "complete",
) -> None:
    """
    Create or update the document registry entry in DynamoDB.

    Table: pedicompass_documents
    PK:    doc_id (UUID string)
    """
    table = dynamodb_resource.Table(table_name)
    now_iso = datetime.now(timezone.utc).isoformat()

    item = {
        "doc_id": doc_id,
        "filename": filename,
        "source_authority": source_authority,
        "upload_date": now_iso,
        "chunk_count": chunk_count,
        "status": status,
        "qdrant_ids": qdrant_ids,
    }

    try:
        table.put_item(Item=item)
        logger.info(
            "DynamoDB: registered doc_id=%s status=%s chunks=%d",
            doc_id, status, chunk_count,
        )
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        logger.error(
            "DynamoDB put_item failed [%s]: %s — document registry NOT updated.",
            error_code, exc,
        )
        raise


def update_document_status(
    dynamodb_resource,
    table_name: str,
    doc_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """Update only the status field of an existing document registry entry."""
    table = dynamodb_resource.Table(table_name)
    update_expr = "SET #s = :status, updated_at = :ts"
    expr_names = {"#s": "status"}
    expr_values: dict = {
        ":status": status,
        ":ts": datetime.now(timezone.utc).isoformat(),
    }
    if error_message:
        update_expr += ", error_message = :err"
        expr_values[":err"] = error_message

    try:
        table.update_item(
            Key={"doc_id": doc_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except ClientError as exc:
        logger.error("Failed to update document status: %s", exc)


# ═════════════════════════════════════════════════════════════════════════════
# Embedding helpers
# ═════════════════════════════════════════════════════════════════════════════

def embed_with_progress(texts: list[str], batch_size: int = EMBED_BATCH_SIZE) -> list[list[float]]:
    """
    Embed texts in batches with a tqdm progress bar.

    Falls back gracefully per-batch: if a batch fails, logs a warning and
    inserts zero vectors for that batch (so downstream can detect failures).
    """
    all_vectors: list[list[float]] = []
    zero_vec = [0.0] * EMBEDDING_DIM

    total_batches = (len(texts) + batch_size - 1) // batch_size

    with tqdm(total=len(texts), desc="Embedding chunks", unit="chunk") as pbar:
        for batch_start in range(0, len(texts), batch_size):
            batch_texts = texts[batch_start: batch_start + batch_size]
            try:
                batch_vectors = embed_batch(batch_texts, batch_size=batch_size)
                all_vectors.extend(batch_vectors)
            except Exception as exc:
                logger.warning(
                    "Embedding failed for batch [%d:%d]: %s — inserting zero vectors.",
                    batch_start, batch_start + len(batch_texts), exc,
                )
                all_vectors.extend([zero_vec] * len(batch_texts))
            pbar.update(len(batch_texts))

    return all_vectors


# ═════════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═════════════════════════════════════════════════════════════════════════════

def run_pipeline(
    pdf_path: Path,
    source: str,
    dry_run: bool,
    skip_context: bool,
    qdrant_host: str,
    qdrant_port: int,
    collection_name: str,
    aws_region: str,
) -> int:
    """
    Execute the full ingestion pipeline.

    Returns:
        0 on success, 2 on partial failure.
    """
    start_time = time.time()
    doc_id = str(uuid.uuid4())
    logger.info("=" * 60)
    logger.info("PediCompass Ingestion Pipeline")
    logger.info("  File   : %s", pdf_path)
    logger.info("  Source : %s", source)
    logger.info("  Doc ID : %s", doc_id)
    logger.info("  Dry run: %s", dry_run)
    logger.info("=" * 60)

    # ── Stage 1: Parse ────────────────────────────────────────────────────
    logger.info("[1/7] Parsing PDF...")
    parser = PDFParser()
    try:
        doc: ParsedDocument = parser.parse(pdf_path)
    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc)
        return 1
    except Exception as exc:
        logger.error("PDF parsing failed: %s", exc)
        return 2

    logger.info(
        "  → Parsed %d sections from %d pages. Title: '%s'",
        len(doc.sections), doc.total_pages, doc.title,
    )

    # ── Stage 2: Chunk ────────────────────────────────────────────────────
    logger.info("[2/7] Chunking sections...")
    chunker = SemanticChunker()
    with tqdm(total=len(doc.sections), desc="Chunking sections", unit="section") as pbar:
        chunks: list[Chunk] = chunker.chunk(doc)
        pbar.update(len(doc.sections))

    if not chunks:
        logger.error("No chunks produced from the document. Aborting.")
        return 2

    logger.info("  → Produced %d chunks.", len(chunks))
    chunk_texts = [c.text for c in chunks]

    # ── Stage 3: Tag metadata ─────────────────────────────────────────────
    logger.info("[3/7] Tagging metadata...")
    tagger = MetadataTagger(pdf_path=str(pdf_path))
    with tqdm(total=len(chunks), desc="Tagging metadata", unit="chunk") as pbar:
        metadatas: list[ChunkMetadata] = []
        for text in chunk_texts:
            metadatas.append(tagger.tag(text, source_override=source))
            pbar.update(1)

    # Print metadata distribution summary
    age_dist: dict = {}
    urgency_dist: dict = {}
    type_dist: dict = {}
    for m in metadatas:
        age_dist[m.age_group] = age_dist.get(m.age_group, 0) + 1
        urgency_dist[m.urgency_relevance] = urgency_dist.get(m.urgency_relevance, 0) + 1
        type_dist[m.content_type] = type_dist.get(m.content_type, 0) + 1

    logger.info("  → Age groups: %s", age_dist)
    logger.info("  → Urgency: %s", urgency_dist)
    logger.info("  → Content types: %s", type_dist)

    # ── Stage 4: Contextual Retrieval ─────────────────────────────────────
    enriched_texts: list[str]
    if skip_context:
        logger.info("[4/7] Skipping Contextual Retrieval (--skip-context).")
        enriched_texts = chunk_texts
    else:
        logger.info("[4/7] Contextual Retrieval via Bedrock Claude Haiku...")
        # Build document summary from title + first non-table section
        first_text = ""
        for s in doc.sections:
            if not s.is_table and s.text.strip():
                first_text = s.text
                break

        doc_summary = ContextualRetrieval.build_doc_summary(
            title=doc.title,
            first_section_text=first_text,
            source_authority=source,
        )

        try:
            cr = ContextualRetrieval(
                doc_summary=doc_summary,
                aws_region=aws_region,
            )
            enriched_texts = cr.enrich_batch(chunk_texts, show_progress=True)
        except ValueError as exc:
            logger.warning(
                "Contextual Retrieval disabled: %s\n"
                "  → Continuing without enrichment (use --skip-context to suppress this warning).",
                exc,
            )
            enriched_texts = chunk_texts
        except Exception as exc:
            logger.warning(
                "Contextual Retrieval failed: %s — falling back to original chunks.",
                exc,
            )
            enriched_texts = chunk_texts

    logger.info("  → %d chunks enriched/prepared.", len(enriched_texts))

    # ── Dry run: print statistics and exit ───────────────────────────────
    if dry_run:
        logger.info("[DRY RUN] Skipping embed, Qdrant upsert, and DynamoDB update.")
        print("\n" + "=" * 60)
        print("DRY RUN RESULTS")
        print("=" * 60)
        print(f"  PDF             : {pdf_path}")
        print(f"  Source          : {source}")
        print(f"  Pages           : {doc.total_pages}")
        print(f"  Sections parsed : {len(doc.sections)}")
        print(f"  Chunks produced : {len(chunks)}")
        print(f"  Age groups      : {json.dumps(age_dist)}")
        print(f"  Urgency dist.   : {json.dumps(urgency_dist)}")
        print(f"  Content types   : {json.dumps(type_dist)}")
        print("\n  Sample chunks (first 3):")
        for ch in chunks[:3]:
            preview = ch.text[:200].replace("\n", " ")
            print(f"  [{ch.chunk_index}] ({ch.token_estimate} toks) {preview}...")
        print("=" * 60)
        elapsed = time.time() - start_time
        logger.info("Dry run complete in %.1f seconds.", elapsed)
        return 0

    # ── Stage 5: Embed ────────────────────────────────────────────────────
    logger.info("[5/7] Embedding %d chunks...", len(enriched_texts))
    vectors = embed_with_progress(enriched_texts, batch_size=EMBED_BATCH_SIZE)
    logger.info("  → Embedded %d vectors (%d dims).", len(vectors), EMBEDDING_DIM)

    # ── Stage 6: Upsert to Qdrant ─────────────────────────────────────────
    logger.info("[6/7] Upserting to Qdrant at %s:%d...", qdrant_host, qdrant_port)
    try:
        qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        get_or_create_qdrant_collection(qdrant, collection_name)
        qdrant_ids = upsert_chunks_to_qdrant(
            client=qdrant,
            collection_name=collection_name,
            doc_id=doc_id,
            chunks=chunks,
            enriched_texts=enriched_texts,
            metadatas=metadatas,
            vectors=vectors,
        )
    except Exception as exc:
        logger.error("Qdrant upsert failed fatally: %s", exc)
        return 2

    logger.info("  → %d / %d points stored in Qdrant.", len(qdrant_ids), len(chunks))

    # ── Stage 7: Update DynamoDB ──────────────────────────────────────────
    logger.info("[7/7] Updating DynamoDB document registry...")
    dynamodb_table_prefix = os.environ.get("DYNAMODB_TABLE_PREFIX", "pedicompass_")
    table_name = f"{dynamodb_table_prefix}documents"

    try:
        dynamo = boto3.resource("dynamodb", region_name=aws_region)
        register_document_in_dynamodb(
            dynamodb_resource=dynamo,
            table_name=table_name,
            doc_id=doc_id,
            filename=pdf_path.name,
            source_authority=source,
            chunk_count=len(qdrant_ids),
            qdrant_ids=qdrant_ids,
            status="complete",
        )
    except NoCredentialsError:
        logger.error(
            "AWS credentials not found. Configure ~/.aws/credentials or set "
            "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY env vars."
        )
        return 2
    except Exception as exc:
        logger.error("DynamoDB update failed: %s", exc)
        return 2

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Ingestion complete in %.1f seconds.", elapsed)
    logger.info("  Doc ID      : %s", doc_id)
    logger.info("  Chunks total: %d", len(chunks))
    logger.info("  Qdrant pts  : %d", len(qdrant_ids))
    logger.info("  Collection  : %s", collection_name)
    logger.info("  DynamoDB    : %s", table_name)
    logger.info("=" * 60)
    return 0


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser_cli = build_arg_parser()
    args = parser_cli.parse_args()

    # Configure log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── Load environment variables ─────────────────────────────────────────
    env_file = args.env_file
    if env_file is None:
        # Default: code/.env (one level up from this script)
        env_file = Path(_CODE_DIR) / ".env"

    if env_file.exists():
        load_dotenv(env_file)
        logger.debug("Loaded .env from %s", env_file)
    else:
        logger.debug("No .env file at %s — relying on environment variables.", env_file)

    # ── Resolve config values (CLI args override env vars) ────────────────
    source = args.source.upper()

    qdrant_host = args.qdrant_host or os.environ.get("QDRANT_HOST", "localhost")
    qdrant_port = args.qdrant_port or int(os.environ.get("QDRANT_PORT", "6333"))
    collection_name = args.collection or os.environ.get("QDRANT_COLLECTION", "pedicompass_kb")
    aws_region = os.environ.get("AWS_REGION", "ap-southeast-1")

    # ── Validate PDF path ──────────────────────────────────────────────────
    pdf_path: Path = args.file
    if not pdf_path.is_absolute():
        # Resolve relative to CWD
        pdf_path = Path.cwd() / pdf_path

    if not pdf_path.exists():
        logger.error("PDF file not found: %s", pdf_path)
        sys.exit(1)

    if pdf_path.suffix.lower() != ".pdf":
        logger.error("File does not have a .pdf extension: %s", pdf_path)
        sys.exit(1)

    # ── Run pipeline ───────────────────────────────────────────────────────
    exit_code = run_pipeline(
        pdf_path=pdf_path,
        source=source,
        dry_run=args.dry_run,
        skip_context=args.skip_context,
        qdrant_host=qdrant_host,
        qdrant_port=qdrant_port,
        collection_name=collection_name,
        aws_region=aws_region,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
