"""Memory compaction via sliding window and LLM summarization."""

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage

from testforge.llm import get_llm

SUMMARIZE_PROMPT = """\
Summarize the following agent conversation into a concise paragraph.
Focus on: what tools were called, what results were found, what decisions were made,
and any errors encountered. Be specific about test names, file paths, and findings.
Keep it under 200 words.
"""


class SlidingWindowCompactor:
    """Compacts message history by summarizing older messages."""

    def __init__(self, window_size: int = 10, model: str = "gpt-5"):
        self.window_size = window_size
        self.model = model

    def compact(self, messages: list[AnyMessage]) -> tuple[str, list[AnyMessage]]:
        """Compact messages. Returns (summary_of_old, recent_messages).

        If messages fit in window, returns empty summary and all messages.
        Otherwise, summarizes older messages and keeps recent ones.
        """
        if len(messages) <= self.window_size:
            return "", messages

        old_messages = messages[:-self.window_size]
        recent_messages = messages[-self.window_size:]

        summary = self._summarize(old_messages)
        return summary, recent_messages

    def _summarize(self, messages: list[AnyMessage]) -> str:
        """Use LLM to summarize a batch of messages."""
        # Build a text representation of messages
        text_parts = []
        for msg in messages:
            role = type(msg).__name__.replace("Message", "")
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            text_parts.append(f"[{role}] {content[:500]}")

        conversation_text = "\n".join(text_parts)

        llm = get_llm(model=self.model)
        response = llm.invoke([
            SystemMessage(content=SUMMARIZE_PROMPT),
            HumanMessage(content=conversation_text[:8000]),
        ])

        return response.content if isinstance(response.content, str) else str(response.content)


def compact_messages_for_agent(
    messages: list[AnyMessage],
    prior_summary: str = "",
    window_size: int = 10,
    model: str = "gpt-5",
) -> tuple[str, list[AnyMessage]]:
    """Helper: compact messages and prepend prior summary context.

    Returns (updated_summary, windowed_messages_with_context).
    """
    compactor = SlidingWindowCompactor(window_size=window_size, model=model)
    new_summary, recent = compactor.compact(messages)

    combined_summary = prior_summary
    if new_summary:
        combined_summary = f"{prior_summary}\n{new_summary}" if prior_summary else new_summary

    return combined_summary, recent
