# Security Policy

## Reporting Vulnerabilities

Do not open public issues for suspected vulnerabilities, exposed credentials,
patient data leakage, authentication bypasses, unsafe clinical behavior, or
prompt-injection paths.

Report privately to the project maintainers with:

- A concise description of the issue.
- Steps to reproduce.
- Affected files, endpoints, models, or infrastructure components.
- Any logs or payloads needed to validate the issue, with secrets and patient
  identifiers removed.

## Data Handling

- Do not commit `.env`, AWS credentials, Cognito secrets, DynamoDB exports, raw
  patient data, or private clinical documents.
- Use `.env.example` for configuration shape only.
- Redact personal and health information from test fixtures, screenshots, logs,
  traces, and bug reports.

## Clinical Safety

PediCompass is software, not a substitute for professional medical judgment.
Changes that affect triage, safety gating, retrieval, clinical reasoning, or
generated advice should include targeted tests and reviewer attention.
