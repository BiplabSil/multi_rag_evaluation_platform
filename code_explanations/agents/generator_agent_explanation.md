# 1. High-Level Flow of This Generator Agent

The complete flow is:

```text
RetrievalResult (chunks + query)
            ↓
Build Context Block
            ↓
Format Messages (System + User)
            ↓
Call LLM (ChatOpenAI)
            ↓
Extract Answer
            ↓
Return GeneratorResult
```

---

# 2. Imports Explained

```python
from dataclasses import dataclass
```

Same as before — creates clean data classes.

---

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
```

LangChain wrappers for OpenAI chat API.

Why LangChain?
- Better prompt management
- LangSmith tracing support
- Message abstraction

---

```python
from agents.retrieval_agent import RetrievalResult
```

Imports the output from the retrieval agent.

Contains:
- query
- chunks
- chunk_ids
- scores

---

```python
from core.config import get_settings
```

Loads application settings (API keys, model names).

---

# 3. Global Objects

```python
_settings = get_settings()
```

Loads configuration once at module load.

---

```python
_llm = ChatOpenAI(
    model=_settings.openai_model,
    api_key=_settings.openai_api_key,
    temperature=0.0,
)
```

Creates the LLM client.

---

## Why temperature=0.0?

Temperature controls randomness:
- 0.0 = deterministic output
- 1.0 = creative/random output

For evaluation:
- Want reproducible results
- Same input → same output
- Fair comparison across runs

---

# 4. System Prompt

```python
_SYSTEM_PROMPT = """You are a precise question-answering assistant.
...
"""
```

The instructions that guide the LLM's behavior.

---

## Rule 1: Context Only

```python
"Answer ONLY using the information in the provided context."
```

Prevents hallucination.

The LLM can ONLY use information from the chunks.

---

## Rule 2: Unknown Response

```python
"If the context does not contain enough information, respond with:
 'I don't have enough context to answer this question.'"
```

Explicit fallback when context is insufficient.

---

## Rule 3: Conciseness

```python
"Be concise. Do not add information beyond what the context provides."
```

Prevents:
- Verbose answers
- Adding unverified information
- Going beyond the context

---

## Rule 4: No Citations

```python
"Cite the context implicitly (do not use footnotes)."
```

Cleaner output without citation noise.

---

# 5. GeneratorResult Dataclass

```python
@dataclass
class GeneratorResult:
```

Stores the final output of the generator.

---

## Fields

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
context: list[str]
```

The chunks that were used to generate the answer.

---

# 6. GeneratorAgent Class

Main generation engine.

---

# 7. _build_context_block()

```python
def _build_context_block(self, chunks: list[str]) -> str:
```

Formats retrieved chunks for the prompt.

---

## Input

```python
[
    "LangChain is a framework...",
    "RAG combines retrieval and generation..."
]
```

---

## Output

```python
"""[1] LangChain is a framework...

[2] RAG combines retrieval and generation..."""
```

---

## Why Numbered Format?

The LLM can reference specific chunks:
- "According to [1], LangChain..."
- Helps with faithfulness evaluation

---

## Implementation

```python
lines = [f"[{i + 1}] {chunk}" for i, chunk in enumerate(chunks)]
return "\n\n".join(lines)
```

- Enumerates chunks (0, 1, 2, ...)
- Adds 1 to start from 1
- Joins with double newlines for separation

---

# 8. run() Method

```python
def run(self, retrieval_result: RetrievalResult) -> GeneratorResult:
```

Main entry point.

---

## Step 1: Build Context Block

```python
context_block = self._build_context_block(retrieval_result.chunks)
```

Formats chunks into numbered format.

---

## Step 2: Build User Message

```python
user_message = (
    f"Context:\n{context_block}\n\n"
    f"Question: {retrieval_result.query}"
)
```

Combines context + question.

Example:
```text
Context:
[1] LangChain is a framework...

[2] RAG combines retrieval and generation...

Question: What is LangChain?
```

---

## Step 3: Create Messages

```python
messages = [
    SystemMessage(content=_SYSTEM_PROMPT),
    HumanMessage(content=user_message),
]
```

LangChain message format:
- SystemMessage: instructions
- HumanMessage: actual user input

---

## Step 4: Call LLM

```python
response = _llm.invoke(messages)
answer = response.content.strip()
```

Sends to OpenAI API.

---

## Step 5: Return Result

```python
return GeneratorResult(
    question=retrieval_result.query,
    answer=answer,
    context=retrieval_result.chunks,
)
```

Packages everything together.

---

# 9. Complete Example

Input:
```python
retrieval_result = RetrievalResult(
    query="What is RAG?",
    chunks=[
        "RAG stands for Retrieval-Augmented Generation.",
        "It combines a retrieval system with an LLM."
    ],
    chunk_ids=["chunk_1", "chunk_2"],
    scores=[0.9, 0.8]
)
```

Internal Messages:
```python
SystemMessage: "You are a precise question-answering assistant..."

HumanMessage: """
Context:
[1] RAG stands for Retrieval-Augmented Generation.

[2] It combines a retrieval system with an LLM.

Question: What is RAG?
"""
```

Output:
```python
GeneratorResult(
    question="What is RAG?",
    answer="RAG stands for Retrieval-Augmented Generation. It combines a retrieval system with an LLM.",
    context=["RAG stands for Retrieval-Augmented Generation.", "It combines a retrieval system with an LLM."]
)
```

---

# 10. Anti-Hallucination Strategy

This agent has multiple safeguards:

| Safeguard | How |
|---|---|
| System Prompt | Explicit "answer only from context" |
| Temperature 0.0 | Deterministic, no creative additions |
| Conciseness Rule | Prevents verbose hallucinations |
| Fallback Response | Explicit "don't know" when unsure |

---

# 11. Final Architecture Summary

```text
RETRIEVAL RESULT
      ↓
FORMAT CHUNKS [1], [2], [3]
      ↓
BUILD USER MESSAGE
      ↓
ADD SYSTEM PROMPT
      ↓
INVOKE LLM
      ↓
EXTRACT ANSWER
      ↓
RETURN GeneratorResult
```

---

# 12. Why This Generator Is Simple But Effective

| Aspect | Design Choice |
|---|---|
| Simple Prompt | Easy to understand, modify |
| Numbered Chunks | Clear reference, better answers |
| Temperature 0.0 | Reproducible evaluation |
| Single-Shot | Fast, no complex chains |
| Direct API | Minimal overhead |

---

# 13. Industry-Level Understanding

This generator uses the simplest effective RAG pattern:

1. Retrieve relevant chunks
2. Format into prompt
3. Ask LLM to answer

This is the foundation that enterprise RAG systems build upon with:
- More sophisticated prompts
- Citation verification
- Multi-turn refinement
- Query decomposition

But the core principle remains: **ground the LLM in retrieved context**.
