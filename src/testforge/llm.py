from functools import lru_cache

from langchain_openai import ChatOpenAI


@lru_cache
def get_llm(
    model: str = "gpt-5",
    temperature: float = 0.0,
    max_retries: int = 3,
) -> ChatOpenAI:
    """Configurable LLM factory. Model can be overridden from manifest."""
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_retries=max_retries,
    )
