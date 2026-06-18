import re
from pydantic import BaseModel
from typing import Optional

class ValidationResult(BaseModel):
    safe: bool
    flagged_pattern: Optional[str] = None

# Precision-high patterns to prevent false positives like "your child has good color"
DIAGNOSIS_ASSERTION_PATTERNS = [
    r"your child (has|is suffering from|is diagnosed with)\s+(a |an )?"
    r"(infection|pneumonia|bronchiolitis|otitis|gastroenteritis|"
    r"meningitis|sepsis|dehydration|RSV|strep|flu|influenza|"
    r"[a-z]+itis|[a-z]+osis|[a-z]+emia)",

    r"(this is|that is)\s+(a |an )?(case of |)?"
    r"(infection|pneumonia|bronchiolitis|[a-z]+itis|[a-z]+osis|[a-z]+emia)",

    r"(diagnosed with|diagnosis (is|of))\s+[a-z]+"
]

class OutputValidator:
    def validate(self, text: str) -> ValidationResult:
        text_lower = text.lower()
        for pattern in DIAGNOSIS_ASSERTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return ValidationResult(safe=False, flagged_pattern=pattern)
        return ValidationResult(safe=True)
