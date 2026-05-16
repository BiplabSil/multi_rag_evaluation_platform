# test_orchestrator.py Explained Simply

This file tests the Orchestrator - the "brain" that coordinates the entire RAG pipeline by connecting the retrieval, generator, and evaluator agents together.

---

# 1. What is the Orchestrator?

The Orchestrator is the main pipeline that ties everything together.

It controls the flow:

```
User Question
      ↓
Retrieval Agent (find relevant chunks)
      ↓
Generator Agent (write answer)
      ↓
Evaluator Agent (score quality)
      ↓
Save to Database
      ↓
Return to User
```

---

# 2. The PipelineResult Dataclass

```python
@dataclass
class PipelineResult:
    query_id: str
    question: str
    answer: str
    retrieval: RetrievalResult
    generation: GeneratorResult
    scores: EvalScores
```

This holds the complete output of the entire pipeline:

- **query_id** - Unique identifier for tracking
- **question** - Original user question
- **answer** - Generated answer
- **retrieval** - What was retrieved
- **generation** - How the answer was generated
- **scores** - Quality evaluation scores

---

# 3. Testing _safe_float Function

```python
def test_safe_float_converts_nan():
    import math

    assert _safe_float(float('nan')) == 0.0
    assert _safe_float(float('inf')) == 0.0
    assert _safe_float(-float('inf')) == 0.0
    assert _safe_float(0.95) == 0.95
    assert _safe_float(None) == 0.0
```

This tests a helper function that converts problematic float values to 0.0.

---

# 4. Why Handle NaN and Infinity?

Sometimes calculations produce:

- **NaN** (Not a Number) - Division by zero, invalid math
- **Infinity** - Numbers too large to represent

These break comparisons and sorting.

The _safe_float function converts them to 0.0 so scores work properly.

---

# 5. Testing Valid Float Values

```python
def test_safe_float_preserves_valid_values():
    assert _safe_float(0.0) == 0.0
    assert _safe_float(1.0) == 1.0
    assert _safe_float(0.123) == 0.123
```

Tests that normal float values pass through unchanged.

---

# 6. Testing PipelineResult Creation

```python
def test_pipeline_result_dataclass():
    retrieval = RetrievalResult(query="test", chunks=["chunk"], chunk_ids=["id"], scores=[0.9])
    generation = GeneratorResult(question="test", answer="answer", context=["chunk"])
    scores = EvalScores(0.9, 0.8, 0.7, 0.6, {})

    result = PipelineResult(
        query_id="qid-1",
        question="What is RAG?",
        answer="RAG combines retrieval.",
        retrieval=retrieval,
        generation=generation,
        scores=scores,
    )

    assert result.query_id == "qid-1"
    assert result.question == "What is RAG?"
    assert result.retrieval.chunks == ["chunk"]
```

Tests that the PipelineResult dataclass can be created with all fields.

---

# 7. Testing Orchestrator Initialization

```python
def test_orchestrator_initialization():
    orchestrator = Orchestrator()

    assert orchestrator.retrieval_agent is not None
    assert orchestrator.generator_agent is not None
    assert orchestrator.evaluator_agent is not None
    assert orchestrator.graph is not None
    assert orchestrator.compiled_graph is not None
```

Tests that the Orchestrator creates all its components.

The orchestrator builds a LangGraph workflow (graph) that defines how agents connect.

---

# 8. What is LangGraph?

```python
from langgraph.graph import StateGraph
```

LangGraph is a library for building agent workflows.

It lets you define:

- Nodes (each agent)
- Edges (connections between agents)
- State (shared data)

The orchestrator uses LangGraph to coordinate the pipeline.

---

# 9. Testing Orchestrator Run

```python
@pytest.mark.asyncio
async def test_orchestrator_run_returns_pipeline_result(mock_db_session):
    mock_retrieval = RetrievalResult(...)
    mock_generation = GeneratorResult(...)
    mock_scores = EvalScores(...)

    with (
        patch.object(Orchestrator, "retrieval_node", return_value={"retrieval": mock_retrieval}),
        patch.object(Orchestrator, "generation_node", return_value={"generation": mock_generation}),
        patch.object(Orchestrator, "evaluation_node", new=AsyncMock(return_value={"scores": mock_scores})),
        patch.object(Orchestrator, "persist_node", return_value={"query_id": "qid-1", "scores": mock_scores}),
    ):
        orchestrator = Orchestrator()
        result = await orchestrator.run("What is RAG?", mock_db_session)

    assert isinstance(result, PipelineResult)
    assert result.question == "What is RAG?"
    assert result.scores.faithfulness == 0.95
```

Tests that the orchestrator's run method returns a complete PipelineResult.

Each node is mocked to return fake data.

---

# 10. What Are Nodes?

In LangGraph, a node is a step in the workflow.

The orchestrator has:

- **retrieval_node** - Calls retrieval agent
- **generation_node** - Calls generator agent
- **evaluation_node** - Calls evaluator agent
- **persist_node** - Saves results to database

Each node takes input state, does work, returns updated state.

---

# 11. Testing With Ground Truth

```python
@pytest.mark.asyncio
async def test_orchestrator_with_ground_truth(mock_db_session):
    mock_retrieval = RetrievalResult(query="?", chunks=[], chunk_ids=[], scores=[])
    mock_generation = GeneratorResult(question="?", answer="answer", context=[])
    mock_scores = EvalScores(0.9, 0.8, 0.7, 0.6, {})

    ground_truth = "Expected answer"

    with (
        patch.object(Orchestrator, "retrieval_node", return_value={"retrieval": mock_retrieval}),
        patch.object(Orchestrator, "generation_node", return_value={"generation": mock_generation}),
        patch.object(Orchestrator, "evaluation_node", new=AsyncMock(return_value={"scores": mock_scores})),
        patch.object(Orchestrator, "persist_node", return_value={"query_id": "qid-1", "scores": mock_scores}),
    ):
        orchestrator = Orchestrator()
        result = await orchestrator.run("?", mock_db_session, ground_truth=ground_truth)

    assert isinstance(result, PipelineResult)
```

Tests that ground truth can be passed to the pipeline.

Ground truth helps evaluate context recall.

---

# 12. Testing Node Existence

```python
def test_orchestrator_nodes_exist():
    orchestrator = Orchestrator()

    assert hasattr(orchestrator, "retrieval_node")
    assert hasattr(orchestrator, "generation_node")
    assert hasattr(orchestrator, "evaluation_node")
    assert hasattr(orchestrator, "persist_node")

    assert callable(orchestrator.retrieval_node)
    assert callable(orchestrator.generation_node)
    assert callable(orchestrator.evaluation_node)
    assert callable(orchestrator.persist_node)
```

Tests that all required node methods exist and are callable.

---

# 13. What Does persist_node Do?

```python
def persist_node(self, state: dict) -> dict:
    # 1. Get query_id from state
    # 2. Save to MySQL database
    # 3. Return state
```

The persist node saves the pipeline results to the database.

This allows:

- Historical tracking
- Metrics analysis
- Debugging past queries

---

# 14. Summary of Tests

| Test | What It Checks |
|------|----------------|
| test_safe_float_converts_nan | NaN/Inf converted to 0 |
| test_safe_float_preserves_valid_values | Normal floats preserved |
| test_pipeline_result_dataclass | Result structure works |
| test_orchestrator_initialization | All agents created |
| test_orchestrator_run_returns_pipeline_result | Run returns complete result |
| test_orchestrator_with_ground_truth | Ground truth passed through |
| test_orchestrator_nodes_exist | All nodes exist |

---

# Why Test the Orchestrator?

The orchestrator is the most important component - it connects everything.

Tests ensure:

- All agents are properly connected
- The pipeline runs end-to-end
- Ground truth flows through correctly
- Results are properly structured
- Edge cases are handled

Without testing the orchestrator, you would not know if the full pipeline works.