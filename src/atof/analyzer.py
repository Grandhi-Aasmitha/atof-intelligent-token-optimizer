import re
from dataclasses import dataclass
from .models import OptimizeRequest

@dataclass(frozen=True)
class Analysis:
    intent: str
    evidence_types: frozenset[str]

_EXPLAIN=re.compile(r'\b(explain|understand|describe|review|what does|how does)\b',re.I)
_DEBUG=re.compile(r'\b(fix|debug|error|exception|fail|traceback|broken)\b',re.I)
_TEST=re.compile(r'\b(test|pytest|unittest|junit|maven)\b',re.I)

def analyze(request: OptimizeRequest)->Analysis:
    text=request.task
    intent='debugging' if _DEBUG.search(text) else 'explanation' if _EXPLAIN.search(text) else 'test_execution' if _TEST.search(text) else 'general'
    evidence=set()
    if request.files: evidence.add('source')
    if 'diff --git ' in text: evidence.add('diff')
    if 'Traceback (most recent call last)' in text or re.search(r'\b(?:[A-Za-z]+Error|[A-Za-z]+Exception):',text):evidence.add('error')
    if re.search(r'\b(?:FAILED|tests? failed|test failures)\b',text,re.I): evidence.add('test')
    return Analysis(intent,frozenset(evidence))
