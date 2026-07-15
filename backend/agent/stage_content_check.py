"""
Stage Content Check — Pure rule-based module to filter vague, short, or greeting messages.
Runs immediately after Stage 0 (Safety Screen) and before LLM calls.
"""

from dataclasses import dataclass
import re


GREETING_PATTERNS: list[str] = [
    "hi", "hello", "hey",
    "good morning", "good afternoon", "good evening",
]

VAGUE_PATTERNS: list[str] = [
    "help", "please help", "i need help",
    "can you help", "what can you do",
    "how does this work", "who are you",
]

MEDICAL_KEYWORD_PASSLIST: list[str] = [
    "rsv", "fever", "cough", "rash", "seizure", "vomit",
    "diarrhea", "dehydration", "vaccine", "fontanelle",
    "newborn", "infant", "toddler", "pediatric", "temperature",
    "who", "nice", "cdc", "aap", "paracetamol", "ibuprofen",
    "breathing", "wheezing", "jaundice", "eczema", "bronchiolitis",
]

STOP_WORDS: set[str] = {
    "i", "my", "the", "a", "an", "is", "are", "was",
    "it", "he", "she", "they", "of", "in", "for",
    "and", "or", "but", "to", "can", "do", "does",
    "what", "how", "when", "why", "where", "about",
}

GREETING_RESPONSE_TEXT = (
    "Hello! I'm PediCompass, your pediatric health guide. You can ask me about your child's "
    "symptoms for age-appropriate care guidance, or explore general children's health topics "
    "like fever management, RSV, vaccination schedules, and more. How can I help you today?"
)


@dataclass
class ContentCheckResult:
    should_pass: bool
    reason: str


class ContentCheck:
    @staticmethod
    def check(message: str, history: list[dict]) -> ContentCheckResult:
        """
        Check if the first message has sufficient content to proceed.
        Bypassed if history is not empty (multi-turn conversation).
        """
        if len(history) > 0:
            return ContentCheckResult(should_pass=True, reason="multi_turn_bypass")

        msg_lower = message.strip().lower()

        # Check for exact word matches in greeting patterns
        # Use regex to match whole words/phrases to prevent 'this is hilarious' from failing
        for greeting in GREETING_PATTERNS:
            if re.search(rf"\b{re.escape(greeting)}\b", msg_lower):
                return ContentCheckResult(should_pass=False, reason="greeting")

        # Medical keywords bypass (must be checked BEFORE vague patterns)
        for kw in MEDICAL_KEYWORD_PASSLIST:
            if kw in msg_lower:
                return ContentCheckResult(should_pass=True, reason="medical_keyword_detected")

        # Vague patterns
        for vague in VAGUE_PATTERNS:
            if vague in msg_lower:
                return ContentCheckResult(should_pass=False, reason="vague")

        # Word count after removing stop words
        words = re.findall(r'\b\w+\b', msg_lower)
        content_words = [w for w in words if w not in STOP_WORDS]
        if len(content_words) < 3:
            return ContentCheckResult(should_pass=False, reason="insufficient_content")

        return ContentCheckResult(should_pass=True, reason="sufficient_content")
