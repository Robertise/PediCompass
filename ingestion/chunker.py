"""
chunker.py — Semantic chunker for PediCompass ingestion pipeline.

Splits parsed document sections into chunks of 300–500 tokens with a
50-token overlap. The primary split strategy is section-boundary-aware:
each ParsedSection is treated as a logical unit first, then subdivided if
it exceeds the target size.

Design decisions:
- Token counting uses a simple whitespace-split approximation (1 token ≈
  0.75 words by GPT convention; for sentence-transformers with a ~512-token
  limit, the exact count matters less than staying well below the limit).
- Section headers are prepended to every sub-chunk generated from that
  section so each chunk is self-contained.
- Table sections are never split — they are kept intact as a single chunk
  even if they exceed MAX_TOKENS. Splitting a table mid-row destroys its
  meaning.
- Overlap is implemented by including the last OVERLAP_TOKENS worth of text
  from the previous sub-chunk at the start of the next one.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from parser import ParsedDocument, ParsedSection

logger = logging.getLogger(__name__)

# ── Tunable parameters ────────────────────────────────────────────────────────

TARGET_TOKENS: int = 400    # Target chunk size (tokens)
MAX_TOKENS: int = 500       # Hard upper limit before forced split
MIN_TOKENS: int = 50        # Chunks smaller than this are merged with the next
OVERLAP_TOKENS: int = 50    # Token overlap between consecutive sub-chunks

# Rough words-to-tokens ratio for all-MiniLM-L6-v2 (WordPiece vocabulary).
# MiniLM's max sequence length is 512 tokens; at ~1.3 tokens/word on medical
# text, 400 "tokens" here ≈ ~308 words — safely inside the 512-token window.
WORDS_PER_TOKEN: float = 0.75   # i.e., 1 word ≈ 1/0.75 ≈ 1.33 tokens


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    """
    A single text chunk ready for embedding.

    Attributes:
        text:           The chunk content (may include a prepended header).
        section_title:  The header of the source section, or empty string.
        chunk_index:    0-based index within the document.
        page_start:     First PDF page this chunk draws from.
        page_end:       Last PDF page this chunk draws from.
        token_estimate: Approximate token count of `text`.
        is_table:       True when this chunk originated from a table block.
    """
    text: str
    section_title: str
    chunk_index: int
    page_start: int
    page_end: int
    token_estimate: int
    is_table: bool = False


# ── Chunker implementation ────────────────────────────────────────────────────

class SemanticChunker:
    """
    Splits a ParsedDocument into a list of Chunk objects.

    Usage::

        chunker = SemanticChunker()
        chunks = chunker.chunk(parsed_doc)
    """

    def __init__(
        self,
        target_tokens: int = TARGET_TOKENS,
        max_tokens: int = MAX_TOKENS,
        min_tokens: int = MIN_TOKENS,
        overlap_tokens: int = OVERLAP_TOKENS,
    ) -> None:
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens
        self.overlap_tokens = overlap_tokens

    # ── Public API ─────────────────────────────────────────────────────────

    def chunk(self, doc: ParsedDocument) -> list[Chunk]:
        """
        Split the entire parsed document into chunks.

        Args:
            doc: A ParsedDocument returned by PDFParser.parse().

        Returns:
            Ordered list of Chunk objects (index 0 is the first chunk).
        """
        raw_chunks: list[Chunk] = []
        chunk_index = 0

        for section in doc.sections:
            section_chunks = self._chunk_section(section, chunk_index)
            raw_chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        # Post-process: merge orphan chunks that are too small
        merged = self._merge_small_chunks(raw_chunks)

        # Re-index after merge
        for i, ch in enumerate(merged):
            ch.chunk_index = i

        logger.info(
            "Produced %d chunks from %d sections",
            len(merged),
            len(doc.sections),
        )
        return merged

    # ── Private helpers ────────────────────────────────────────────────────

    def _chunk_section(self, section: ParsedSection, start_index: int) -> list[Chunk]:
        """Split a single ParsedSection into one or more Chunks."""
        text = section.text.strip()
        if not text:
            return []

        title = section.title.strip()

        # Tables: always one chunk, never split
        if section.is_table:
            return [Chunk(
                text=self._prepend_header(title, text),
                section_title=title,
                chunk_index=start_index,
                page_start=section.page_start,
                page_end=section.page_end,
                token_estimate=self._count_tokens(text),
                is_table=True,
            )]

        # Estimate tokens
        total_tokens = self._count_tokens(text)

        # If the section fits in one chunk, return it directly
        if total_tokens <= self.max_tokens:
            return [Chunk(
                text=self._prepend_header(title, text),
                section_title=title,
                chunk_index=start_index,
                page_start=section.page_start,
                page_end=section.page_end,
                token_estimate=total_tokens,
            )]

        # Otherwise split into sub-chunks at sentence boundaries with overlap
        return self._split_with_overlap(section, title, start_index)

    def _split_with_overlap(
        self,
        section: ParsedSection,
        title: str,
        start_index: int,
    ) -> list[Chunk]:
        """
        Split a long section into overlapping sub-chunks.

        Strategy:
        1. Split text into sentences.
        2. Greedily accumulate sentences until we hit TARGET_TOKENS.
        3. Start the next chunk by backtracking OVERLAP_TOKENS worth of text.
        """
        sentences = self._split_sentences(section.text)
        if not sentences:
            return []

        chunks: list[Chunk] = []
        i = 0  # sentence pointer

        while i < len(sentences):
            # Build chunk from sentence i onwards
            accumulated: list[str] = []
            token_count = 0

            j = i
            while j < len(sentences):
                sent = sentences[j]
                sent_tokens = self._count_tokens(sent)

                if token_count + sent_tokens > self.target_tokens and accumulated:
                    break

                accumulated.append(sent)
                token_count += sent_tokens
                j += 1

            if not accumulated:
                # Edge case: single sentence exceeds target — include it anyway
                accumulated = [sentences[i]]
                token_count = self._count_tokens(sentences[i])
                j = i + 1

            chunk_text = " ".join(accumulated)
            full_text = self._prepend_header(title, chunk_text)

            chunks.append(Chunk(
                text=full_text,
                section_title=title,
                chunk_index=start_index + len(chunks),
                page_start=section.page_start,
                page_end=section.page_end,
                token_estimate=self._count_tokens(full_text),
            ))

            # Advance pointer, backing up by OVERLAP_TOKENS worth of sentences
            overlap_words = int(self.overlap_tokens * WORDS_PER_TOKEN)
            backed_words = 0
            back_j = j - 1
            while back_j > i and backed_words < overlap_words:
                backed_words += len(sentences[back_j].split())
                back_j -= 1

            i = max(back_j + 1, i + 1)  # always advance at least 1

        return chunks

    # ── Post-processing ────────────────────────────────────────────────────

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Merge consecutive chunks that are below MIN_TOKENS into their successor.

        A chunk is considered a "runt" when it has too little content to be
        useful on its own (e.g., a one-sentence trailing section). Runts are
        prepended to the next chunk. If the last chunk is a runt, it is
        appended to the previous one instead.
        """
        if not chunks:
            return chunks

        merged: list[Chunk] = []
        pending: Optional[Chunk] = None

        for chunk in chunks:
            if pending is not None:
                # Merge pending into current
                combined_text = pending.text.rstrip() + "\n\n" + chunk.text.lstrip()
                chunk = Chunk(
                    text=combined_text,
                    section_title=pending.section_title or chunk.section_title,
                    chunk_index=chunk.chunk_index,
                    page_start=min(pending.page_start, chunk.page_start),
                    page_end=max(pending.page_end, chunk.page_end),
                    token_estimate=self._count_tokens(combined_text),
                    is_table=pending.is_table or chunk.is_table,
                )
                pending = None

            if chunk.token_estimate < self.min_tokens and not chunk.is_table:
                pending = chunk  # hold and merge with next
            else:
                merged.append(chunk)

        # If last chunk was a runt, append to previous
        if pending is not None:
            if merged:
                last = merged[-1]
                combined_text = last.text.rstrip() + "\n\n" + pending.text.lstrip()
                merged[-1] = Chunk(
                    text=combined_text,
                    section_title=last.section_title,
                    chunk_index=last.chunk_index,
                    page_start=min(last.page_start, pending.page_start),
                    page_end=max(last.page_end, pending.page_end),
                    token_estimate=self._count_tokens(combined_text),
                    is_table=last.is_table or pending.is_table,
                )
            else:
                # Document had only one tiny chunk — keep it
                merged.append(pending)

        return merged

    # ── Utility ────────────────────────────────────────────────────────────

    @staticmethod
    def _count_tokens(text: str) -> int:
        """
        Approximate token count via whitespace word splitting.

        MiniLM uses WordPiece; medical text tends to over-tokenise (~1.3–1.5
        tokens per word). Using 1/0.75 ≈ 1.33 as the multiplier gives a
        conservative upper-bound that keeps chunks inside MiniLM's 512-token
        context window.
        """
        word_count = len(text.split())
        return int(word_count / WORDS_PER_TOKEN)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        Split text into sentences using punctuation heuristics.

        Handles:
        - Standard sentence terminators: . ! ?
        - Bullet-point lines (lines starting with •, -, *, numbers)
        - Newline-delimited paragraphs
        """
        # First split on double newlines (paragraph breaks)
        paragraphs = re.split(r"\n\n+", text)
        sentences: list[str] = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Split bullet lists by line
            if re.match(r"^[\s]*[•\-\*\d]+[\.\)]\s", para):
                lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
                sentences.extend(lines)
                continue

            # Standard sentence splitting
            raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'\(\[])", para)
            sentences.extend(s.strip() for s in raw if s.strip())

        return sentences

    @staticmethod
    def _prepend_header(title: str, text: str) -> str:
        """
        Prepend the section title to the chunk text.

        Avoids duplication when the title already appears at the start of the
        text (common when a section has a single long paragraph).
        """
        if not title or title == "[TABLE]":
            return text
        if text.startswith(title):
            return text
        return f"{title}\n\n{text}"
