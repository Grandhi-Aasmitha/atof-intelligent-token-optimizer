"""Deterministic request analysis. Intent is not authorization or evidence."""
import re
from dataclasses import dataclass
from .models import OptimizeRequest

@dataclass(frozen=True)
class Analysis:
    intent: str
    evidence_types: frozenset[str]
    supplied_slots: frozenset[str] = frozenset()
    requested_slots: frozenset[str] = frozenset()

SLOT_KIND = {'files':'source', 'diff':'diff', 'test_output':'test',
             'error_output':'error', 'context':'context', 'tool_output':'tool'}
_EXPLAIN = re.compile(r'\b(explain|understand|describe|review|what does|how does)\b', re.I)
_DEBUG = re.compile(r'\b(fix|debug|error|exception|fail(?:ed|ing|ure)?|traceback|broken)\b', re.I)
_TEST = re.compile(r'\b(tests?|pytest|unittest|junit|maven)\b', re.I)
_HINTS = {
    'diff': re.compile(r'diff --git |\b(?:git diff|review (?:the |my )?diff|pull request diff)\b', re.I),
    'error_output': re.compile(r'Traceback \(most recent call last\)|\b[A-Za-z_][\w.]*(?:Error|Exception):|\b(?:error log|stack trace|traceback)\b', re.I),
    'test_output': re.compile(r'\b(?:FAILED|tests? (?:failed|failing|failures?)|failing (?:unit )?tests?|test failures?|test log)\b', re.I),
    'files': re.compile(r'\b(?:source files?|repository|codebase)\b', re.I),
    'context': re.compile(r'\b(?:attached report|supplied context)\b', re.I),
    'tool_output': re.compile(r'\b(?:tool output|command output|terminal output)\b', re.I),
}

def analyze(request: OptimizeRequest) -> Analysis:
    text = request.task
    intent = ('debugging' if _DEBUG.search(text) else 'explanation' if _EXPLAIN.search(text)
              else 'test_execution' if _TEST.search(text) else 'general')
    supplied = frozenset(slot for slot in SLOT_KIND
                         if (request.files if slot == 'files' else getattr(request, slot).strip()))
    hinted = frozenset(slot for slot, pattern in _HINTS.items() if pattern.search(text))
    return Analysis(intent, frozenset(SLOT_KIND[s] for s in supplied | hinted), supplied, hinted)
