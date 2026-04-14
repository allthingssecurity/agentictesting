"""Token budget enforcement for agent context management."""


class TokenBudgetEnforcer:
    """Estimates token count and enforces budget.

    Uses tiktoken for OpenAI models, falls back to char/4 estimation.
    """

    def __init__(self, budget: int = 16000, model: str = "gpt-5"):
        self.budget = budget
        self.model = model
        self._encoder = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._encoder is None:
            try:
                import tiktoken
                self._encoder = tiktoken.encoding_for_model(self.model)
            except Exception:
                self._encoder = "fallback"

        if self._encoder == "fallback":
            return len(text) // 4

        return len(self._encoder.encode(text))

    def is_over_budget(self, text: str) -> bool:
        return self.count_tokens(text) > self.budget

    def remaining(self, current_text: str) -> int:
        return max(0, self.budget - self.count_tokens(current_text))

    def truncate_to_budget(self, text: str) -> str:
        """Truncate text to fit within budget."""
        if not self.is_over_budget(text):
            return text

        # Binary search for the right truncation point
        low, high = 0, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if self.count_tokens(text[:mid]) <= self.budget:
                low = mid
            else:
                high = mid - 1

        return text[:low]
