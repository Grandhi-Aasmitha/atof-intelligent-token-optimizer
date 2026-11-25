"""Compose independent evidence transforms, never drop failed or untouched inputs.

Safe default: retain the original evidence section on failure, no reduction or
cross-feature conflict. The returned result is only an API payload candidate.
"""
from time import perf_counter
from .fidelity import validate_stage, FidelityResult
from .measurement import compare_context
from .legacy.tokens import estimate_text
from .models import OptimizeRequest, OptimizationReport, FeatureDecision
from .engines.registry import EngineRegistry

LABEL = {'error_output':'ERROR OUTPUT', 'test_output':'TEST OUTPUT',
         'diff':'GIT DIFF', 'files':'SOURCE FILES', 'context':'CONTEXT', 'tool_output':'TOOL OUTPUT'}
SLOTS = tuple(LABEL)


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
    for slot in ('context', 'tool_output'):
        if getattr(request, slot):
            result[slot] = getattr(request, slot)
    return result


def compose(parts: dict[str,str]) -> str:
    present = [(slot, parts[slot]) for slot in SLOTS if slot in parts]
    if len(present) == 1:
        return present[0][1]
    return '\n\n'.join(f'===== {LABEL[slot]} =====\n{value}' for slot,value in present)


def run_pipeline(request: OptimizeRequest, decisions: list[FeatureDecision],
                 report: OptimizationReport, engines: EngineRegistry):
    from .models import OptimizeResponse
    started = perf_counter()
    original = source_sections(request)
    if not original:
        report.execution_duration_ms = round((perf_counter()-started)*1000, 3)
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
        report.execution_duration_ms = round((perf_counter()-started)*1000, 3)
        return OptimizeResponse(report=report)
    staged = dict(original)
    used_slots = set()
    for decision in decisions:
        if decision.status != 'selected':
            continue
        spec = engines.spec(decision.feature_id)
        slot = spec.evidence
        if not set(spec.depends_on).issubset(report.executed_features):
            decision.status, decision.reason = 'skipped', 'dependency_not_executed'
            continue
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
            if spec.validator is not None:
                valid = spec.validator(original[slot], result.content) is True
                fidelity = FidelityResult(valid, 'plugin_validation_passed' if valid else 'plugin_validation_failed', 1, int(valid))
            else:
                fidelity = validate_stage(decision.feature_id, original[slot], result.content, request.task)
            report.fidelity_checks.append({'feature_id':decision.feature_id,
                'passed':fidelity.passed, 'reason':fidelity.reason,
                'anchors_checked':fidelity.anchors_checked,
                'anchors_preserved':fidelity.anchors_preserved})
            if not fidelity.passed:
                decision.status, decision.reason = 'skipped', 'fidelity_' + fidelity.reason
                report.fidelity_status = 'rejected'
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
        report.execution_duration_ms = round((perf_counter()-started)*1000, 3)
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
        report.execution_duration_ms = round((perf_counter()-started)*1000, 3)
        return OptimizeResponse(report=report)
    report.optimized_estimated_tokens=after
    report.estimated_reduction_tokens=before-after
    report.estimated_reduction_percent=compare_context(baseline,payload).reduction_percent
    if report.fidelity_status != 'rejected':
        report.fidelity_status='passed'
    report.execution_duration_ms = round((perf_counter()-started)*1000, 3)
    report.delivery_status='payload_returned_to_client'
    report.warnings.append('Model delivery and provider token savings are unverified')
    return OptimizeResponse(optimized_context=payload,report=report)
