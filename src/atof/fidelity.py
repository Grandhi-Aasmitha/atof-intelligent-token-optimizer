"""Conservative, explainable preservation checks over explicitly supplied evidence.

No semantic-equivalence claim. Protects diagnostic anchors before and after
individual transformations; fail closed when a required anchor is missing.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class FidelityResult:
    passed: bool
    reason: str
    anchors_checked: int
    anchors_preserved: int

_ERROR_LINE = re.compile(r'(?:\b[A-Za-z_][\w.]*(?:Error|Exception)\s*:|\bCaused by:|\bTraceback\b)', re.I)
_TEST_LINE = re.compile(r'\b(?:FAILED|FAILURES|ERRORS|AssertionError|[A-Za-z_]+Error|[A-Za-z_]+Exception)\b|^E\s+', re.I)

def _significant_lines(text: str, kind: str) -> set[str]:
    lines = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if kind == 'diff':
            if line[:1] in ('+', '-') and not line.startswith(('+++ ', '--- ')):
                lines.add(line)
        elif kind == 'error' and _ERROR_LINE.search(stripped):
            lines.add(stripped)
        elif kind == 'test' and _TEST_LINE.search(stripped):
            lines.add(stripped)
    return lines

def validate_stage(feature_id: str, original: str, optimized: str, task: str = '') -> FidelityResult:
    if not optimized.strip():
        return FidelityResult(False, 'empty_optimized_context', 0, 0)
    kind = {'coding.code_diff':'diff', 'coding.test_log':'test', 'coding.error_context':'error'}.get(feature_id)
    anchors = _significant_lines(original, kind) if kind else set()
    if feature_id == 'coding.code_context':
        # A requested Python function should not disappear. The legacy code
        # transformer separately validates unresolved dependencies.
        try:
            modules = re.findall(r'(?m)^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(', original)
            mentioned = {name for name in modules if re.search(r'\b' + re.escape(name) + r'\b', task)}
            anchors.update(f'def {name}(' for name in mentioned)
        except (ValueError, re.error):
            return FidelityResult(False, 'code_anchor_inspection_failed', 0, 0)
    present = {anchor for anchor in anchors if anchor in optimized}
    if len(present) != len(anchors):
        return FidelityResult(False, 'required_evidence_missing', len(anchors), len(present))
    return FidelityResult(True, 'required_anchors_preserved', len(anchors), len(present))
