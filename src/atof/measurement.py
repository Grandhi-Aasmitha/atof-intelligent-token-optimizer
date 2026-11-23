"""Measurement distinguishes local estimates from provider usage.

For defensible savings claims use matched ON/OFF provider usage with identical
model, task, cache conditions and correctness validation; this module does not
fabricate provider receipts.
"""
from __future__ import annotations
from dataclasses import dataclass
from .legacy.tokens import estimate_text

@dataclass(frozen=True)
class Estimate:
    original_tokens: int
    optimized_tokens: int
    reduction_tokens: int
    reduction_percent: float
    method: str = 'local_heuristic_estimate'


def compare_context(original: str, optimized: str) -> Estimate:
    before = estimate_text(original)
    after = estimate_text(optimized)
    reduction = max(0, before - after)
    return Estimate(before, after, reduction, round((100 * reduction / before), 2) if before else 0.0)
