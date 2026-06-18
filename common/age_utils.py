"""
Age utility functions for PediCompass.

Used by Stage 0 (safety screen) and Stage 1 (query analysis).
Centralising here ensures age parsing logic is identical across all call sites.

Design goals:
- Pure functions, no LLM dependency, runs in <1ms
- Handle English and Vietnamese age expressions
- Conservative estimates when exact age is ambiguous ("newborn" → 14 days)
- Priority: Child Profile DOB > regex parse from free text > None
"""

import re
from datetime import date
from enum import Enum
from typing import Optional


# ── Age group enum ─────────────────────────────────────────────────────────────

class AgeGroup(str, Enum):
    NEWBORN = "newborn"            # 0–28 days
    YOUNG_INFANT = "young_infant"  # 29–90 days
    INFANT = "infant"              # 91–365 days
    TODDLER = "toddler"            # 366–1095 days
    PRESCHOOL = "preschool"        # 1096–1825 days


# ── Regex patterns for age extraction from free text ──────────────────────────
# Each entry: (regex_pattern, unit_name, multiplier_to_days)
# Evaluated top-to-bottom; first match wins.

_AGE_PATTERNS: list[tuple[str, str, Optional[int]]] = [
    # ── English ───────────────────────────────────────────────────────────────
    # "X day(s) old" / "X-day-old"
    (r"(\d+)\s*[-–]?\s*days?\s*[-–]?\s*old", "days", 1),
    # "X week(s) old" / "X-week-old"
    (r"(\d+)\s*[-–]?\s*weeks?\s*[-–]?\s*old", "weeks", 7),
    # "X month(s) old" / "X-month-old"
    (r"(\d+)\s*[-–]?\s*months?\s*[-–]?\s*old", "months", 30),
    # "X year(s) old" / "X-year-old"
    (r"(\d+)\s*[-–]?\s*years?\s*[-–]?\s*old", "years", 365),
    # Shorthand: "3mo", "6mo", "2wk"
    (r"(\d+)\s*mo\b", "months", 30),
    (r"(\d+)\s*wk\b", "weeks", 7),
    # Keyword-only: "newborn" / "neonatal" / "neonate"
    # No digit group — handled separately with a fixed return value
    (r"\b(newborn|neonate|neonatal)\b", "keyword_newborn", None),

    # ── Vietnamese ────────────────────────────────────────────────────────────
    # "X ngày tuổi" (X days old)
    (r"(\d+)\s*ngày\s*tuổi", "days", 1),
    # "X tuần tuổi" (X weeks old)
    (r"(\d+)\s*tuần\s*tuổi", "weeks", 7),
    # "X tháng tuổi" (X months old)
    (r"(\d+)\s*tháng\s*tuổi", "months", 30),
    # "X tuổi" (X years old) — must be last to avoid matching substrings above
    (r"(\d+)\s*tuổi", "years", 365),
]

# Conservative estimate for "newborn" keyword with no numeric value.
# 14 days = middle of newborn window (0–28 days). Chosen conservatively so that
# a 1-day-old calling themselves "newborn" still triggers emergency screens.
_NEWBORN_KEYWORD_DAYS = 14


def extract_age_days_from_text(text: str) -> Optional[int]:
    """
    Parse child age in days from a free-text message.

    Does NOT call any LLM. Uses regex only. Runs in <1ms.

    Args:
        text: Free-text input from a parent (English or Vietnamese).

    Returns:
        Age in days as an integer, or None if no recognisable pattern found.
    """
    text_lower = text.lower()

    for pattern, unit, multiplier in _AGE_PATTERNS:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if not match:
            continue

        if unit == "keyword_newborn":
            return _NEWBORN_KEYWORD_DAYS

        value = int(match.group(1))
        return value * multiplier  # type: ignore[operator]

    return None


def map_age_to_group(age_days: int) -> AgeGroup:
    """
    Map an age in days to a clinical age group.

    Clinical boundaries per WHO / NICE / AAP convention:
      Newborn:      0–28 days    — highest risk, distinct physiology
      Young infant: 29–90 days   — high-risk, immature immune response
      Infant:       91–365 days  — transitional thresholds
      Toddler:      366–1095 days — more robust
      Preschool:    1096–1825 days — closer to standard child thresholds

    Args:
        age_days: Age in days (must be >= 0).

    Returns:
        AgeGroup enum value.
    """
    if age_days <= 28:
        return AgeGroup.NEWBORN
    elif age_days <= 90:
        return AgeGroup.YOUNG_INFANT
    elif age_days <= 365:
        return AgeGroup.INFANT
    elif age_days <= 1095:
        return AgeGroup.TODDLER
    else:
        return AgeGroup.PRESCHOOL


def resolve_age_days(
    message: str,
    profile_dob: Optional[str] = None,
) -> Optional[int]:
    """
    Resolve the child's age in days using all available sources.

    Resolution priority (highest to lowest):
      1. Child Profile DOB (ISO string "YYYY-MM-DD") — exact, reliable
      2. Regex extraction from free-text message — approximate, safe
      3. None — not enough information

    Args:
        message: The parent's free-text message.
        profile_dob: Date of birth string in ISO format, or None if no profile.

    Returns:
        Age in days, or None if unresolvable.
    """
    if profile_dob:
        try:
            dob = date.fromisoformat(profile_dob)
            return (date.today() - dob).days
        except ValueError:
            pass  # Malformed DOB — fall through to regex

    return extract_age_days_from_text(message)


def age_days_to_display(age_days: int) -> str:
    """
    Convert age in days to a human-readable string.

    Used in UI displays and agent prompts.

    Examples:
        7  → "7 days old"
        60 → "2 months old"
        400 → "1 year 1 month old"
    """
    if age_days < 28:
        return f"{age_days} day{'s' if age_days != 1 else ''} old"
    elif age_days < 365:
        months = age_days // 30
        return f"{months} month{'s' if months != 1 else ''} old"
    else:
        years = age_days // 365
        remaining_months = (age_days % 365) // 30
        if remaining_months > 0:
            return f"{years} year{'s' if years != 1 else ''} {remaining_months} month{'s' if remaining_months != 1 else ''} old"
        return f"{years} year{'s' if years != 1 else ''} old"
