import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../backend"))

sys.path.insert(0, CODE_DIR)
sys.path.insert(0, BACKEND_DIR)

from rag.qdrant_client import get_qdrant_manager
from common.embedder import embed

qm = get_qdrant_manager()

with open(os.path.join(SCRIPT_DIR, "eval_data/rag_testcases.json"), "r", encoding="utf-8") as f:
    tcs = json.load(f)

print("=" * 80)
print(f"VERIFYING {len(tcs)} TESTCASES AGAINST INGESTED QDRANT CHUNKS")
print("=" * 80)

for tc in tcs:
    q = tc["query"]
    age = tc["age_group"]
    vec = embed(tc["expected_keywords"][0] + " " + q)
    chunks = qm.search(vec, age_group_filter=[age, "all"], top_k=2)
    
    top_score = chunks[0]["score"] if chunks else 0
    top_text = chunks[0]["text"][:120].replace("\n", " ") if chunks else "NONE"
    doc_auth = chunks[0]["source_authority"] if chunks else "N/A"
    
    print(f"ID: {tc['id']} [{age:12s}] | Score: {top_score:.3f} | Authority: {doc_auth:5s} | Snippet: {top_text}")
