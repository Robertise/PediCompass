"""
Central configuration for PediCompass backend.

All settings are loaded from environment variables (or .env file).
Required fields have no default — the app will fail loudly on startup
if they are not set, which is intentional.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── AWS core ──────────────────────────────────────────────────────────────
    aws_region: str = "ap-southeast-1"
    aws_access_key_id: str
    aws_secret_access_key: str

    # ── Bedrock ───────────────────────────────────────────────────────────────
    # MUST be the inference profile ID, NOT the bare model ID.
    # Obtain with: aws bedrock list-inference-profiles --region ap-southeast-1
    # Example: ap.anthropic.claude-3-5-sonnet-20241022-v2:0
    # Using bare model ID (e.g. "anthropic.claude-sonnet-4-5") causes:
    #   ValidationException: on-demand throughput isn't supported
    bedrock_model_id: str

    # ── Cognito ───────────────────────────────────────────────────────────────
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str = "ap-southeast-1"

    # ── DynamoDB ──────────────────────────────────────────────────────────────
    dynamodb_table_prefix: str = "pedicompass_"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "pedicompass_kb"

    # ── App ───────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"


settings = Settings()
