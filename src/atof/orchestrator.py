"""Compose independent evidence transforms, never drop failed or untouched inputs.

Safe default: retain the original evidence section on failure, no reduction or
cross-feature conflict. The returned result is only an API payload candidate.
"""
from dataclasses import dataclass
from .legacy.tokens import estimate_text
from .models import OptimizeRequest, OptimizationReport, FeatureDecision
from .engines.registry import EngineRegistry

SLOTS = ('error_output', 'test_output', 'diff', 'files')
FEATURE_SLOT = {
    'coding.error_context': 'error_output',
    'coding.test_log': 'test_output',
    'coding.code_diff': 'diff',
    'coding.code_context': 'files',
    'coding.repository_retrieval': 'files',
}
LABEL = {'error_output':'ERROR OUTPUT', 'test_output':'TEST OUTPUT',
         'diff':'GIT DIFF', 'files':'SOURCE FILES'}


def source_sections(request: OptimizeRequest) -> dict[str, str]:
    result = {}
    if request.error_output:
        result['error_output'] = request.error_output
    if request.test_output:
        result['test_output'] = request.test_output
    if request.diff:
        result['diff'] = request.diff
    if request.files:
        result['files'] = '\n\n'.join(f'# {f.path}\n{f.content}' for f in request.files)
    return result


def compose(parts: dict[str,str]) -> str:
    present = [(slot, parts[slot]) for slot in SLOTS if slot in parts]
    if len(present) == 1:
        return present[0][1]
    return '\n\n'.join(f'===== {LABEL[slot]} =====\n{value}' for slot,value in present)


def run_pipeline(request: OptimizeRequest, decisions: list[FeatureDecision],
                 report: OptimizationReport, engines: EngineRegistry):
    from .models import OptimizeResponse
    original = source_sections(request)
    if not original:
        return OptimizeResponse(report=report)
    baseline = compose(original)
    before = estimate_text(baseline)
    report.original_context_estimated_tokens = before
    report.original_estimated_tokens = before
    if not request.execute:
        for decision in decisions:
            if decision.status == 'selected':
                decision.status='applicable'
                decision.reason='dry_run_only'
        return OptimizeResponse(report=report)
    staged = dict(original)
    used_slots = set()
    for decision in decisions:
        if decision.status != 'selected':
            continue
        slot = FEATURE_SLOT[decision.feature_id]
        if slot in used_slots:
            decision.status = 'skipped'
            decision.reason = 'evidence_slot_already_processed'
            continue
        used_slots.add(slot)
        engine = engines.get(decision.feature_id)
        if engine is None:
            decision.status, decision.reason = 'unsupported','engine_missing_during_execution'
            continue
        try:
            result = engine.optimize(request)
            decision.estimated_before = result.before
            decision.estimated_after = result.after
            report.warnings.extend(result.warnings)
            safe = (result.content.strip() and result.after < result.before
                    and not any(w.startswith('unresolved_dependencies:') for w in result.warnings))
            if not safe:
                decision.status, decision.reason = 'skipped', 'not_smaller_or_unresolved_dependencies'
                continue
            # Verify using the same estimator for both sides, not arbitrary
            # engine-specific token estimates. Preserve original when larger.
            trial = dict(staged)
            trial[slot] = result.content
            if estimate_text(compose(trial)) >= estimate_text(compose(staged)):
                decision.status, decision.reason = 'skipped', 'composed_context_not_smaller'
                continue
            staged[slot] = result.content
            decision.status, decision.reason = 'executed','optimized_candidate_composed'
            report.executed_features.append(decision.feature_id)
            if report.engine is None:
                report.engine = type(engine).__name__
                report.executed_feature = decision.feature_id
        except Exception as exc:
            # Never return raw exception text: it may contain evidence/secrets.
            decision.status, decision.reason = 'failed', f'engine_{type(exc).__name__}'
            report.warnings.append(f'{decision.feature_id} failed; original evidence preserved')
        finally:
            report.stage_results.append({'feature_id':decision.feature_id,
                                         'status':decision.status, 'reason':decision.reason,
                                         'estimated_before':decision.estimated_before,
                                         'estimated_after':decision.estimated_after})
    if not report.executed_features:
        return OptimizeResponse(report=report)
    payload = compose(staged)
    after = estimate_text(payload)
    if after >= before:
        report.warnings.append('Composite reduction rejected; original context preserved')
        for d in decisions:
            if d.status=='executed':
                d.status, d.reason='skipped','composite_not_smaller'
        report.executed_features=[]
        report.executed_feature=None
        report.engine=None
        report.stage_results=[]
        return OptimizeResponse(report=report)
    report.optimized_estimated_tokens=after
    report.estimated_reduction_tokens=before-after
    report.delivery_status='payload_returned_to_client'
    report.warnings.append('Model delivery and provider token savings are unverified')
    return OptimizeResponse(optimized_context=payload,report=report)
