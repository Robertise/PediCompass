"""
parser.py — PDF Parser for PediCompass ingestion pipeline.

Uses PyMuPDF (fitz) to extract text from pediatric guideline PDFs while
preserving structural information (section headers, tables) that is critical
for accurate downstream chunking.

Design decisions:
- Section headers are detected by font-size heuristic: text blocks whose
  dominant font size is ≥ 1.2× the body-text median are tagged as headers.
- Tables are extracted as pipe-delimited markdown text so they survive the
  chunking step as a single logical unit.
- Pages with fewer than 20 characters of text after stripping are skipped
  (covers cover pages, blank pages, image-only pages).
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    """A single logical section extracted from the PDF."""

    title: str                    # Section header text (empty string for body-only blocks)
    text: str                     # Combined text of the section
    page_start: int               # 1-indexed first page this section appears on
    page_end: int                 # 1-indexed last page this section appears on
    is_table: bool = False        # True when this section originated from a table block


@dataclass
class ParsedDocument:
    """Full parse result for a single PDF file."""

    source_path: str
    title: str                          # Best-guess document title (first large text on page 1)
    total_pages: int
    sections: list[ParsedSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Return all section text concatenated (used for document-level context)."""
        return "\n\n".join(s.text for s in self.sections if s.text.strip())


class PDFParser:
    """
    Extracts structured text from a PDF using PyMuPDF.

    Each call to `parse()` returns a `ParsedDocument` containing a list of
    `ParsedSection` objects ordered by their appearance in the document.
    """

    # A block is treated as a section header when its dominant font size
    # exceeds this multiple of the median body font size.
    HEADER_FONT_RATIO: float = 1.2

    # Pages with fewer characters than this are skipped entirely.
    MIN_PAGE_CHARS: int = 20

    # Tables with fewer cells than this are rendered as plain text, not
    # pipe-delimited markdown.
    MIN_TABLE_CELLS: int = 4

    def __init__(self) -> None:
        try:
            import fitz  # PyMuPDF
            self._fitz = fitz
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for the PDF parser. "
                "Install it with: pip install pymupdf"
            ) from exc

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self, pdf_path: str | Path) -> ParsedDocument:
        """
        Parse a PDF file and return a structured ParsedDocument.

        Args:
            pdf_path: Absolute or relative path to the PDF file.

        Returns:
            ParsedDocument with extracted sections.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If PyMuPDF cannot open the file.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info("Opening PDF: %s", pdf_path)
        doc = self._fitz.open(str(pdf_path))

        try:
            total_pages = doc.page_count
            logger.info("Total pages: %d", total_pages)

            # ── Pass 1: collect all text blocks with font sizes ────────────
            all_blocks = self._collect_blocks(doc)

            # ── Pass 2: determine median body font size ────────────────────
            median_font_size = self._compute_median_font_size(all_blocks)
            header_threshold = median_font_size * self.HEADER_FONT_RATIO
            logger.debug(
                "Median font size: %.1f px → header threshold: %.1f px",
                median_font_size,
                header_threshold,
            )

            # ── Pass 3: extract document title (largest text, page 1) ─────
            doc_title = self._extract_title(doc, all_blocks)

            # ── Pass 4: group blocks into sections ────────────────────────
            sections = self._group_into_sections(
                doc, all_blocks, header_threshold
            )

            # ── Build document metadata ────────────────────────────────────
            pdf_meta = doc.metadata or {}
            metadata = {
                "pdf_title": pdf_meta.get("title", ""),
                "pdf_author": pdf_meta.get("author", ""),
                "pdf_subject": pdf_meta.get("subject", ""),
                "pdf_creation_date": pdf_meta.get("creationDate", ""),
            }

            parsed = ParsedDocument(
                source_path=str(pdf_path),
                title=doc_title,
                total_pages=total_pages,
                sections=sections,
                metadata=metadata,
            )

            logger.info(
                "Parsed %d sections from %d pages",
                len(sections),
                total_pages,
            )
            return parsed

        finally:
            doc.close()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _collect_blocks(self, doc) -> list[dict]:
        """
        Iterate all pages and collect text blocks with font metadata.

        Each block dict contains:
            page (int), bbox (tuple), text (str), font_size (float), block_type (str)
        """
        blocks = []
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            if len(page_text.strip()) < self.MIN_PAGE_CHARS:
                logger.debug("Skipping sparse page %d", page_num)
                continue

            # Extract detailed dict-based blocks for font size info
            raw_dict = page.get_text("dict", flags=self._fitz.TEXT_PRESERVE_WHITESPACE)
            for block in raw_dict.get("blocks", []):
                block_type = block.get("type", -1)

                # Type 0 = text block
                if block_type == 0:
                    lines = block.get("lines", [])
                    if not lines:
                        continue

                    # Collect all spans to determine dominant font size and text
                    all_text_parts = []
                    font_sizes = []
                    for line in lines:
                        for span in line.get("spans", []):
                            span_text = span.get("text", "").strip()
                            if span_text:
                                all_text_parts.append(span_text)
                                font_sizes.append(span.get("size", 10.0))

                    if not all_text_parts:
                        continue

                    block_text = " ".join(all_text_parts)
                    dominant_size = max(font_sizes) if font_sizes else 10.0

                    blocks.append({
                        "page": page_num,
                        "bbox": block.get("bbox", (0, 0, 0, 0)),
                        "text": block_text,
                        "font_size": dominant_size,
                        "block_type": "text",
                    })

                # Type 1 = image block — skip
                # Tables are handled separately below

            # ── Table extraction ──────────────────────────────────────────
            tables = page.find_tables()
            if tables and tables.tables:
                for tbl in tables.tables:
                    md_text = self._table_to_markdown(tbl)
                    if md_text:
                        # Use a very large font size so tables are never
                        # confused with headers during grouping
                        blocks.append({
                            "page": page_num,
                            "bbox": tbl.bbox,
                            "text": md_text,
                            "font_size": 0.0,   # sentinel: tables have no "font size"
                            "block_type": "table",
                        })

        return blocks

    def _table_to_markdown(self, table) -> str:
        """Convert a PyMuPDF Table object to pipe-delimited markdown."""
        try:
            rows = table.extract()
            if not rows:
                return ""

            # Count non-None cells to decide if worth rendering
            cell_count = sum(
                1 for row in rows for cell in row if cell is not None and str(cell).strip()
            )
            if cell_count < self.MIN_TABLE_CELLS:
                return ""

            md_rows = []
            for i, row in enumerate(rows):
                cells = [str(c).replace("|", "\\|").strip() if c else "" for c in row]
                md_rows.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    # Header separator
                    md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")

            return "\n".join(md_rows)
        except Exception as exc:
            logger.warning("Failed to extract table: %s", exc)
            return ""

    def _compute_median_font_size(self, blocks: list[dict]) -> float:
        """Compute the median font size of all text (non-table) blocks."""
        sizes = [b["font_size"] for b in blocks if b["block_type"] == "text"]
        if not sizes:
            return 10.0
        sizes.sort()
        mid = len(sizes) // 2
        return sizes[mid]

    def _extract_title(self, doc, blocks: list[dict]) -> str:
        """
        Extract document title as the largest text block on page 1.
        Falls back to the PDF metadata title, then the filename stem.
        """
        page1_blocks = [b for b in blocks if b["page"] == 1 and b["block_type"] == "text"]
        if page1_blocks:
            largest = max(page1_blocks, key=lambda b: b["font_size"])
            candidate = largest["text"].strip()
            if len(candidate) > 5:  # avoid single-character artefacts
                return candidate

        # Fallback: PDF metadata
        meta = doc.metadata or {}
        pdf_title = meta.get("title", "").strip()
        if pdf_title:
            return pdf_title

        return Path(doc.name).stem

    def _group_into_sections(
        self,
        doc,
        blocks: list[dict],
        header_threshold: float,
    ) -> list[ParsedSection]:
        """
        Walk blocks in order and group them into ParsedSection objects.

        A new section begins whenever a text block's font_size exceeds the
        header_threshold, or whenever a table block is encountered (tables
        always get their own section so the chunker can keep them intact).
        """
        sections: list[ParsedSection] = []
        current_title = ""
        current_parts: list[str] = []
        current_page_start = 1
        current_page = 1

        def flush_current():
            nonlocal current_title, current_parts, current_page_start, current_page
            text = self._clean_text("\n".join(current_parts))
            if text.strip():
                sections.append(ParsedSection(
                    title=current_title,
                    text=text,
                    page_start=current_page_start,
                    page_end=current_page,
                    is_table=False,
                ))
            current_title = ""
            current_parts = []
            current_page_start = current_page

        for block in blocks:
            page = block["page"]
            current_page = page

            if block["block_type"] == "table":
                # Flush any in-progress section first
                flush_current()
                # Table becomes its own section
                sections.append(ParsedSection(
                    title="[TABLE]",
                    text=block["text"],
                    page_start=page,
                    page_end=page,
                    is_table=True,
                ))
                current_page_start = page
                continue

            # Text block
            font_size = block["font_size"]
            text = block["text"].strip()

            if not text:
                continue

            is_header = (
                font_size >= header_threshold
                and len(text) < 200   # headers are typically short
                and not text.endswith(".")   # body sentences end with period
            )

            if is_header:
                # Flush previous section, start new one
                flush_current()
                current_title = text
                current_page_start = page
            else:
                current_parts.append(text)

        # Flush the last in-progress section
        flush_current()

        logger.debug("Grouped into %d sections", len(sections))
        return sections

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Normalise whitespace and remove common PDF extraction artefacts.

        - Collapse runs of whitespace inside lines
        - Remove ligature artefacts (fi, fl, etc.)
        - Strip trailing whitespace per line
        - Collapse 3+ blank lines to 2
        """
        # Ligature replacements (common in pdfminer/PyMuPDF output)
        ligatures = {
            "\ufb01": "fi",
            "\ufb02": "fl",
            "\ufb00": "ff",
            "\ufb03": "ffi",
            "\ufb04": "ffl",
        }
        for lig, replacement in ligatures.items():
            text = text.replace(lig, replacement)

        # Normalise whitespace within lines (keep newlines)
        lines = text.split("\n")
        cleaned = [re.sub(r"[ \t]+", " ", line).rstrip() for line in lines]
        text = "\n".join(cleaned)

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
