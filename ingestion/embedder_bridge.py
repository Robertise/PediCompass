"""
embedder_bridge.py — Path bridge for common/embedder.py

Resolves the sys.path issue when running ingestion scripts directly from
the code/ingestion/ directory. By inserting the `code/` parent directory
into sys.path, `from common.embedder import ...` works correctly regardless
of the current working directory.

Usage (in any ingestion module):
    from embedder_bridge import embed_batch, embed, EMBEDDING_DIM
"""

import os
import sys

# Insert the `code/` directory (parent of this file's directory) so that
# `from common.embedder import ...` resolves correctly.
_CODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)

# Re-export everything callers need — so they import from embedder_bridge
# instead of directly importing from common.embedder. This keeps all
# path-manipulation in one place.
from common.embedder import embed, embed_batch, EMBEDDING_DIM  # noqa: E402, F401
