"""
Stage 0 — Deterministic Safety Screen.

No LLM. Runs in <10ms. Checks for paediatric emergency red flags using
keyword matching on two categories:
  1. Age-independent flags: trigger regardless of child age.
  2. Age-dependent flags: trigger only when the resolved age satisfies a condition.

Returns (Optional[RedFlag], Optional[int]) — the red flag (if any) and the
resolved age in days. The age is always returned so that analytics logging on
the emergency path can record the age group instead of None.
"""

from typing import Optional

# common/ is on sys.path (patched by main.py at startup)
from common.age_utils import resolve_age_days

from agent.models import RedFlag


# ── Age-independent red flags ─────────────────────────────────────────────────
# These trigger regardless of the child's age.
#
# IMPORTANT keyword-safety notes (to prevent false positives):
#
#  * "fit" is NOT included bare → matches "a fit of crying" (tantrum, not seizure).
#    Use unambiguous synonyms: "seizure", "convulsion", "fitting", etc.
#
#  * "limp" is NOT included bare → matches "limping after the fall" (leg injury).
#    Use "went limp" or "floppy" which capture the intended meaning (body went
#    limp/unresponsive) without catching benign walking descriptions.
#
#  * "grunting" is NOT included bare → matches "grunting while pooping"
#    (straining during a bowel movement, totally benign).
#    Qualified to respiratory-context phrases only.

AGE_INDEPENDENT_FLAGS: list[dict] = [
    {
        "name": "cyanosis",
        "keywords": [
            "blue lips", "blue face", "bluish", "cyanosis", "purple lips",
            "turning blue", "gone blue",
        ],
        "reason": "Cyanosis detected (blue/purple discoloration)",
        "action": (
            "Call emergency services (999/911) immediately. "
            "Cyanosis is a life-threatening emergency."
        ),
    },
    {
        "name": "bulging_fontanelle",
        "keywords": [
            "bulging fontanelle", "bulging soft spot", "fontanel bulging",
            "swollen fontanelle", "tense fontanelle",
        ],
        "reason": "Bulging fontanelle reported",
        "action": "Go to the Pediatric Emergency Department immediately.",
    },
    {
        # bare "fit" excluded — see module-level docstring.
        "name": "febrile_seizure",
        "keywords": [
            "seizure", "convulsion", "convulsing", "seizing",
            "fitting", "shaking uncontrollably", "jerking",
            "body shaking", "twitching all over",
        ],
        "reason": "Seizure / febrile convulsion reported",
        "action": "Call emergency services (999/911) immediately.",
    },
    {
        # bare "limp" excluded — see module-level docstring.
        "name": "unresponsive",
        "keywords": [
            "unresponsive", "won't wake", "won't wake up", "unconscious",
            "went limp", "floppy", "not responding", "cannot wake",
            "can't wake", "passed out", "lost consciousness",
        ],
        "reason": "Child is unresponsive or cannot be woken",
        "action": "Call emergency services (999/911) immediately.",
    },
    {
        # bare "grunting" excluded — see module-level docstring.
        "name": "breathing_difficulty",
        "keywords": [
            "can't breathe", "cannot breathe", "difficulty breathing",
            "struggling to breathe", "grunting while breathing",
            "grunting with each breath", "nasal flaring",
            "chest retractions", "gasping", "not breathing",
            "stopped breathing", "apnea", "apnoea",
            "working hard to breathe",
        ],
        "reason": "Signs of respiratory distress",
        "action": "Call emergency services (999/911) immediately.",
    },
    {
        "name": "severe_dehydration",
        "keywords": [
            "no wet diaper", "hasn't urinated", "no urine", "sunken eyes",
            "sunken fontanelle", "very dry mouth", "no tears",
            "dry eyes", "skin tenting",
        ],
        "reason": "Signs of severe dehydration",
        "action": "Go to the Pediatric Emergency Department immediately.",
    },
    {
        "name": "inconsolable_cry",
        "keywords": [
            "high-pitched cry", "high pitched cry", "inconsolable",
            "won't stop crying", "screaming in pain", "shrieking",
            "piercing cry", "constant crying for hours",
        ],
        "reason": "High-pitched or inconsolable cry reported",
        "action": "Seek urgent paediatric care immediately.",
    },
    {
        "name": "petechiae_purpura",
        "keywords": [
            "petechiae", "purpura", "non-blanching rash",
            "purple spots", "blood spots under skin",
        ],
        "reason": "Non-blanching rash / petechiae reported — possible meningococcal disease",
        "action": (
            "Call emergency services (999/911) immediately. "
            "Non-blanching rash in a child is a medical emergency."
        ),
    },
]


# ── Age-dependent red flags ───────────────────────────────────────────────────
# These only trigger when the resolved age satisfies the `age_condition` lambda.

AGE_DEPENDENT_FLAGS: list[dict] = [
    {
        "name": "fever_young_infant",
        "keywords": [
            "fever", "temperature", "hot", "feverish",
            "38", "37.8", "37.9", "39", "40", "38.5", "38.1", "38.2",
        ],
        "age_condition": lambda d: d < 90,
        "reason": "Fever in infant under 3 months of age",
        "action": (
            "Go to the Pediatric Emergency Department immediately — "
            "fever in infants under 3 months is always a medical emergency."
        ),
    },
    {
        "name": "not_feeding_newborn",
        "keywords": [
            "not feeding", "won't feed", "refusing to feed", "not eating",
            "can't latch", "not breastfeeding", "not drinking",
            "refuses breast", "not taking bottle",
        ],
        "age_condition": lambda d: d < 28,
        "reason": "Feeding refusal in newborn (under 28 days)",
        "action": "Seek emergency paediatric care immediately.",
    },
]


class PediatricEmergencyScreen:
    """
    Layer 1 safety screen — deterministic, no LLM, <10ms.

    Checks for emergency red flags in the parent's message using keyword
    matching. Age-dependent flags require the child's age to be resolved
    (via Profile DOB or regex parsing of the message text).
    """

    def screen(
        self,
        message: str,
        profile_dob: Optional[str] = None,
    ) -> tuple[Optional[RedFlag], Optional[int]]:
        """
        Screen the message for emergency red flags.

        Age resolution priority:
          1. Child Profile DOB (exact, reliable)
          2. Regex parse from message text (approximate, safe)
          3. None → age-dependent flags cannot trigger

        Args:
            message: The parent's free-text message.
            profile_dob: ISO date string "YYYY-MM-DD" from the child's profile,
                         or None if no profile is attached.

        Returns:
            Tuple of (red_flag, age_days).
            - red_flag: RedFlag if an emergency pattern was detected, else None.
            - age_days: Resolved age in days (may be None if not determinable).
              Always returned — even when a red flag IS detected — so callers
              on the emergency path can log the age group without it being lost.
        """
        age_days = resolve_age_days(message, profile_dob)
        text_lower = message.lower()

        # 1. Age-independent checks (always run, no age required)
        for flag in AGE_INDEPENDENT_FLAGS:
            if any(kw in text_lower for kw in flag["keywords"]):
                red_flag = RedFlag(
                    detected=True,
                    reason=flag["reason"],
                    immediate_action=flag["action"],
                    triggered_pattern=flag["name"],
                )
                return red_flag, age_days

        # 2. Age-dependent checks (only when age could be resolved)
        if age_days is not None:
            for flag in AGE_DEPENDENT_FLAGS:
                kw_match = any(kw in text_lower for kw in flag["keywords"])
                age_match = flag["age_condition"](age_days)
                if kw_match and age_match:
                    red_flag = RedFlag(
                        detected=True,
                        reason=flag["reason"],
                        immediate_action=flag["action"],
                        triggered_pattern=flag["name"],
                    )
                    return red_flag, age_days

        return None, age_days
