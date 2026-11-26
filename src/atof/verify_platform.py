"""Deterministic, offline feature verification; never invokes a model."""
import json
from .models import OptimizeRequest
from .service import optimize


def fixtures():
    source = 'def subtotal(items):\n    return sum(items)\n\ndef total(items):\n    return subtotal(items)\n'
    source += ''.join(f'\ndef unrelated_{i}(): return {i}\n' for i in range(100))
    return [
        ('coding.code_context', {'task':'Explain total and dependencies', 'files':[{'path':'service.py','content':source}]}, ['def total','def subtotal']),
        ('coding.repository_retrieval', {'task':'Find invoice total implementation','files':[{'path':'invoice.py','content':'def invoice_total(x): return x * 2\n'}, {'path':'weather.py','content':'def forecast(): return "sunny"\n'*150}], 'token_budget':200}, ['invoice.py','invoice_total']),
        ('coding.code_diff', {'task':'Review changes','diff':'diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,6 +1,6 @@\n'+' context\n'*100+'-old\n+new\n'+' context\n'*100}, ['-old','+new']),
        ('coding.test_log', {'task':'Analyze failing tests','test_output':'test_ok PASSED\n'*130+'test_bad FAILED\nE AssertionError: wrong total\n'}, ['test_bad FAILED','AssertionError']),
        ('coding.error_context', {'task':'Diagnose error','error_output':'heartbeat healthy\n'*100+'RuntimeError: database failed\n'}, ['RuntimeError: database failed']),
        ('core.context', {'task':'Explain supplied context','context':'Service status: healthy\n'*100+'Region: west\n'}, ['Service status: healthy','Region: west','[ATOF repeat x100]']),
        ('agent.tool_output', {'task':'Inspect tool output','tool_output':'worker ready\n'*100+'ERROR: missing input\n'}, ['worker ready','ERROR: missing input','[ATOF repeat x100]']),
    ]


def verify():
    results = []
    for feature, data, anchors in fixtures():
        request = OptimizeRequest(**data, feature_override=feature)
        off = optimize(request.model_copy(update={'optimization_enabled':False}), source_kind='synthetic_test')
        on = optimize(request, source_kind='synthetic_test')
        report = on.report
        content = on.optimized_context or ''
        passed = (off.optimized_context is None and not off.report.executed_features and
                  len(off.report.decisions) == 1 and off.report.decisions[0].reason == 'optimization_disabled' and
                  report.executed_features == [feature] and report.fidelity_status == 'passed' and
                  report.estimated_reduction_tokens is not None and report.estimated_reduction_tokens > 0 and
                  report.original_estimated_tokens == off.report.original_estimated_tokens and
                  all(anchor in content for anchor in anchors) and report.provider_tokens_saved is None)
        results.append({'feature':feature, 'passed':passed, 'before':report.original_estimated_tokens,
                        'after':report.optimized_estimated_tokens, 'removed':report.estimated_reduction_tokens,
                        'fidelity':report.fidelity_status, 'duration_ms':report.execution_duration_ms,
                        'request_id':report.request_id, 'decisions':[d.model_dump() for d in report.decisions]})
    return {'passed':sum(row['passed'] for row in results), 'total':len(results),
            'measurement':'local_heuristic_estimate', 'provider_savings_verified':False, 'results':results}


def main():
    result = verify()
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] == result['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
