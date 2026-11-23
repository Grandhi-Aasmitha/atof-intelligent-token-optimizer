"""Shared, content-free decisions for trusted development instructions."""
from __future__ import annotations

import re
from collections.abc import Iterable

OPTIMIZERS = (
    "code_context", "repository_retrieval", "incremental_context",
    "code_diff", "test_log", "error_context",
)

_CODING_CONTEXT = re.compile(
    r"\b(?:app|application|project|software|website|webpage|dashboard|screen|"
    r"code|codebase|source|repository|repo|file|files|module|package|function|"
    r"method|class|component|service|endpoint|api|sdk|cli|script|library|"
    r"database|schema|query|test|tests|pytest|unittest|diff|patch|commit|"
    r"pull request|branch|stack trace|traceback|exception|bug|refactor|"
    r"implementation|deploy|compiler|compile|runtime|dependency|configuration|"
    r"cache|parser|serialization|authentication|handler|interface|algorithm|"
    r"timeout|import|thread|lint|regex|uncommitted|staged)\b"
    r"|\b[A-Za-z_]\w*\(\)|\b[A-Za-z_]\w*_[A-Za-z0-9_]+\b"
    r"|\b[A-Z]\w*(?:Error|Exception)\b"
    r"|\b[\w.-]+\.(?:py|js|jsx|ts|tsx|go|rs|java|cs|cpp|sql|sh|ps1)\b",
    re.I,
)
_IMPLEMENT = re.compile(r"\b(?:add|adds|adding|implement|create|build|develop|extend|introduce|integrate|enable|"
                        r"support|wire up|hook up|expose|allow)\b", re.I)
# Changes to existing behaviour phrased as edits ("update", "change", "make the X ...").
_MODIFY = re.compile(r"\b(?:update|change|modify|improve|enhance|adjust|tweak|replace|convert|migrate|port|upgrade|"
                     r"redesign|rework|optimi[sz]e|speed up|persist|validate|paginate|locali[sz]e)\b"
                     r"|\bmake\s+(?:the|it|this|that|our|my|all|every|each)\b(?!\s+sure)", re.I)
# Requirement-style requests that name a desired behaviour without an edit verb.
_FEATURE_NEED = re.compile(r"\b(?:should|must|needs? to|has to)\s+(?:also\s+|now\s+|be able to\s+)?"
                           r"(?:show|display|list|allow|support|accept|reject|return|include|send|save|store|"
                           r"let|have|work|handle|load|export|import|sort|filter|notify|remember|be)\b"
                           r"|\b(?:let|allow|enable)\s+(?:the\s+)?(?:users?|customers?|admins?|visitors?|people|clients?)\b"
                           r"|\bi (?:want|need|would like)\s+(?:a|an|the|to)\b|\bcan you (?:add|make|get)\b"
                           r"|\b(?:users?|customers?|admins?)\s+(?:should|must|can(?:not|'t)?|need)\b", re.I)
_PRODUCT = re.compile(r"\b(?:page|pages|screen|view|button|form|modal|dialog|menu|sidebar|navbar|login|logout|"
                      r"signup|sign[- ]in|password|profile|avatar|account|checkout|cart|order|orders|invoice|"
                      r"report|reports|export|upload|download|notification|email|feature|setting|settings|widget|"
                      r"table|column|field|route|ui|ux|frontend|backend|server|client|users?)\b", re.I)
_NEW = re.compile(
    r"\bfrom scratch\b|\bnew\s+(?:\w+\s+){0,4}(?:app|application|project|service|website|tool|game|cli)\b"
    r"|\b(?:build|create|make|develop|scaffold|bootstrap|start)\s+(?:me\s+)?(?:a|an)\s+"
    r"(?:\w+\s+){0,5}(?:app|application|project|service|website|tool|game|cli|api)\b", re.I,
)
_EXISTING = re.compile(r"\b(?:existing|current|this|our|my)\s+(?:\w+\s+){0,3}(?:app|application|project|codebase|"
                       r"repository|repo|module|service|code|endpoint|page|component)\b", re.I)
_DEBUG = re.compile(r"\b(?:debug|diagnose|troubleshoot|root cause|traceback|stack ?trace|exception|"
                    r"crash(?:es|ed|ing)?|hang(?:s|ing)?|freez(?:es|ing)|timeouts?|timing out|segfault|panic)\b"
                    r"|\b[A-Z]\w*(?:Error|Exception)\b", re.I)
_ERROR = re.compile(r"\b(?:error|errors|failure|failures|failing|fails|failed|red)\b", re.I)
_FIX = re.compile(r"\b(?:fix|fixes|repair|resolve|broken|breaks|bug|bugs|regression|not working|doesn'?t work|"
                  r"stopped working|wrong|incorrect)\b", re.I)
_REVIEW = re.compile(r"\b(?:review|code review|audit|critique|look over|sanity[- ]check)\b"
                     r"|\b(?:my|current|local|uncommitted|staged|pending|recent)\s+(?:changes?|diff|edits?|commits?)\b"
                     r"|\b(?:this|the)\s+(?:diff|patch|pull request|pr)\b", re.I)
_REFACTOR = re.compile(r"\b(?:refactor|refactoring|clean ?up|simplify|rename|restructure|reorgani[sz]e|"
                       r"deduplicate|extract (?:a |the )?(?:function|method|class|module))\b", re.I)
_EXPLAIN = re.compile(r"\b(?:explain|describe|understand|how does|how do|what does|what happens|walk me through|"
                      r"analyse|analyze|investigate|find where|where is|where does|locate|summari[sz]e)\b", re.I)
_TEST = re.compile(r"\b(?:test|tests|testing|pytest|unittest|jest|vitest|coverage|spec|specs)\b", re.I)
_TEST_ONLY = re.compile(
    r"^\s*(?:please\s+)?(?:write|add|create|run|update|improve|increase|extend|expand|fix)\s+"
    r"(?:(?:the|some|more|unit|integration|automated|new|existing|missing|failing|my|our)\s+)*"
    r"(?:tests?|test coverage|coverage|specs?)\b", re.I,
)
# Running/verifying an existing suite, as opposed to authoring tests.
_TEST_RUN = re.compile(
    r"\b(?:run|re-?run|execute|kick off|trigger)\s+(?:(?:the|all|of|my|our|unit|integration|e2e|end-to-end|"
    r"existing|failing|failed|full|whole|entire|test)\s+)*(?:tests?|test suite|suite|specs?|pytest|unittest|"
    r"jest|vitest|mocha|go test|cargo test|npm test)\b"
    r"|\b(?:do|does|did)\s+(?:the\s+|all\s+(?:the\s+)?)?tests?\s+(?:still\s+)?pass"
    r"|\b(?:check|verify|confirm|see|make sure|ensure)\s+(?:if\s+|whether\s+|that\s+)?(?:the\s+|all\s+(?:the\s+)?)?"
    r"tests?\s+(?:still\s+)?(?:pass|passes|work|are green|succeed)", re.I,
)
_TEST_AUTHOR = re.compile(
    r"\b(?:write|writes|writing|add|create|generate|update|improve|increase|extend|expand|cover)\b"
    r"(?:\s+(?:and|then|&)\s+(?:re-?run|run|execute))?"
    r"(?:\s+(?!(?:and|then|run|rerun|execute)\b)\w+){0,4}\s+(?:tests?|test cases?|test coverage|coverage|specs?)\b", re.I,
)
# "my change", "the last changes": a noun naming prior work, not an edit request.
_CHANGE_NOUN = re.compile(r"\b(?:my|the|this|that|these|those|our|your|last|recent|latest|previous)\s+"
                          r"(?:\w+\s+)?changes?\b", re.I)
_NEGATED = re.compile(r"\b(?:do not|don't|dont|never|without|no need to|avoid|nor)\s+(?:\w+\s+)?\w+", re.I)
_FIX_VERB = re.compile(r"\b(?:fix|fixes|repair|resolve)\b", re.I)
_STRONG_ACTION = (_IMPLEMENT, _MODIFY, _FEATURE_NEED, _FIX, _REFACTOR, _DEBUG)
_EVIDENCE_OPTIMIZERS = {
    "source_files": ("code_context", "repository_retrieval"),
    "verified_prior_context": ("incremental_context",),
    "diff": ("code_diff",),
    "test_output": ("test_log",),
    "error_output": ("error_context",),
}
OPTIMIZATION_CAPABILITIES = ("prompt_optimizer",) + OPTIMIZERS
CONTRACT = "atof-intent/2"
_EVIDENCE_FOR = {"code_context": "source_files", "repository_retrieval": "source_files",
                 "incremental_context": "verified_prior_context", "code_diff": "diff",
                 "test_log": "test_output", "error_context": "error_output"}


def _plan(primary: str, scope: str, evidence: list[str], coding: bool) -> dict:
    """Per-capability eligibility. Evidence is data: it enables its optimizer for any intent."""
    plan = {"prompt_optimizer": {
        "eligible": coding, "trigger": "instruction_text" if coding else None,
        "reason": "natural_language_instruction" if coding else "non_coding_prompt"}}
    for name in OPTIMIZERS:
        kind = _EVIDENCE_FOR[name]
        present = kind in evidence
        if not coding:
            entry = (False, "non_coding_prompt")
        elif name == "repository_retrieval" and scope == "new_project" and not present:
            entry = (False, "new_project_has_no_repository")
        elif present:
            entry = (True, "evidence_present")
        else:
            entry = (False, f"awaiting_{kind}")
        plan[name] = {"eligible": entry[0], "trigger": kind if present else None, "reason": entry[1]}
    return plan


def route_intent(task: str, *, evidence_types: Iterable[str] = (), coding_agent: bool = False) -> dict:
    """Classify an instruction; evidence describes data, never another instruction.

    ``coding_agent`` marks text that arrived through a coding agent (hook, gateway,
    MCP), where a clear development action is a coding signal even without a code
    noun ("Let users reset their password"). Explanations alone never are.
    """
    if not isinstance(task, str):
        raise ValueError("task must be text")
    evidence = sorted(set(evidence_types) & _EVIDENCE_OPTIMIZERS.keys())
    original_task = task
    # Negated actions are constraints ("do not modify files"), not requested work.
    task = _NEGATED.sub(" ", task)
    action = any(pattern.search(task) for pattern in _STRONG_ACTION)
    signals = [name for name, hit in (
        ("code_noun", bool(_CODING_CONTEXT.search(task))),
        ("product_noun_with_action", bool(_PRODUCT.search(task) and action)),
        ("agent_action", bool(coding_agent and action)),
        ("evidence", bool(evidence)),
    ) if hit]
    coding = bool(signals)
    if not coding:
        return {
            "contract": CONTRACT, "primary_intent": "general", "capabilities": [], "secondary_intents": [],
            "scope": "unknown", "signals": [], "evidence_types": evidence,
            "eligible_optimizers": [], "optimizer_plan": _plan("general", "unknown", evidence, False),
            "confidence": "low", "uncertainty": "no_development_signal", "bypass_reason": "non_coding_prompt",
        }

    test_run = bool(_TEST_RUN.search(task))
    test_author = bool(_TEST_AUTHOR.search(task))
    modify = bool(_MODIFY.search(_CHANGE_NOUN.sub(" ", task)))
    # Primary intent comes from the instruction text; attached evidence only adds
    # capabilities (and decides the primary when the text names no goal).
    tests = bool(_TEST.search(task) or test_run)
    debug = bool(_DEBUG.search(task))
    fix = bool(_FIX.search(task))
    review = bool(_REVIEW.search(task))
    tests_cap = tests or "test_output" in evidence
    debug_cap = debug or "error_output" in evidence
    review_cap = review or ("diff" in evidence and not (_IMPLEMENT.search(task) or modify))
    refactor = bool(_REFACTOR.search(task))
    explain = bool(_EXPLAIN.search(task))
    implementation = bool(_IMPLEMENT.search(task) or modify or _FEATURE_NEED.search(task))
    test_only = bool(_TEST_ONLY.search(task) and not re.search(r"\b(?:implement|build|extend|feature)\b", task, re.I)
                     and not re.search(r"\b(?:and|then|also)\s+(?:add|implement|update|change|make|build)\b", task, re.I))
    if test_only:
        implementation = False
    if review and fix and not _FIX_VERB.search(task):
        fix = False  # "review X for bugs": bugs are what the review looks for
    if refactor and not _IMPLEMENT.search(task) and not _FEATURE_NEED.search(task):
        implementation = False
    new_app = bool(_NEW.search(task) and not _EXISTING.search(task))
    if review and not (_IMPLEMENT.search(task) or _FEATURE_NEED.search(task)) and re.search(
            r"\breview\b", task, re.I):
        implementation = False

    capabilities = []
    for name, enabled in (
        ("implementation", implementation or new_app or fix),
        ("debugging", debug_cap or fix or (tests_cap and bool(_ERROR.search(task)))),
        ("review", review_cap), ("tests", tests_cap), ("test_execution", test_run), ("refactoring", refactor),
        ("explanation", explain), ("new_app_creation", new_app),
    ):
        if enabled:
            capabilities.append(name)

    if new_app:
        primary = "new_application"
    elif debug:
        primary = "error_analysis"
    elif fix:
        primary = "test_debugging" if tests and test_only else "bug_fix"
    elif refactor:
        primary = "refactoring"
    elif implementation:
        primary = "feature_addition"
    elif test_run and not test_author and not re.search(r"\b(?:review|audit|critique)\b", task, re.I):
        primary = "test_execution"
    elif tests and (test_author or not test_run) and _ERROR.search(task):
        primary = "test_debugging"
    elif tests and (test_author or not test_run):
        primary = "test_writing"
    elif review and (not explain or re.search(r"\b(?:diff|changes?|commit|patch|pull request)\b", original_task, re.I)):
        primary = "change_review"
    elif explain:
        primary = "explanation"
    elif review:
        primary = "change_review"
    elif test_run:
        primary = "test_execution"
    elif "error_output" in evidence:
        primary = "error_analysis"
    elif "test_output" in evidence:
        primary = "test_debugging" if _ERROR.search(task) else "test_writing"
    elif "diff" in evidence:
        primary = "change_review"
    else:
        primary = "general"

    if new_app:
        scope = "new_project"
    elif (_EXISTING.search(task) or evidence or fix or debug or refactor or review_cap or test_run
          or (implementation and modify) or "code_noun" in signals and implementation):
        scope = "existing_project"
    else:
        scope = "unknown"
    secondary = {"implementation": "feature_addition", "debugging": "error_analysis", "review": "change_review",
                 "tests": "test_execution" if test_run and not test_author else "test_writing",
                 "test_execution": "test_execution", "refactoring": "refactoring", "explanation": "explanation"}
    eligible = {name for kind in evidence for name in _EVIDENCE_OPTIMIZERS[kind]}
    return {
        "contract": CONTRACT,
        "primary_intent": primary,
        "capabilities": capabilities,
        "secondary_intents": sorted({secondary[c] for c in capabilities if c in secondary} - {primary}),
        "scope": scope,
        "signals": signals,
        "evidence_types": evidence,
        "eligible_optimizers": [name for name in OPTIMIZERS if name in eligible],
        "optimizer_plan": _plan(primary, scope, evidence, True),
        "confidence": "high" if capabilities or evidence else "medium",
        "uncertainty": None if capabilities or evidence else "development_goal_unclear",
        "bypass_reason": None if capabilities or evidence else "development_goal_unclear",
    }


def legacy_developer_intent(decision: dict) -> str:
    """Map the common contract to the existing BLM-7 public vocabulary."""
    return {
        "new_application": "implementation",
        "feature_addition": "implementation",
        "bug_fix": "implementation",
        "error_analysis": "debugging",
        "test_debugging": "test_debugging",
        "test_writing": "test_debugging",
        "test_execution": "test_debugging",
        "refactoring": "refactoring",
        "change_review": "change_review",
        "explanation": "code_explanation",
    }.get(decision["primary_intent"], "code_explanation")
