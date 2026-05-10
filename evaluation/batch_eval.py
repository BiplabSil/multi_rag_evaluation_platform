"""
evaluation/batch_eval.py
------------------------
Batch evaluation runner.

Reads a JSONL file of question/answer/context/ground_truth samples,
runs RAGAS on each, and writes a CSV summary.

Useful for:
- Offline regression testing after changing retrieval parameters.
- Generating evaluation reports for portfolio demos.

JSONL format (one JSON object per line):
    {"question": "...", "answer": "...", "contexts": ["...", "..."], "ground_truth": "..."}

Usage:
    python -m evaluation.batch_eval --input samples.jsonl --output results.csv
"""

import argparse
import csv
import json
import logging
from pathlib import Path

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

logger = logging.getLogger(__name__)


def run_batch_eval(input_path: str, output_path: str) -> None:
    """Evaluate all samples in a JSONL file and save scores to CSV.

    Args:
        input_path:  Path to the input JSONL file.
        output_path: Path for the output CSV file.
    """
    samples = _load_jsonl(input_path)
    logger.info("Loaded %d samples from %s", len(samples), input_path)

    dataset = Dataset.from_list(samples)
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    result = evaluate(dataset, metrics=metrics)
    df = result.to_pandas()

    df.to_csv(output_path, index=False)
    logger.info("Saved evaluation results to %s", output_path)

    # Print summary to stdout
    print("\n── Batch Evaluation Summary ──────────────────")
    for col in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
        if col in df.columns:
            print(f"  {col:<22} avg={df[col].mean():.4f}  min={df[col].min():.4f}  max={df[col].max():.4f}")
    print(f"\n  Total samples evaluated: {len(df)}")
    print("──────────────────────────────────────────────\n")


def _load_jsonl(path: str) -> list[dict]:
    """Load records from a JSONL file.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of parsed JSON objects.
    """
    records = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Batch RAGAS evaluation runner")
    parser.add_argument("--input", required=True, help="Path to input JSONL file")
    parser.add_argument("--output", default="eval_results.csv", help="Path for output CSV")
    args = parser.parse_args()
    run_batch_eval(args.input, args.output)
