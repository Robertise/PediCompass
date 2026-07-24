import os
import sys
from unittest.mock import MagicMock

# Ensure backend and code directories are on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
code_dir = os.path.abspath(os.path.join(backend_dir, ".."))

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

# Set default environment variables for Pydantic Settings before config import
os.environ.setdefault("BEDROCK_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
os.environ.setdefault("BEDROCK_HAIKU_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
os.environ.setdefault("COGNITO_USER_POOL_ID", "ap-southeast-1_Osm01gaEp")
os.environ.setdefault("COGNITO_CLIENT_ID", "2eh8v88egbs0khrutkemnjtceu")
os.environ.setdefault("AWS_REGION", "ap-southeast-1")

# Mock sentence_transformers if not installed in environment
try:
    import sentence_transformers
except ImportError:
    mock_st = MagicMock()
    sys.modules["sentence_transformers"] = mock_st
