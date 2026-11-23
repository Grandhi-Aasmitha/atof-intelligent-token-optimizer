"""Model-agnostic ESTIMATES. Provider usage fields are the billing source of truth."""
import json
import re
from decimal import Decimal
from typing import Any

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def estimate_text(value: Any) -> int:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if not value:
        return 0
    # Fast deterministic approximation; never represented as exact provider token count.
    return max(1, sum(max(1, (len(piece) + 3) // 4) for piece in _TOKEN_PATTERN.findall(value)))


def estimate_messages(messages: list[dict]) -> int:
    return sum(4 + estimate_text(m) for m in messages) + 3


def usage_counts(usage: dict) -> tuple[int, int, int | None]:
    """Validate Chat Completions usage; cached input is a subset, never additive."""
    if not isinstance(usage, dict):
        raise ValueError("Provider usage must be an object")
    prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
    details = usage.get("prompt_tokens_details") or {}
    if not isinstance(details, dict):
        raise ValueError("Provider prompt token details must be an object")
    cached = details.get("cached_tokens")
    for value in (prompt, completion):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 50_000_000:
            raise ValueError("Provider input and output token counts must be nonnegative bounded integers")
    if cached is not None and (isinstance(cached, bool) or not isinstance(cached, int) or not 0 <= cached <= prompt):
        raise ValueError("Provider cached input must be a nonnegative subset of input")
    return prompt, completion, cached


def usage_cost(usage: dict, rates: dict | None) -> str | None:
    """USD using operator-supplied per-million rates; unknown cache pricing stays unknown."""
    prompt, completion, cached = usage_counts(usage)
    if rates is None or cached is None:
        return None
    prices = []
    for key in ("input", "cached_input", "output"):
        if key not in rates:
            return None
        price = Decimal(str(rates[key]))
        if not price.is_finite() or price < 0:
            raise ValueError("Token prices must be finite nonnegative USD per million")
        prices.append(price)
    return str(((prompt - cached) * prices[0] + cached * prices[1] + completion * prices[2]) / Decimal(1_000_000))
