"""
Stage 0 — Deterministic Safety Screen with Hybrid Context Check.

Runs fast keyword matching for unambiguous red flags (<10ms).
For ambiguous red flags (e.g. "difficulty breathing"), triggers a fast 
LLM context check (Haiku) to eliminate false positives from negated symptoms.

Returns (Optional[RedFlag], Optional[int]) — the red flag (if any) and the
resolved age in days.
"""

import asyncio
import json
import logging
import re
from typing import Optional

# common/ is on sys.path (patched by main.py at startup)
from common.age_utils import resolve_age_days
from config import settings
from agent.models import RedFlag

logger = logging.getLogger(__name__)

# ── Age-independent red flags (Layer A - Unambiguous) ──────────────────────────
UNAMBIGUOUS_FLAGS: list[dict] = [
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

# ── Age-independent red flags (Layer B - Context Sensitive) ───────────────────
CONTEXT_SENSITIVE_FLAGS: list[dict] = [
    {
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
]

# ── Age-dependent red flags ───────────────────────────────────────────────────
AGE_DEPENDENT_FLAGS: list[dict] = [
    {
        "name": "fever_young_infant",
        "patterns": [
            r"\bfever\b", r"\btemperature\b", r"\bfebrile\b",
            r"3[89](?:\.\d)?°", r"4[012](?:\.\d)?°",
            r"3[89](?:\.\d)?\s*degrees",
        ],
        "age_condition": lambda d: d < 90,
        "context_sensitive": True,
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
        "context_sensitive": True,
        "reason": "Feeding refusal in newborn (under 28 days)",
        "action": "Seek emergency paediatric care immediately.",
    },
]

HAIKU_PROMPT = """You are a pediatric emergency screening assistant. 
A keyword related to a possible emergency was detected in a parent's message.
Determine ONLY if the parent is REPORTING this symptom as currently present 
(not denying it, not asking about it, not ruling it out).

Respond ONLY with valid JSON: {"is_emergency_present": true, "reason": "..."} or {"is_emergency_present": false, "reason": "..."}

Be very conservative: if ambiguous, return true."""

class PediatricEmergencyScreen:
    """
    Layer 1 safety screen — Hybrid approach.
    
    1. Deterministic keyword matching (fast, no LLM).
    2. If an ambiguous keyword matches, calls Haiku (fast LLM) to check context
       and eliminate false positives (e.g. "no difficulty breathing").
    """

    def __init__(self, bedrock_client=None) -> None:
        self.llm = bedrock_client

    async def _haiku_context_check(self, keyword_or_pattern: str, message: str) -> bool:
        """
        Ask Haiku if the keyword actually implies an emergency in context.
        Returns True if emergency is confirmed, False if denied/benign.
        """
        if not self.llm:
            logger.warning("No bedrock_client provided to Stage 0. Defaulting to emergency.")
            return True

        if not settings.bedrock_haiku_model_id:
            logger.warning("bedrock_haiku_model_id not configured. Defaulting to emergency.")
            return True

        user_text = f"Keyword detected: '{keyword_or_pattern}'\nFull parent message: '{message}'"
        
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "system": HAIKU_PROMPT,
                "messages": [{"role": "user", "content": user_text}],
                "max_tokens": 150,
            }
            
            loop = asyncio.get_running_loop()
            
            def _call_haiku():
                response = self.llm._client.invoke_model(
                    modelId=settings.bedrock_haiku_model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                return json.loads(response["body"].read())
                
            response_body = await asyncio.wait_for(loop.run_in_executor(None, _call_haiku), timeout=3.0)
            
            # Extract JSON from response
            text = ""
            for block in response_body.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            
            # Parse JSON
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                is_emergency = parsed.get("is_emergency_present", True)
                logger.info("Haiku context check result: %s. Reason: %s", is_emergency, parsed.get("reason"))
                return is_emergency
            else:
                logger.warning("Could not parse JSON from Haiku: %s", text)
                return True
                
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("Haiku context check failed (%s) — defaulting to emergency", exc)
            return True

    async def screen(
        self,
        message: str,
        profile_dob: Optional[str] = None,
    ) -> tuple[Optional[RedFlag], Optional[int]]:
        """
        Screen the message for emergency red flags.
        """
        age_days = resolve_age_days(message, profile_dob)
        text_lower = message.lower()

        # 1. Age-independent Unambiguous checks
        for flag in UNAMBIGUOUS_FLAGS:
            if any(kw in text_lower for kw in flag["keywords"]):
                return self._create_red_flag(flag), age_days

        # 2. Age-independent Context-Sensitive checks
        for flag in CONTEXT_SENSITIVE_FLAGS:
            for kw in flag["keywords"]:
                if kw in text_lower:
                    is_real = await self._haiku_context_check(kw, message)
                    if is_real:
                        return self._create_red_flag(flag), age_days
                    break # if false positive, skip this flag and continue

        # 3. Age-dependent checks
        if age_days is not None:
            for flag in AGE_DEPENDENT_FLAGS:
                matched_pattern = None
                if "patterns" in flag:
                    for pat in flag["patterns"]:
                        if re.search(pat, text_lower):
                            matched_pattern = pat
                            break
                else:
                    for kw in flag.get("keywords", []):
                        if kw in text_lower:
                            matched_pattern = kw
                            break
                    
                age_match = flag["age_condition"](age_days)
                if matched_pattern and age_match:
                    if flag.get("context_sensitive", False):
                        is_real = await self._haiku_context_check(matched_pattern, message)
                        if not is_real:
                            continue
                            
                    return self._create_red_flag(flag), age_days

        return None, age_days

    def _create_red_flag(self, flag: dict) -> RedFlag:
        return RedFlag(
            detected=True,
            reason=flag["reason"],
            immediate_action=flag["action"],
            triggered_pattern=flag["name"],
        )
