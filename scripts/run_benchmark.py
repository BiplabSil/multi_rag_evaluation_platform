import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
import statistics
import sys

from agents.retrieval_agent import RetrievalAgent
from agents.generator_agent import GeneratorAgent
from agents.evaluator_agent import EvaluatorAgent

THRESHOLD = 0.7


async def evaluate_question(sample):
    question = sample["question"]
    ground_truth = sample["ground_truth"]

    print(f"\nRunning benchmark for: {question}")

    retrieval = RetrievalAgent()
    retrieval_result = retrieval.run(question)

    generator = GeneratorAgent()
    generator_result = generator.run(
        question=question,
        contexts=retrieval_result.chunks,
    )

    evaluator = EvaluatorAgent()

    scores = await evaluator.run(
        generator_result=generator_result,
        ground_truth=ground_truth,
    )

    print("Faithfulness:", scores.faithfulness)
    print("Answer Relevancy:", scores.answer_relevancy)
    print("Context Precision:", scores.context_precision)
    print("Context Recall:", scores.context_recall)

    return scores


async def main():
    with open("benchmarks/benchmark_dataset.json", "r") as f:
        dataset = json.load(f)

    results = []

    for sample in dataset:
        score = await evaluate_question(sample)
        results.append(score)

    avg_faithfulness = statistics.mean(
        [r.faithfulness for r in results]
    )

    avg_answer_relevancy = statistics.mean(
        [r.answer_relevancy for r in results]
    )

    avg_context_precision = statistics.mean(
        [r.context_precision for r in results]
    )

    avg_context_recall = statistics.mean(
        [r.context_recall for r in results]
    )

    print("\n========== FINAL SCORES ==========")

    print("Average Faithfulness:", avg_faithfulness)
    print("Average Answer Relevancy:", avg_answer_relevancy)
    print("Average Context Precision:", avg_context_precision)
    print("Average Context Recall:", avg_context_recall)

    failed = any([
        avg_faithfulness < THRESHOLD,
        avg_answer_relevancy < THRESHOLD,
        avg_context_precision < THRESHOLD,
        avg_context_recall < THRESHOLD,
    ])

    if failed:
        print("\nBenchmark FAILED")
        sys.exit(1)

    print("\nBenchmark PASSED")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())