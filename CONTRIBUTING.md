# Contributing

Thank you for helping improve PediCompass. Keep changes focused, reproducible,
and aligned with the existing architecture.

## Local Setup

1. Copy `.env.example` to `.env` and fill in local values.
2. Start Qdrant with `docker compose up -d`.
3. Install backend dependencies from `backend/requirements.txt`.
4. Install frontend dependencies from `frontend/package.json`.

## Development Standards

- Prefer improving the current architecture before introducing new services,
  model providers, or frameworks.
- Keep clinical safety behavior explicit and test-covered.
- Avoid committing secrets, raw patient data, generated model caches, or large
  source PDFs.
- Preserve reproducibility when touching data processing, retrieval, model
  inference, or evaluation paths.
- Document tensor, matrix, graph, and payload shapes where ambiguity could hide
  a logic error.

## Checks

Run the relevant checks before opening a change:

```bash
cd backend
pytest tests/ -v
```

```bash
cd frontend
npm run lint
npm run build
```
