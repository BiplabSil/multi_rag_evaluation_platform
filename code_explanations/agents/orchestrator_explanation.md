# 1. High-Level Flow of This Orchestrator

The complete flow is:

```text
User Query + DB Session
            ↓
LangGraph Pipeline
            ↓
RetrievalAgent → chunks from Qdrant
            ↓
GeneratorAgent → grounded answer
            ↓
EvaluatorAgent → RAGAS scores
            ↓
PersistNode → save to MySQL
            ↓
Return PipelineResult
```

---

# 2. What is LangGraph?

LangGraph is a library for creating agent workflows.

Instead of sequential code:
```python
retrieval = retrieval_agent.run(query)
generation = generator_agent.run(retrieval)
scores = evaluator_agent.run(generation)
```

LangGraph organizes into a graph:
```text
START → retrieval → generation → evaluation → persist → END
```

---

## Why LangGraph?

| Benefit | Explanation |
|---|---|
| State Management | Passes data between nodes automatically |
| Visualization | Can see the pipeline as a graph |
| Flexibility | Easy to add/remove/modify steps |
| Debugging | Can inspect state at each node |

---

# 3. Imports Explained

```python
import math
```

Used for:
- checking NaN/Infinity values
- _safe_float function

---

```python
from dataclasses import dataclass
```

Creates data classes.

---

```python
from typing import TypedDict
```

Type hint for dictionaries with specific keys.

---

```python
from langgraph.graph import END, START, StateGraph
```

LangGraph core components:
- START: entry point
- END: exit point
- StateGraph: builds the pipeline

---

```python
from sqlalchemy.orm import Session
```

Database session for persisting results.

---

# 4. Helper Function

```python
def _safe_float(value: float) -> float:
```

Converts floats to MySQL-safe values.

---

## Why Needed?

RAGAS can return:
- NaN (Not a Number)
- Infinity

MySQL rejects these values.

---

## Logic

```python
if value is None or math.isnan(value) or math.isinf(value):
    return 0.0
return float(value)
```

- None → 0.0
- NaN → 0.0
- Infinity → 0.0
- Valid float → unchanged

---

# 5. PipelineResult Dataclass

```python
@dataclass
class PipelineResult:
```

Complete output of the entire pipeline.

---

## Fields

```python
query_id: str
```

MySQL row ID of the persisted Query.

---

```python
question: str
```

Original user question.

---

```python
answer: str
```

Generated answer from the LLM.

---

```python
retrieval: RetrievalResult
```

Intermediate retrieval details:
- chunks
- chunk_ids
- scores

---

```python
generation: GeneratorResult
```

Intermediate generation details:
- question
- answer
- context

---

```python
scores: EvalScores
```

Final RAGAS evaluation scores.

---

# 6. PipelineState TypedDict

```python
class PipelineState(TypedDict):
```

Defines what data flows through the graph.

---

## Fields

```python
question: str
```

The user query.

---

```python
db: Session
```

Database session for persistence.

---

```python
ground_truth: str | None
```

Optional reference answer for evaluation.

---

```python
retrieval: RetrievalResult | None
```

Output from retrieval node.

---

```python
generation: GeneratorResult | None
```

Output from generation node.

---

```python
scores: EvalScores | None
```

Output from evaluation node.

---

```python
query_id: str | None
```

ID returned after persisting.

---

# 7. Orchestrator Class

Main pipeline coordinator.

---

# 8. Constructor

```python
def __init__(self) -> None:
```

Initializes all agents and builds the graph.

---

## Initialize Agents

```python
self.retrieval_agent = RetrievalAgent()
self.generator_agent = GeneratorAgent()
self.evaluator_agent = EvaluatorAgent()
```

Creates instances of all three agents.

---

## Build Graph

```python
self.graph = StateGraph(PipelineState)
```

Creates a new graph with PipelineState.

---

## Add Nodes

```python
self.graph.add_node("retrieval", self.retrieval_node)
self.graph.add_node("generation", self.generation_node)
self.graph.add_node("evaluation", self.evaluation_node)
self.graph.add_node("persist", self.persist_node)
```

Four steps in the pipeline.

---

## Add Edges

```python
self.graph.add_edge(START, "retrieval")
self.graph.add_edge("retrieval", "generation")
self.graph.add_edge("generation", "evaluation")
self.graph.add_edge("evaluation", "persist")
self.graph.add_edge("persist", END)
```

Defines the execution order:
```text
START → retrieval → generation → evaluation → persist → END
```

---

## Compile Graph

```python
self.compiled_graph = self.graph.compile()
```

Prepares the graph for execution.

---

# 9. Node Methods

---

## retrieval_node()

```python
def retrieval_node(self, state: PipelineState) -> dict:
    retrieval = self.retrieval_agent.run(state["question"])
    return {"retrieval": retrieval}
```

Takes question from state.
Returns retrieval result.

---

## generation_node()

```python
def generation_node(self, state: PipelineState) -> dict:
    generation = self.generator_agent.run(state["retrieval"])
    return {"generation": generation}
```

Takes retrieval result from state.
Returns generation result.

---

## evaluation_node()

```python
async def evaluation_node(self, state: PipelineState) -> dict:
    scores = await self.evaluator_agent.run(state["generation"], state["ground_truth"])
    return {"scores": scores}
```

Takes generation and ground truth.
Returns evaluation scores.

**Note:** This is async because RAGAS evaluation is async.

---

## persist_node()

```python
def persist_node(self, state: PipelineState) -> dict:
```

The persistence step. More complex — see next section.

---

# 10. persist_node() Deep Dive

---

## Get Data from State

```python
scores = state["scores"]
generation = state["generation"]
retrieval = state["retrieval"]
```

Retrieves all intermediate results.

---

## Sanitize Scores

```python
safe_faithfulness = _safe_float(scores.faithfulness)
safe_answer_relevancy = _safe_float(scores.answer_relevancy)
safe_context_precision = _safe_float(scores.context_precision)
safe_context_recall = _safe_float(scores.context_recall)
```

Converts all scores to safe floats.

---

## Sanitize Raw Scores

```python
safe_raw = {
    k: (0.0 if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
    for k, v in scores.raw.items()
}
```

Converts any NaN/Infinity in raw dict to 0.0.

---

## Create Query Row

```python
query_row = Query(
    question=state["question"],
    answer=generation.answer,
    retrieved_chunk_ids=retrieval.chunk_ids,
)
state["db"].add(query_row)
state["db"].flush()
```

Creates a Query record.

flush() generates the ID without committing.

---

## Create EvalResult Row

```python
eval_row = EvalResult(
    query_id=query_row.id,
    faithfulness=safe_faithfulness,
    answer_relevancy=safe_answer_relevancy,
    context_precision=safe_context_precision,
    context_recall=safe_context_recall,
    raw_scores=safe_raw,
)
state["db"].add(eval_row)
state["db"].commit()
```

Creates an EvalResult record with foreign key.

commit() saves everything to the database.

---

## Update State Scores

```python
scores.faithfulness = safe_faithfulness
scores.answer_relevancy = safe_answer_relevancy
scores.context_precision = safe_context_precision
scores.context_recall = safe_context_recall
```

Updates scores with sanitized values.

---

## Return Final State

```python
return {"query_id": query_row.id, "scores": scores}
```

Returns the query ID and sanitized scores.

---

# 11. run() Method

```python
async def run(
    self,
    question: str,
    db: Session,
    ground_truth: str | None = None,
) -> PipelineResult:
```

Main entry point for the pipeline.

---

## Build Initial State

```python
initial_state: PipelineState = {
    "question": question,
    "db": db,
    "ground_truth": ground_truth,
    "retrieval": None,
    "generation": None,
    "scores": None,
    "query_id": None,
}
```

Packages all input data.

---

## Execute Graph

```python
final_state = await self.compiled_graph.ainvoke(initial_state)
```

Runs the entire pipeline asynchronously.

LangGraph handles:
- Passing state between nodes
- Managing async/sync nodes
- Collecting final results

---

## Return PipelineResult

```python
return PipelineResult(
    query_id=final_state["query_id"],
    question=question,
    answer=final_state["generation"].answer,
    retrieval=final_state["retrieval"],
    generation=final_state["generation"],
    scores=final_state["scores"],
)
```

Packages everything into a single result object.

---

# 12. Complete Flow Visualization

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│   │          │    │          │    │          │    │          │   │
│   │retrieval │───▶│generation│───▶│evaluation│───▶│  persist │   │
│   │  _node   │    │   _node  │    │   _node  │    │   _node  │   │
│   │          │    │          │    │          │    │          │   │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│        │              │               │               │          │
│        ▼              ▼               ▼               ▼          │
│   RetrievalResult  GeneratorResult   EvalScores      query_id     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

# 13. Data Flow Through Nodes

| Node | Input | Output |
|---|---|---|
| retrieval_node | question | RetrievalResult |
| generation_node | RetrievalResult | GeneratorResult |
| evaluation_node | GeneratorResult | EvalScores |
| persist_node | EvalScores | query_id |

---

# 14. Why Two-Step Persistence?

```python
query_row = Query(...)
state["db"].flush()  # Gets ID

eval_row = EvalResult(query_id=query_row.id, ...)
state["db"].commit()  # Saves both
```

Two-step because:
1. Query needs to exist first (for foreign key)
2. Flush gets the ID without committing
3. Commit saves both together (transaction)

---

# 15. Async/Sync Mix

```python
async def evaluation_node(...)  # Async
def persist_node(...)            # Sync
```

Why mix?

- Evaluation: calls LLM APIs (slow) → async
- Persistence: database operations (fast) → sync

LangGraph handles this automatically.

---

# 16. Final Architecture Summary

```text
QUESTION + DB SESSION
         │
         ▼
    ┌─────────────┐
    │  LangGraph  │
    │   Pipeline  │
    └─────────────┘
         │
         ▼
┌────────┴────────┬───────────┬────────────┐
│                 │           │            │
▼                 ▼           ▼            ▼
RETRIEVAL    GENERATION   EVALUATION    PERSIST
   │             │            │            │
   ▼             ▼            ▼            ▼
chunks       answer       scores       MySQL
                                               │
                                               ▼
                                    PipelineResult
```

---

# 17. Why This Orchestrator Is Production-Grade

| Feature | Purpose |
|---|---|
| LangGraph | Structured, visualizable pipeline |
| State Management | Clean data flow between nodes |
| Async Support | Handles slow LLM calls |
| Safe Floats | Prevents database errors |
| Transaction | Atomic persistence |
| TypedDict | Type safety, IDE support |
| Modular Nodes | Easy to modify/replace steps |

---

# 18. Industry-Level Understanding

This orchestrator pattern is used in:

- **LangChain Agents**: sequential tool execution
- **AutoGPT**: autonomous agent loops
- **Microsoft Semantic Kernel**: skill orchestration
- **LlamaIndex**: query pipelines
- **Enterprise RAG**: multi-stage retrieval

The key insight:
> Complex AI workflows are best expressed as graphs of simple, composable nodes.

Each node does one thing well, and LangGraph coordinates them.
