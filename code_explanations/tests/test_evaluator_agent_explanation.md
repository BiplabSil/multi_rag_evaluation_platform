# test_evaluator_agent.py Explained Simply

This file tests the EvaluatorAgent - the component that measures how good the RAG pipeline's responses are.

---

# 1. What Does the EvaluatorAgent Do?

The EvaluatorAgent evaluates RAG pipeline quality using RAGAS (RAG Assessment).

RAGAS is a framework that measures:

- **Faithfulness** - Does the answer match the retrieved context?
- **Answer Relevancy** - Is the answer relevant to the question?
- **Context Precision** - Are the most relevant chunks ranked highest?
- **Context Recall** - Does the context contain the answer?

---

# 2. The EvalScores Dataclass

```python
@dataclass
class EvalScores:
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    raw: dict = field(default_factory=dict)
```

This stores evaluation results.

Each score is a float between 0 and 1:

- 1.0 = perfect score
- 0.0 = worst score

---

# 3. What is a Dataclass?

```python
from dataclasses import dataclass

@dataclass
class EvalScores:
    faithfulness: float
```

A dataclass is a Python class that automatically creates:

- `__init__` (constructor)
- `__repr__` (string representation)
- Comparison methods

Instead of:

```python
class EvalScores:
    def __init__(self, faithfulness):
        self.faithfulness = faithfulness
```

You just write:

```python
@dataclass
class EvalScores:
    faithfulness: float
```

---

# 4. Sample Data for Testing

```python
@pytest.fixture
def sample_generator_result():
    return GeneratorResult(
        question="What is RAG?",
        answer="RAG combines retrieval and generation.",
        context=["RAG combines retrieval and generation.", "RAGAS evaluates RAG pipelines."],
    )
```

This is a fake output from the GeneratorAgent.

The evaluator will evaluate this sample result.

---

# 5. Mocking RAGAS

```python
class MockRow:
    def __init__(self):
        self._data = {
            "faithfulness": 0.95,
            "answer_relevancy": 0.90,
            "context_precision": 0.88,
            "context_recall": 0.85,
        }
    def to_dict(self):
        return self._data

mock_df = MagicMock()
mock_df.iloc = [MockRow()]
```

RAGAS is an external library that calls APIs to compute scores.

We mock it because:

- Real RAGAS calls OpenAI (costs money)
- Network calls are slow
- We just need to test our code logic

---

# 6. Testing Evaluator Returns Scores

```python
@pytest.mark.asyncio
async def test_evaluator_returns_scores(sample_generator_result, mock_ragas_result):
    with patch("agents.evaluator_agent.evaluate", return_value=mock_ragas_result):
        with patch("agents.evaluator_agent._embeddings", MagicMock()):
            agent = EvaluatorAgent()
            result = await agent.run(sample_generator_result)

    assert isinstance(result, EvalScores)
    assert 0.0 <= result.faithfulness <= 1.0
    assert result.answer_relevancy == 0.90
```

This test checks that the evaluator returns an EvalScores object with valid values.

---

# 7. Why @pytest.mark.asyncio?

```python
@pytest.mark.asyncio
async def test_evaluator_returns_scores(...):
```

The EvaluatorAgent.run() is an async function.

pytest-asyncio lets you test async functions directly.

Without this marker, pytest would not know how to run the async test.

---

# 8. Testing Without Ground Truth

```python
@pytest.mark.asyncio
async def test_evaluator_without_ground_truth(sample_generator_result, mock_ragas_result):
    with patch("agents.evaluator_agent.evaluate", return_value=mock_ragas_result):
        agent = EvaluatorAgent()
        result = await agent.run(sample_generator_result, ground_truth=None)

    assert result.context_recall == 0.0
```

When no ground truth is provided, context_recall cannot be computed.

The evaluator sets it to 0.0 as a default.

---

# 9. What is Ground Truth?

Ground truth is the correct expected answer.

Example:

```
Question: "What is RAG?"
Ground Truth: "RAG is retrieval-augmented generation"
```

With ground truth, the evaluator can check if the retrieved context contains the expected information.

---

# 10. Testing With Ground Truth

```python
@pytest.mark.asyncio
async def test_evaluator_with_ground_truth(sample_generator_result, mock_ragas_result):
    with patch("agents.evaluator_agent.evaluate", return_value=mock_ragas_result):
        agent = EvaluatorAgent()
        result = await agent.run(
            sample_generator_result,
            ground_truth="RAG is retrieval-augmented generation."
        )

    assert isinstance(result, EvalScores)
```

When ground truth is provided, context_recall can be computed properly.

---

# 11. Testing NaN Handling

```python
@pytest.mark.asyncio
async def test_safe_float_handles_nan(sample_generator_result):
    mock_df = MagicMock()
    mock_df.iloc = [MagicMock(to_dict=lambda: {
        "faithfulness": float('nan'),
        "answer_relevancy": 0.90,
        "context_precision": 0.88,
        "context_recall": 0.85,
    })]

    with patch("agents.evaluator_agent.evaluate", return_value=mock_df):
        agent = EvaluatorAgent()
        result = await agent.run(sample_generator_result)

    assert result.faithfulness == 0.0 or math.isnan(result.faithfulness) == False
```

Sometimes RAGAS returns NaN (Not a Number).

The code should handle this gracefully by converting NaN to 0.0.

---

# 12. What is NaN?

NaN stands for "Not a Number".

It happens when:

- Dividing by zero
- Invalid mathematical operations
- Missing data in calculations

In scores, NaN is problematic because:

- Cannot compare scores
- Breaks sorting
- Causes errors in downstream code

---

# 13. Testing the EvalScores Dataclass

```python
def test_eval_scores_dataclass():
    scores = EvalScores(
        faithfulness=0.95,
        answer_relevancy=0.90,
        context_precision=0.88,
        context_recall=0.85,
        raw={"faithfulness": 0.95},
    )

    assert scores.faithfulness == 0.95
    assert scores.raw["faithfulness"] == 0.95
```

Simple test to verify the EvalScores dataclass works correctly.

---

# 14. What is the raw Field?

```python
raw: dict = field(default_factory=dict)
```

The `raw` field stores the original RAGAS output before processing.

Useful for:

- Debugging
- Logging
- Detailed analysis

---

# 15. Summary of Tests

| Test | What It Checks |
|------|----------------|
| test_evaluator_returns_scores | Evaluator returns EvalScores |
| test_evaluator_without_ground_truth | Ground truth optional, defaults context_recall to 0 |
| test_evaluator_with_ground_truth | Ground truth enables full evaluation |
| test_safe_float_handles_nan | NaN values converted to 0 |
| test_eval_scores_dataclass | EvalScores dataclass works |

---

# Why Test the Evaluator?

The evaluator is critical for measuring RAG quality.

Tests ensure:

- Scores are calculated correctly
- Edge cases (NaN, no ground truth) are handled
- The dataclass works as expected
- Integration with RAGAS is correct

Without testing, you would not know if your evaluation is accurate.