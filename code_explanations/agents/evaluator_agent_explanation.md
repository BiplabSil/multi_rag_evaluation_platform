# 1. High-Level Flow of This Evaluator Agent

The complete flow is:

```text
GeneratorResult (answer + context)
            ↓
Prepare RAGAS Dataset
            ↓
Set Embeddings for Metrics
            ↓
Call RAGAS evaluate (async)
            ↓
Extract Scores (faithfulness, answer_relevancy, context_precision, context_recall)
            ↓
(Optional) Post GitHub Status Check
            ↓
Return EvalScores
```

---

# 2. Imports Explained

```python
import asyncio
```

Used for:
- running code concurrently
- prevents blocking while waiting for LLM calls

Example:
```python
await asyncio.to_thread(evaluate, dataset, metrics=metrics)
```

---

```python
import logging
```

Used for:
- tracking what happens during execution
- debugging issues

Example:
```python
logger = logging.getLogger(__name__)
logger.info("Evaluation complete")
```

---

```python
from dataclasses import dataclass
```

Same as before — creates clean data classes.

---

```python
import requests
```

Used to call external APIs.

Here:
- used for GitHub status check API.

---

```python
from datasets import Dataset
```

HuggingFace datasets library.

Used to:
- format data for RAGAS evaluation
- RAGAS expects HuggingFace Dataset format

Example:
```python
dataset = Dataset.from_dict({"question": ["..."], "answer": ["..."]})
```

---

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
```

RAGAS = Retrieval-Augmented Generation Assessment

A framework for evaluating RAG pipelines using LLMs.

---

```python
from agents.generator_agent import GeneratorResult
```

Imports the output from the generator agent.

---

# 3. RAGAS Metrics Explained

# What is RAGAS?

RAGAS = Retrieval-Augmented Generation Assessment

It evaluates RAG quality using LLM calls.

---

# Faithfulness

**Question:** Does the answer only say things supported by the context?

Example:

Context:
```text
"The capital of France is Paris."
```

Good Answer:
```text
"Paris is the capital of France."
```
✅ Faithful — all facts come from context.

Bad Answer:
```text
"Paris is the capital of France and the largest city in Europe."
```
❌ Not faithful — "largest city in Europe" not in context.

---

# Answer Relevancy

**Question:** Is the answer on-topic for the question?

Example:

Question:
```text
"What is Python?"
```

Good Answer:
```text
"Python is a programming language known for its simple syntax."
```
✅ Relevant — directly answers the question.

Bad Answer:
```text
"Python is a type of snake found in tropical regions."
```
❌ Not relevant — wrong topic!

---

# Context Precision

**Question:** Are the retrieved chunks actually about the question?

Example:

Question:
```text
"How does caching work?"
```

Good Chunks:
```text
- "Caching stores frequently accessed data..."
- "Cache invalidation clears old entries..."
```
✅ Precise — chunks are relevant to caching.

Bad Chunks:
```text
- "Database normalization techniques..."
- "Network routing protocols..."
```
❌ Not precise — chunks are about different topics.

---

# Context Recall

**Question:** Did we retrieve ALL the chunks needed to answer?

This metric:
- Requires ground truth answer
- Compares ground truth with retrieved context
- Measures if context contains all necessary information

Example:

Ground Truth:
```text
"To make coffee, you need water, coffee beans, and a brewing method."
```

Retrieved Context:
```text
"You need coffee beans and water to make coffee."
```

Recall = Partial — missing "brewing method" information.

---

# 4. EvalScores Dataclass

```python
@dataclass
class EvalScores:
```

Stores all evaluation results.

---

## Fields

```python
faithfulness: float
```

Score: 0.0–1.0
Higher is better.

---

```python
answer_relevancy: float
```

Score: 0.0–1.0
Higher is better.

---

```python
context_precision: float
```

Score: 0.0–1.0
Higher is better.

---

```python
context_recall: float
```

Score: 0.0–1.0
Higher is better.
= 0.0 when no ground truth provided.

---

```python
raw: dict
```

Full RAGAS output for debugging.

---

# 5. EvaluatorAgent Class

Main evaluation engine.

---

# 6. Constructor (run method)

```python
async def run(
    self,
    generator_result: GeneratorResult,
    ground_truth: str | None = None,
    enable_github_check: bool = False,
) -> EvalScores:
```

---

## Parameters

```python
generator_result: GeneratorResult
```

Output from the Generator Agent.
Contains:
- question
- answer
- context

---

```python
ground_truth: str | None = None
```

Optional reference answer.

Why optional?
- Faithfulness, answer_relevancy, context_precision work without it
- Context_recall requires it

---

```python
enable_github_check: bool = False
```

If True:
- posts results to GitHub API
- used for CI/CD pipelines
- default: skip for user queries

---

# 7. Ground Truth Logic

```python
has_ground_truth = ground_truth and ground_truth.strip()
```

Checks if ground truth is provided and non-empty.

---

## Metrics Selection

```python
base_metrics = [faithfulness, answer_relevancy, context_precision]
```

These 3 metrics work WITHOUT ground truth.

---

```python
if has_ground_truth:
    metrics = base_metrics + [context_recall]
```

Adds context_recall only when ground truth is available.

---

## Why Not Always Include Context Recall?

Because:
- It requires a reference answer
- User queries often don't have ground truth
- Makes the evaluator flexible for different use cases

---

# 8. Embeddings Setup

```python
for metric in base_metrics:
    metric.embeddings = _embeddings
```

RAGAS uses embeddings for some metrics.

Why set them?
- Prevents NaN issues
- Ensures consistent evaluation
- Uses OpenAI's text-embedding-3-small

---

# 9. Dataset Preparation

```python
sample = {
    "question": [generator_result.question],
    "answer": [generator_result.answer],
    "contexts": [generator_result.context],
    "ground_truth": [ground_truth or ""],
}
dataset = Dataset.from_dict(sample)
```

Converts to HuggingFace Dataset format.

RAGAS expects these column names:
- question
- answer
- contexts (list of strings)
- ground_truth

---

# 10. Async Evaluation

```python
result = await asyncio.to_thread(evaluate, dataset, metrics=metrics)
```

Runs RAGAS evaluation in a thread.

Why asyncio?
- RAGAS calls LLM APIs (slow)
- Don't block the main thread
- Keep the app responsive

---

## LangChain Tracing Cleanup

```python
original = os.environ.get("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_TRACING_V2"] = "false"
```

Disables LangChain tracing during evaluation.

Why?
- RAGAS has its own tracing
- Prevents duplicate/conflicting traces
- Restored after evaluation

---

# 11. Safe Float Extraction

```python
def safe_float(value, default=0.0):
```

RAGAS sometimes returns NaN.

Why?
- When context is empty
- When answer is too short
- When metric can't be computed

---

## Logic

```python
if value is None:
    return default
if math.isnan(value):
    return default
```

Converts invalid values to 0.0.

Why 0.0?
- Safe for database storage
- Clear indicator of failure
- Prevents crashes

---

# 12. Score Extraction

```python
scores = EvalScores(
    faithfulness=safe_float(scores_dict.get("faithfulness")),
    answer_relevancy=safe_float(scores_dict.get("answer_relevancy")),
    context_precision=safe_float(scores_dict.get("context_precision")),
    context_recall=safe_float(scores_dict.get("context_recall")) if has_ground_truth else 0.0,
    raw=scores_dict,
)
```

Extracts individual scores from RAGAS output.

---

## Context Recall Special Case

```python
context_recall=safe_float(...) if has_ground_truth else 0.0
```

When no ground truth:
- Context recall = 0.0
- Not computed (can't be)

---

# 13. GitHub Check Feature

```python
async def _trigger_github_check(
    self, scores: EvalScores, question: str, computed_metrics: list[str]
) -> None:
```

Posts evaluation results to GitHub API.

Used for CI/CD quality gates.

---

## Why?

Enterprise teams want:
- Automated quality checks
- Fail builds when quality drops
- Track quality over time

---

## Threshold Check

```python
threshold = settings.github_failure_threshold
failed = [(name, value) for name, value in metrics_to_check if value < threshold]
```

Compares each metric against threshold.

---

## Conclusion

```python
conclusion = "success" if not failed else "failure"
```

GitHub status:
- Success: all metrics above threshold
- Failure: any metric below threshold

---

## API Payload

```python
payload = {
    "state": conclusion,
    "description": "RAG benchmark",
    "context": "ragas-eval",
}
```

Posts to GitHub commit status API.

---

# 14. Final Architecture Summary

```text
GENERATOR RESULT
      ↓
PREPARE DATASET
      ↓
SET EMBEDDINGS
      ↓
RAGAS EVALUATE (async)
      ↓
EXTRACT SCORES
      ↓
SAFE FLOAT CONVERSION
      ↓
(optional) GITHUB STATUS
      ↓
RETURN EvalScores
```

---

# 15. Why This Evaluator Is Production-Grade

| Feature | Purpose |
|---|---|
| Async Execution | Non-blocking evaluation |
| Safe Float Handling | Prevents NaN crashes |
| Flexible Metrics | Works with/without ground truth |
| GitHub Integration | CI/CD quality gates |
| Embedding Setup | Consistent evaluation |
| Logging | Debugging support |
| Context Recall Skip | Graceful degradation |

---

# 16. Industry-Level Understanding

This evaluator follows RAGAS best practices:

- Uses LLM-based evaluation (not heuristics)
- Provides multiple perspectives on quality
- Separates retrieval from generation quality
- Enables automated quality monitoring
- Integrates with development workflow

This is similar to how:
- OpenAI evaluates their models
- Enterprise RAG systems track quality
- Research papers benchmark RAG approaches
