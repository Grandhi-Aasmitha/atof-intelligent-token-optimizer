"""Opt-in, reversible compression of consecutive identical evidence lines."""
import re
from itertools import groupby
from .base import EngineResult, PluginSpec
from ..legacy.tokens import estimate_text

MARKER = '[ATOF repeat x'
PATTERN = re.compile(r'\[ATOF repeat x([1-9][0-9]{0,5})\]\n')


def encode(text: str) -> str:
    if MARKER in text:
        return text
    parts = []
    for line, group in groupby(text.splitlines(keepends=True)):
        count = sum(1 for _ in group)
        if count >= 4 and line.endswith('\n') and count <= 999999:
            candidate = f'{MARKER}{count}]\n{line}'
            original = line * count
            parts.append(candidate if estimate_text(candidate) < estimate_text(original) else original)
        else:
            parts.append(line * count)
    return ''.join(parts)


def restores(original: str, candidate: str) -> bool:
    """Independently reconstruct, with an expansion bound from original size."""
    if MARKER in original:
        return False
    result = []
    size = 0
    lines = iter(candidate.splitlines(keepends=True))
    for line in lines:
        if line.startswith(MARKER):
            match = PATTERN.fullmatch(line)
            item = next(lines, None)
            if not match or item is None or MARKER in item or not item.endswith('\n'):
                return False
            count = int(match[1])
            if count < 4 or size + len(item) * count > len(original):
                return False
            line = item * count
        size += len(line)
        if size > len(original):
            return False
        result.append(line)
    return ''.join(result) == original


class GenericContextEngine:
    feature_id = 'core.context'
    spec = PluginSpec(feature_id, 'context', 50, validator=restores, task_pattern=r'\b(context|summari[sz]e|report)\b')

    def optimize(self, request):
        original = getattr(request, self.spec.evidence)
        candidate = encode(original)
        return EngineResult(candidate, estimate_text(original), estimate_text(candidate))


class GenericToolOutputEngine(GenericContextEngine):
    feature_id = 'agent.tool_output'
    spec = PluginSpec(feature_id, 'tool_output', 95, validator=restores, task_pattern=r'\b(tool output|command output|terminal output)\b')
