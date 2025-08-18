from __future__ import annotations

import argparse
import os
from typing import Any, Dict, List

import pandas as pd
import requests

from datasets import Dataset
from ragas.evaluation import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI


def call_query(api_base: str, question: str, source: str | None, strict_privacy: bool) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/api/v1/query"
    payload: Dict[str, Any] = {"query": question, "strict_privacy": strict_privacy}
    if source:
        payload["source"] = source
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def build_dataset(df_questions: pd.DataFrame, api_base: str, source: str | None, strict_privacy: bool) -> Dataset:
    records: List[Dict[str, Any]] = []
    for idx, row in df_questions.iterrows():
        q = str(row["question"]).strip()
        gt = str(row["ground_truth_answer"]).strip()
        out = call_query(api_base, q, source=source, strict_privacy=strict_privacy)
        answer = str(out.get("answer", "")).strip()
        citations = out.get("citations", []) or []
        contexts = [str(c.get("text", "")) for c in citations if str(c.get("text", "")).strip()]
        records.append({
            "question": q,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": gt,
        })
    return Dataset.from_pandas(pd.DataFrame.from_records(records))


def run_ragas(ds: Dataset, model_name: str) -> pd.DataFrame:
    # OPENAI_API_KEY must be set in env
    base_llm = ChatOpenAI(model=model_name, temperature=0.0)
    llm = LangchainLLMWrapper(base_llm)
    result = evaluate(
        ds,
        metrics=[faithfulness, answer_relevancy, context_precision],
        llm=llm,
    )
    return result.to_pandas()


def summarize(df_scores: pd.DataFrame) -> Dict[str, float]:
    def mean_for(col: str) -> float:
        if col not in df_scores.columns:
            return 0.0
        series = pd.to_numeric(df_scores[col], errors="coerce").dropna()
        return float(series.mean()) if not series.empty else 0.0

    return {
        "faithfulness": mean_for("faithfulness"),
        "answer_relevancy": mean_for("answer_relevancy"),
        "context_precision": mean_for("context_precision"),
    }


def check_quality_gate(aggregates: Dict[str, float], threshold: float = 0.85) -> bool:
    return all(score >= threshold for score in aggregates.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG pipeline with Ragas")
    parser.add_argument("--csv", required=True, help="Path to golden_dataset.csv (columns: question, ground_truth_answer)")
    parser.add_argument("--api-base", default=os.environ.get("API_BASE", "http://localhost:8000"))
    parser.add_argument("--source", default=os.environ.get("RAG_SOURCE", None))
    parser.add_argument("--model", default=os.environ.get("RAGAS_MODEL", "gpt-4o-mini"))
    parser.add_argument("--strict-privacy", action="store_true", default=True)
    parser.add_argument("--no-strict-privacy", action="store_true", dest="no_strict_privacy")
    parser.add_argument("--threshold", type=float, default=0.85)
    args = parser.parse_args()

    strict_privacy = not args.no_strict_privacy
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for Ragas LLM-based metrics")

    df_q = pd.read_csv(args.csv)
    expected_cols = {"question", "ground_truth_answer"}
    if not expected_cols.issubset(set(df_q.columns)):
        raise SystemExit(f"CSV must contain columns: {expected_cols}")

    print(f"Building evaluation dataset from {len(df_q)} questions …")
    ds = build_dataset(df_q, api_base=args.api_base, source=args.source, strict_privacy=strict_privacy)
    print("Running Ragas metrics (faithfulness, answer_relevancy, context_precision) …")
    df_scores = run_ragas(ds, model_name=args.model)

    aggregates = summarize(df_scores)
    print("\nAggregate Scores:")
    for k, v in aggregates.items():
        print(f"- {k}: {v:.3f}")

    ok = check_quality_gate(aggregates, threshold=args.threshold)
    print(f"\nQuality Gate (>= {args.threshold:.2f} across all): {'PASS' if ok else 'FAIL'}")

    # Save a simple report CSV next to input
    out_path = os.path.splitext(args.csv)[0] + "_ragas_report.csv"
    df_scores.to_csv(out_path, index=False)
    print(f"\nPer-sample scores written to: {out_path}")


if __name__ == "__main__":
    main()


