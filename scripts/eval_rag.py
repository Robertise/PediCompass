#!/usr/bin/env python3
"""
RAG Evaluation Script for edix.

Evaluates:
  1. Retrieval Quality (Keyword Hit@1, Keyword Hit@3, Mean Rerank Score, Age Group Filter Compliance)
  2. Urgency Classification Accuracy (Exact Match, Adjacent Match, Critical Safety Misses)

Usage:
  # Full evaluation (Retrieval + Stage 0/Stage 3 Bedrock reasoning)
  python scripts/eval_rag.py

  # Fast evaluation (Retrieval only, no Bedrock API calls)
  python scripts/eval_rag.py --retrieval-only

  # Custom output path or top-k
  python scripts/eval_rag.py --top-k 5 --output scripts/eval_results/custom_run.json
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add code directory and backend directory to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../backend"))

for d in [CODE_DIR, BACKEND_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

# Suppress noisy logs during eval run
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("qdrant_client").setLevel(logging.WARNING)

from common.age_utils import AgeGroup
from rag.qdrant_client import get_qdrant_manager
from rag.reranker import get_reranker
from rag.retriever import Retriever
from agent.stage2_retrieval import Stage2Retriever
from agent.stage0_safety import PediatricEmergencyScreen
from agent.stage3_reasoning import Stage3Reasoner
from llm.bedrock_client import BedrockClient

URGENCY_ORDER = ["emergency", "urgent", "soon", "routine", "self_care"]


def get_urgency_index(urgency_str: str) -> int:
    urgency_lower = urgency_str.lower()
    if urgency_lower in URGENCY_ORDER:
        return URGENCY_ORDER.index(urgency_lower)
    return 999


def check_keyword_hit(text: str, expected_keywords: List[str]) -> bool:
    """Check if any expected keyword exists as a substring in chunk text."""
    text_lower = text.lower()
    for kw in expected_keywords:
        if kw.lower() in text_lower:
            return True
    return False


async def run_evaluation(
    testcases_path: str,
    top_k: int = 3,
    retrieval_only: bool = False,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 68)
    print(" [PEDIX RAG & CLINICAL REASONING EVALUATION HARNESS]")
    print("=" * 68)
    print(f" Loading testcases from: {testcases_path}")
    print(f" Mode: {'RETRIEVAL-ONLY (No Bedrock)' if retrieval_only else 'FULL (Retrieval + Stage 0/3 Bedrock)'}")
    print(f" Top-K Retrieval: {top_k}")
    print("-" * 68)

    with open(testcases_path, "r", encoding="utf-8") as f:
        testcases = json.load(f)

    # Initialize RAG components
    print(" Initializing Qdrant Manager & Cross-Encoder Reranker...")
    qdrant = get_qdrant_manager()
    qdrant.ensure_collection()
    reranker = get_reranker()
    retriever = Retriever(qdrant, reranker)
    stage2 = Stage2Retriever(retriever)

    # Initialize LLM components if full evaluation mode
    safety_screen = None
    stage3 = None
    if not retrieval_only:
        print(" Initializing Bedrock Client & Agent Stages 0 / 3...")
        bedrock = BedrockClient()
        safety_screen = PediatricEmergencyScreen(bedrock)
        stage3 = Stage3Reasoner(bedrock)

    results: List[Dict[str, Any]] = []
    
    total_cases = len(testcases)
    retrieval_hit1_count = 0
    retrieval_hit3_count = 0
    age_filter_valid_count = 0
    rerank_scores_sum = 0.0
    
    urgency_exact_count = 0
    urgency_adjacent_count = 0
    critical_misses_count = 0

    start_time = time.time()

    for idx, tc in enumerate(testcases, start=1):
        tc_id = tc["id"]
        query = tc["query"]
        age_group_str = tc["age_group"]
        expected_urgency = tc["expected_urgency"]
        expected_keywords = tc.get("expected_keywords", [])
        
        try:
            age_group_enum = AgeGroup(age_group_str)
        except ValueError:
            age_group_enum = AgeGroup.ALL

        print(f"[{idx:02d}/{total_cases}] Evaluating {tc_id} ({age_group_str})... ", end="", flush=True)

        # Step 1: Stage 2 Retrieval
        t0 = time.time()
        retrieved_chunks = await stage2.retrieve(
            symptom_summary=query,
            age_group=age_group_enum,
        )
        retrieval_latency_ms = int((time.time() - t0) * 1000)

        # Limit to top_k
        chunks_top_k = retrieved_chunks[:top_k]

        # Compute Retrieval Metrics
        hit_at_1 = False
        hit_at_k = False
        if chunks_top_k:
            hit_at_1 = check_keyword_hit(chunks_top_k[0]["text"], expected_keywords)
            hit_at_k = any(check_keyword_hit(c["text"], expected_keywords) for c in chunks_top_k)

        if hit_at_1:
            retrieval_hit1_count += 1
        if hit_at_k:
            retrieval_hit3_count += 1

        avg_score = (
            sum(c.get("rerank_score", 0.0) for c in chunks_top_k) / len(chunks_top_k)
            if chunks_top_k
            else 0.0
        )
        rerank_scores_sum += avg_score

        # Age group filter compliance
        valid_age_filter = all(
            c.get("age_group") in [age_group_str, "all"] for c in chunks_top_k
        )
        if valid_age_filter:
            age_filter_valid_count += 1

        predicted_urgency = "unknown"
        urgency_exact = False
        urgency_adjacent = False
        is_critical_miss = False
        reasoning_latency_ms = 0

        # Step 2: Urgency Classification
        if not retrieval_only:
            t1 = time.time()
            # First check Stage 0 Safety Screen
            red_flag, _ = await safety_screen.screen(query)
            if red_flag and red_flag.detected:
                predicted_urgency = "emergency"
            else:
                # Stage 3 reasoning over query + retrieved chunks
                context = [{"role": "user", "content": query}]
                pathway = await stage3.reason(
                    context=context,
                    chunks=chunks_top_k,
                    age_group=age_group_enum,
                )
                predicted_urgency = pathway.urgency_level.value

            reasoning_latency_ms = int((time.time() - t1) * 1000)

            # Evaluate Urgency
            exp_idx = get_urgency_index(expected_urgency)
            pred_idx = get_urgency_index(predicted_urgency)

            urgency_exact = pred_idx == exp_idx
            urgency_adjacent = abs(pred_idx - exp_idx) <= 1

            if urgency_exact:
                urgency_exact_count += 1
            if urgency_adjacent:
                urgency_adjacent_count += 1

            # Critical safety miss: expected emergency, but predicted soon / routine / self_care
            if expected_urgency == "emergency" and pred_idx > get_urgency_index("urgent"):
                is_critical_miss = True
                critical_misses_count += 1

            status_str = "OK" if urgency_exact else ("ADJACENT" if urgency_adjacent else "MISMATCH")
            if is_critical_miss:
                status_str = "CRITICAL MISS [!]"
            print(f"Retrieved: {len(chunks_top_k)} chunks | Urgency: Exp={expected_urgency} Pred={predicted_urgency} [{status_str}]")
        else:
            print(f"Retrieved: {len(chunks_top_k)} chunks | Hit@1={hit_at_1} Hit@{top_k}={hit_at_k}")

        results.append({
            "id": tc_id,
            "query": query,
            "age_group": age_group_str,
            "expected_urgency": expected_urgency,
            "predicted_urgency": predicted_urgency,
            "expected_keywords": expected_keywords,
            "retrieval": {
                "chunks_count": len(chunks_top_k),
                "hit_at_1": hit_at_1,
                "hit_at_k": hit_at_k,
                "avg_rerank_score": round(avg_score, 4),
                "valid_age_filter": valid_age_filter,
                "latency_ms": retrieval_latency_ms,
                "retrieved_chunk_ids": [c.get("chunk_id") for c in chunks_top_k],
            },
            "urgency": {
                "exact_match": urgency_exact,
                "adjacent_match": urgency_adjacent,
                "critical_miss": is_critical_miss,
                "latency_ms": reasoning_latency_ms,
            } if not retrieval_only else None,
        })

    elapsed_time = round(time.time() - start_time, 2)

    # Calculate overall metrics
    hit1_pct = round((retrieval_hit1_count / total_cases) * 100, 1)
    hitk_pct = round((retrieval_hit3_count / total_cases) * 100, 1)
    avg_rerank_overall = round(rerank_scores_sum / total_cases, 4)
    age_filter_pct = round((age_filter_valid_count / total_cases) * 100, 1)

    exact_pct = round((urgency_exact_count / total_cases) * 100, 1) if not retrieval_only else 0.0
    adj_pct = round((urgency_adjacent_count / total_cases) * 100, 1) if not retrieval_only else 0.0

    # Print Summary Table
    print("\n" + "=" * 68)
    print(" [EVALUATION SUMMARY REPORT]")
    print("=" * 68)
    print(f" Total Cases Evaluated : {total_cases}")
    print(f" Execution Time       : {elapsed_time}s")
    print("-" * 68)
    print(" RETRIEVAL METRICS (Pass 1 Qdrant + Pass 2 Cross-Encoder):")
    print(f"   * Keyword Hit@1      : {retrieval_hit1_count}/{total_cases} ({hit1_pct}%)")
    print(f"   * Keyword Hit@{top_k}      : {retrieval_hit3_count}/{total_cases} ({hitk_pct}%)")
    print(f"   * Mean Rerank Score  : {avg_rerank_overall}")
    print(f"   * Age Filter Compliance: {age_filter_valid_count}/{total_cases} ({age_filter_pct}%)")

    if not retrieval_only:
        print("-" * 68)
        print(" CLINICAL URGENCY METRICS (Stage 0 Safety + Stage 3 Reasoner):")
        print(f"   * Exact Match        : {urgency_exact_count}/{total_cases} ({exact_pct}%)")
        print(f"   * Adjacent Match     : {urgency_adjacent_count}/{total_cases} ({adj_pct}%)")
        print(f"   * Critical Safety Misses: {critical_misses_count} " + ("[PASS]" if critical_misses_count == 0 else "[FAIL]"))
    print("=" * 68)

    summary_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total_cases,
        "elapsed_time_seconds": elapsed_time,
        "mode": "retrieval_only" if retrieval_only else "full",
        "top_k": top_k,
        "metrics": {
            "retrieval": {
                "hit_at_1_pct": hit1_pct,
                "hit_at_k_pct": hitk_pct,
                "mean_rerank_score": avg_rerank_overall,
                "age_filter_compliance_pct": age_filter_pct,
            },
            "urgency": {
                "exact_match_pct": exact_pct,
                "adjacent_match_pct": adj_pct,
                "critical_misses_count": critical_misses_count,
            } if not retrieval_only else None,
        },
        "details": results,
    }

    # Save output to JSON file
    if not output_path:
        os.makedirs(os.path.join(SCRIPT_DIR, "eval_results"), exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(SCRIPT_DIR, "eval_results", f"eval_{ts_str}.json")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    print(f"\n Detailed JSON evaluation report saved to:\n   {output_path}\n")
    return summary_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Pedix RAG & Clinical Reasoning Evaluator")
    parser.add_argument(
        "--testcases",
        type=str,
        default=os.path.join(SCRIPT_DIR, "eval_data", "rag_testcases.json"),
        help="Path to JSON testcases file",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of top retrieved chunks to consider (default: 3)",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Run retrieval evaluation only (skips Bedrock LLM calls)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output file path for evaluation results JSON",
    )

    args = parser.parse_args()

    asyncio.run(
        run_evaluation(
            testcases_path=args.testcases,
            top_k=args.top_k,
            retrieval_only=args.retrieval_only,
            output_path=args.output,
        )
    )


if __name__ == "__main__":
    main()
