"""
metadata_tagger.py — Heuristic metadata tagger for PediCompass ingestion.

Assigns structured metadata to each chunk based on:
  1. Filename patterns → source_authority
  2. Content keyword matching → age_group, urgency_relevance, content_type

All tagging is deterministic / regex-based (no LLM calls here).
The Contextual Retrieval step (contextual_retrieval.py) handles the
semantic enrichment via Bedrock.

Metadata schema (matches Qdrant payload and DynamoDB document registry):
  source_authority:  "NICE" | "WHO" | "CDC" | "AAP" | "UNKNOWN"
  age_group:         "newborn" | "young_infant" | "infant" | "toddler" | "preschool" | "all"
  urgency_relevance: "emergency" | "urgent" | "routine"
  content_type:      "triage_protocol" | "symptom_cluster" | "care_pathway" | "parent_education"
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Type aliases ──────────────────────────────────────────────────────────────

SourceAuthority = str   # "NICE" | "WHO" | "CDC" | "AAP" | "UNKNOWN"
AgeGroup = str          # "newborn" | "young_infant" | "infant" | "toddler" | "preschool" | "all"
UrgencyRelevance = str  # "emergency" | "urgent" | "routine"
ContentType = str       # "triage_protocol" | "symptom_cluster" | "care_pathway" | "parent_education"


# ── Keyword lists ─────────────────────────────────────────────────────────────

# Source authority — matched against the PDF filename (case-insensitive stem).
_SOURCE_FILENAME_PATTERNS: list[tuple[re.Pattern, SourceAuthority]] = [
    (re.compile(r"^nice[_\-]", re.IGNORECASE), "NICE"),
    (re.compile(r"^who[_\-]", re.IGNORECASE), "WHO"),
    (re.compile(r"^cdc[_\-]", re.IGNORECASE), "CDC"),
    (re.compile(r"^(aap|healthychildren)[_\-]", re.IGNORECASE), "AAP"),
]

# Age group — matched against chunk text (lower-cased).
# Entries are evaluated in order; first match wins.
_AGE_KEYWORD_MAP: list[tuple[list[str], AgeGroup]] = [
    # Most specific first — newborn / neonate
    (["neonate", "neonatal", "newborn", "0-28 day", "0–28 day",
      "first 28 day", "first month of life"], "newborn"),
    # Young infant (1–3 months)
    (["young infant", "1-3 month", "1–3 month", "4-12 week", "4–12 week",
      "29-90 day", "29–90 day", "under 3 month", "less than 3 month",
      "less than 90 day", "under 90 day"], "young_infant"),
    # Infant (3–12 months)
    (["3-12 month", "3–12 month", "infant", "6 month", "9 month",
      "91-365 day", "91–365 day"], "infant"),
    # Toddler (1–3 years)
    (["toddler", "1-3 year", "1–3 year", "12-36 month", "12–36 month",
      "18 month", "24 month"], "toddler"),
    # Preschool (3–5 years)
    (["preschool", "pre-school", "3-5 year", "3–5 year",
      "4 year", "5 year", "4-year", "5-year"], "preschool"),
]

# Urgency — matched against chunk text (lower-cased).
# First match wins.
_URGENCY_KEYWORD_MAP: list[tuple[list[str], UrgencyRelevance]] = [
    (["emergency", "immediately", "life-threatening", "life threatening",
      "call 999", "call 911", "call emergency", "ambulance",
      "resuscitat", "critical", "code blue", "do not delay"], "emergency"),
    (["urgent", "seek care", "seek medical", "go to hospital",
      "go to ed", "go to a&e", "within 24 hour", "within 4 hour",
      "same day", "as soon as possible", "asap",
      "do not wait", "without delay"], "urgent"),
]

# Content type — matched against chunk text (lower-cased).
# First match wins.
_CONTENT_TYPE_KEYWORD_MAP: list[tuple[list[str], ContentType]] = [
    (["protocol", "procedure", "algorithm", "decision tree",
      "flowchart", "triage", "clinical pathway step",
      "management protocol", "action plan"], "triage_protocol"),
    (["symptom", "sign", "present", "manifestation", "feature",
      "clinical feature", "finding", "complain",
      "history of", "red flag", "warning sign"], "symptom_cluster"),
    (["pathway", "management", "treatment", "therapy", "intervention",
      "care plan", "care pathway", "guideline recommendation",
      "first-line", "second-line", "antibiotic"], "care_pathway"),
]


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ChunkMetadata:
    """
    Metadata for a single chunk, ready to be stored in Qdrant payload
    and referenced in DynamoDB.
    """
    source_authority: SourceAuthority   # Guideline issuing body
    age_group: AgeGroup                 # Target age range
    urgency_relevance: UrgencyRelevance # Clinical urgency of the content
    content_type: ContentType           # What kind of content this chunk contains
    source_doc: str                     # Filename of the source PDF (stem)
    publication_date: str               # YYYY or YYYY-MM-DD if extractable, else ""

    def to_dict(self) -> dict:
        return {
            "source_authority": self.source_authority,
            "age_group": self.age_group,
            "urgency_relevance": self.urgency_relevance,
            "content_type": self.content_type,
            "source_doc": self.source_doc,
            "publication_date": self.publication_date,
        }


# ── Tagger implementation ─────────────────────────────────────────────────────

class MetadataTagger:
    """
    Assigns structured metadata to a text chunk using heuristic rules.

    Usage::

        tagger = MetadataTagger(pdf_path="data/nice_cg160.pdf")
        meta = tagger.tag(chunk_text, source_override="NICE")
    """

    def __init__(self, pdf_path: str) -> None:
        self._path = Path(pdf_path)
        self._stem = self._path.stem.lower()
        self._source_from_filename = self._detect_source_from_filename()

    # ── Public API ─────────────────────────────────────────────────────────

    def tag(
        self,
        text: str,
        source_override: Optional[SourceAuthority] = None,
    ) -> ChunkMetadata:
        """
        Tag a single chunk text with metadata.

        Args:
            text: The chunk text content.
            source_override: If provided (e.g., from CLI --source flag),
                             takes precedence over filename detection.

        Returns:
            A ChunkMetadata object with all fields populated.
        """
        text_lower = text.lower()

        source_authority = source_override or self._source_from_filename
        age_group = self._detect_age_group(text_lower)
        urgency_relevance = self._detect_urgency(text_lower)
        content_type = self._detect_content_type(text_lower)
        publication_date = self._extract_publication_date(text_lower)

        meta = ChunkMetadata(
            source_authority=source_authority,
            age_group=age_group,
            urgency_relevance=urgency_relevance,
            content_type=content_type,
            source_doc=self._path.stem,
            publication_date=publication_date,
        )

        logger.debug(
            "Tagged chunk → source=%s age=%s urgency=%s type=%s",
            source_authority, age_group, urgency_relevance, content_type,
        )
        return meta

    def tag_batch(
        self,
        texts: list[str],
        source_override: Optional[SourceAuthority] = None,
    ) -> list[ChunkMetadata]:
        """
        Tag a list of chunk texts. Convenience wrapper around `tag()`.

        Args:
            texts: List of chunk text strings.
            source_override: Optional CLI-level source authority override.

        Returns:
            List of ChunkMetadata objects, one per input text.
        """
        return [self.tag(t, source_override) for t in texts]

    # ── Detection helpers ──────────────────────────────────────────────────

    def _detect_source_from_filename(self) -> SourceAuthority:
        """Match the PDF filename stem against known source patterns."""
        for pattern, authority in _SOURCE_FILENAME_PATTERNS:
            if pattern.search(self._stem):
                logger.debug("Source detected from filename: %s", authority)
                return authority
        logger.debug("Source not detected from filename '%s' → UNKNOWN", self._stem)
        return "UNKNOWN"

    @staticmethod
    def _detect_age_group(text_lower: str) -> AgeGroup:
        """Return the most specific age group whose keywords appear in the text."""
        for keywords, group in _AGE_KEYWORD_MAP:
            if any(kw in text_lower for kw in keywords):
                return group
        return "all"

    @staticmethod
    def _detect_urgency(text_lower: str) -> UrgencyRelevance:
        """Return urgency level based on keyword presence."""
        for keywords, urgency in _URGENCY_KEYWORD_MAP:
            if any(kw in text_lower for kw in keywords):
                return urgency
        return "routine"

    @staticmethod
    def _detect_content_type(text_lower: str) -> ContentType:
        """Return content type based on keyword presence."""
        for keywords, content_type in _CONTENT_TYPE_KEYWORD_MAP:
            if any(kw in text_lower for kw in keywords):
                return content_type
        return "parent_education"

    @staticmethod
    def _extract_publication_date(text_lower: str) -> str:
        """
        Attempt to extract a year or full date from the chunk text.

        Looks for patterns like:
          - \"published 2019\", \"updated 2023\", \"© 2021\"
          - ISO dates: 2020-03-15
        Returns a string like \"2019\" or \"2020-03-15\", or \"\" if not found.
        """
        # Full ISO date
        iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text_lower)
        if iso_match:
            return iso_match.group(1)

        # Year near publication keywords
        year_context = re.search(
            r"(published|updated|revised|issued|©|copyright)\s+(?:in\s+)?(20\d{2})\b",
            text_lower,
        )
        if year_context:
            return year_context.group(2)

        # Bare 4-digit year (20xx) — lower confidence, only if unique
        years = re.findall(r"\b(20\d{2})\b", text_lower)
        if len(years) == 1:
            return years[0]

        return ""
