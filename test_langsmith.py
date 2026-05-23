import os
from core.config import get_settings

# Load settings
settings = get_settings()

# Check if LangSmith tracing is enabled
print("LANGSMITH_TRACING setting:", settings.langsmith_tracing)
print("LANGSMITH_API_KEY setting:", settings.langsmith_api_key[:10] + "..." if settings.langsmith_api_key else "Not set")
print("LANGSMITH_PROJECT setting:", settings.langsmith_project)

# Check environment variables
print("\nEnvironment variables:")
print("LANGCHAIN_TRACING_V2:", os.environ.get("LANGCHAIN_TRACING_V2", "Not set"))
print("LANGSMITH_TRACING:", os.environ.get("LANGSMITH_TRACING", "Not set"))
print("LANGSMITH_ENDPOINT:", os.environ.get("LANGSMITH_ENDPOINT", "Not set"))
print("LANGSMITH_API_KEY env:", os.environ.get("LANGSMITH_API_KEY", "Not set")[:10] + "..." if os.environ.get("LANGSMITH_API_KEY") else "Not set")
print("LANGSMITH_PROJECT env:", os.environ.get("LANGSMITH_PROJECT", "Not set"))

# Test evaluator agent
try:
    from agents.evaluator_agent import EvaluatorAgent
    print("\nEvaluator agent imported successfully")

    # Check if LangChain tracing is enabled in the agent
    import asyncio
    from agents.generator_agent import GeneratorResult

    # Create a simple test
    result = GeneratorResult(
        question="Test question",
        answer="Test answer",
        context=["Test context"]
    )

    print("Testing evaluator agent...")
    print("Original LANGCHAIN_TRACING_V2:", os.environ.get("LANGCHAIN_TRACING_V2", "Not set"))

except Exception as e:
    print(f"Error testing evaluator agent: {e}")